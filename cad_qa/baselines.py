"""Simple baselines and metric aggregation."""

from __future__ import annotations

from collections import Counter, defaultdict
import ast
import json
import math
import random
import re
from typing import Any

from cad_qa.operation_graph import extract_operation_graph
from cad_qa.parse import grade_candidate


def evaluate_predictions(rows: list[dict[str, Any]], predictions: dict[str, str]) -> dict[str, Any]:
    results = []
    for row in rows:
        row_id = str(row["id"])
        candidate = predictions.get(row_id, "")
        grade = grade_candidate(row, candidate)
        results.append({"row_id": row_id, "task_type": row["task_type"], "split": row["split"], **grade})
    return aggregate_results(results)


def baseline_predictions(rows: list[dict[str, Any]], *, name: str, seed: int = 1234) -> dict[str, str]:
    if name == "oracle":
        return {str(row["id"]): _answer_to_text(row["answer"]) for row in rows}
    if name == "majority":
        return _majority_predictions(rows)
    if name == "random":
        return _random_predictions(rows, seed=seed)
    if name == "static_operation_count":
        return _static_operation_count_predictions(rows)
    if name == "regex_operation_count":
        return _regex_operation_count_predictions(rows)
    if name == "selector_heuristic":
        return _selector_heuristic_predictions(rows)
    if name == "primitive_symbolic_volume":
        return _primitive_symbolic_volume_predictions(rows)
    if name == "aabb_point_membership":
        return _aabb_point_membership_predictions(rows)
    if name == "advanced_diagnostic_naive":
        return _advanced_diagnostic_naive_predictions(rows)
    raise ValueError(f"unknown baseline: {name}")


def run_baselines(rows: list[dict[str, Any]], *, seed: int = 1234) -> dict[str, Any]:
    return {
        name: evaluate_predictions(rows, baseline_predictions(rows, name=name, seed=seed))
        for name in (
            "majority",
            "random",
            "static_operation_count",
            "regex_operation_count",
            "selector_heuristic",
            "primitive_symbolic_volume",
            "aabb_point_membership",
            "advanced_diagnostic_naive",
            "oracle",
        )
    }


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    correct = sum(1 for result in results if result["correct"])
    invalid = sum(1 for result in results if not result["valid"])
    return {
        "row_count": total,
        "accuracy": correct / total if total else 0.0,
        "invalid_output_rate": invalid / total if total else 0.0,
        "by_task_type": _group_accuracy(results, "task_type"),
        "by_split": _group_accuracy(results, "split"),
    }


def _majority_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    by_task: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_task[str(row["task_type"])][_answer_to_text(row["answer"])] += 1
    majority = {task: counter.most_common(1)[0][0] for task, counter in by_task.items()}
    return {str(row["id"]): majority[str(row["task_type"])] for row in rows}


def _random_predictions(rows: list[dict[str, Any]], *, seed: int) -> dict[str, str]:
    rng = random.Random(seed)
    predictions: dict[str, str] = {}
    for row in rows:
        choices = row.get("choices")
        if isinstance(choices, list) and choices:
            predictions[str(row["id"])] = str(rng.choice(choices))
        elif row.get("answer_type") == "integer":
            predictions[str(row["id"])] = str(rng.randint(0, 5))
        elif row.get("answer_type") == "number":
            predictions[str(row["id"])] = "0"
        elif row.get("answer_type") == "bbox":
            predictions[str(row["id"])] = '{"min":[0,0,0],"max":[0,0,0]}'
        else:
            predictions[str(row["id"])] = ""
    return predictions


def _static_operation_count_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    for row in rows:
        if row.get("task_type") == "operation_count":
            labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
            predictions[str(row["id"])] = str(labels.get("operation_count", 0))
        else:
            predictions[str(row["id"])] = "0"
    return predictions


def _regex_operation_count_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    for row in rows:
        if row.get("task_type") == "operation_count":
            labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
            operation = str(labels.get("operation", ""))
            code = _code_from_prompt(str(row.get("prompt", "")))
            if operation == "Workplane":
                count = len(re.findall(r"\b(?:cq|cadquery)\.Workplane\s*\(", code))
            else:
                count = len(re.findall(rf"\.{re.escape(operation)}\s*\(", code))
            predictions[str(row["id"])] = str(count)
        else:
            predictions[str(row["id"])] = "0"
    return predictions


def _selector_heuristic_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    for row in rows:
        if row.get("task_type") != "selector_count":
            predictions[str(row["id"])] = "0"
            continue
        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        selector_result = labels.get("selector_result") if isinstance(labels.get("selector_result"), dict) else {}
        expression = str(selector_result.get("selector_expression", ""))
        entity_type = str(selector_result.get("entity_type", ""))
        predictions[str(row["id"])] = str(_selector_guess(expression, entity_type))
    return predictions


def _selector_guess(expression: str, entity_type: str) -> int:
    if any(token in expression for token in ('">', '"<', "'>", "'<")):
        return 1
    if "|Z" in expression or "|X" in expression or "|Y" in expression:
        return 4 if entity_type == "edge" else 2
    if entity_type == "face":
        return 6
    if entity_type == "edge":
        return 12
    if entity_type == "vertex":
        return 8
    return 1


def _primitive_symbolic_volume_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    bbox_by_target = _bbox_by_target(rows)
    graph_by_code: dict[str, Any] = {}
    for row in rows:
        if row.get("task_type") != "signed_volume_delta":
            predictions[str(row["id"])] = "0"
            continue
        code = _code_from_prompt(str(row.get("prompt", "")))
        nodes = graph_by_code.get(code)
        if nodes is None:
            nodes, _result_variable, _issues = extract_operation_graph(code)
            graph_by_code[code] = nodes
        target = str(row.get("target_feature_id") or "")
        node = next((item for item in nodes if item.feature_id == target), None)
        guess = _symbolic_volume_delta(
            operation=getattr(node, "operation", ""),
            args=getattr(node, "args_repr", []),
            bbox=bbox_by_target.get((str(row.get("source_id")), target)),
        )
        predictions[str(row["id"])] = _number_to_text(guess if guess is not None else 0.0)
    return predictions


def _aabb_point_membership_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    bbox_by_target = _bbox_by_target(rows)
    for row in rows:
        if row.get("task_type") != "point_membership":
            predictions[str(row["id"])] = "outside"
            continue
        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        query = labels.get("point_query") if isinstance(labels.get("point_query"), dict) else {}
        point = query.get("point")
        target = str(query.get("target_feature_id") or row.get("target_feature_id") or "")
        bbox = bbox_by_target.get((str(row.get("source_id")), target))
        predictions[str(row["id"])] = _classify_point_in_bbox(point, bbox)
    return predictions


def _advanced_diagnostic_naive_predictions(rows: list[dict[str, Any]]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    for row in rows:
        task_type = row.get("task_type")
        if task_type == "graph_query":
            choices = row.get("choices")
            predictions[str(row["id"])] = str(choices[0]) if isinstance(choices, list) and choices else ""
        elif task_type == "spatial_distance":
            predictions[str(row["id"])] = "0"
        elif task_type == "bbox_region_query":
            predictions[str(row["id"])] = "0"
        elif task_type == "validity_failure_prediction":
            choices = row.get("choices")
            predictions[str(row["id"])] = "valid" if not isinstance(choices, list) or "valid" in choices else str(choices[0])
        else:
            predictions[str(row["id"])] = "0"
    return predictions


def _bbox_by_target(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, list[float]]]:
    result: dict[tuple[str, str], dict[str, list[float]]] = {}
    for row in rows:
        if row.get("task_type") != "bbox_after_step":
            continue
        target = row.get("target_feature_id")
        if not isinstance(target, str):
            continue
        answer = row.get("answer")
        if _is_bbox(answer):
            result[(str(row.get("source_id")), target)] = answer
    return result


def _symbolic_volume_delta(operation: str, args: list[str], bbox: dict[str, list[float]] | None) -> float | None:
    values = [_literal_number(arg) for arg in args]
    if operation == "box" and len(values) >= 3 and all(value is not None for value in values[:3]):
        return float(values[0]) * float(values[1]) * float(values[2])
    if operation == "hole" and values and values[0] is not None:
        height = _bbox_extent(bbox, axis=2)
        if height is not None:
            radius = float(values[0]) / 2.0
            return -(math.pi * radius * radius * height)
    if operation in {"cut_blind", "cutBlind"} and values and values[0] is not None:
        return -abs(float(values[0]))
    if operation == "extrude" and values and values[0] is not None:
        return float(values[0])
    return None


def _classify_point_in_bbox(point: Any, bbox: dict[str, list[float]] | None) -> str:
    if not _is_point(point) or not _is_bbox(bbox):
        return "outside"
    minimum = bbox["min"]
    maximum = bbox["max"]
    tolerance = 1e-9
    outside = any(float(coord) < lo - tolerance or float(coord) > hi + tolerance for coord, lo, hi in zip(point, minimum, maximum, strict=True))
    if outside:
        return "outside"
    boundary = any(abs(float(coord) - lo) <= tolerance or abs(float(coord) - hi) <= tolerance for coord, lo, hi in zip(point, minimum, maximum, strict=True))
    return "on_boundary" if boundary else "inside"


def _literal_number(value: str) -> float | None:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None
    if isinstance(parsed, int | float) and math.isfinite(float(parsed)):
        return float(parsed)
    return None


def _bbox_extent(bbox: dict[str, list[float]] | None, *, axis: int) -> float | None:
    if not _is_bbox(bbox):
        return None
    return float(bbox["max"][axis]) - float(bbox["min"][axis])


def _is_bbox(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("min"), list)
        and isinstance(value.get("max"), list)
        and len(value["min"]) == 3
        and len(value["max"]) == 3
    )


def _is_point(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(isinstance(item, int | float) for item in value)


def _number_to_text(value: float) -> str:
    return format(value, ".12g")


def _group_accuracy(results: list[dict[str, Any]], field: str) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        groups[str(result[field])].append(result)
    return {
        group: {
            "row_count": len(items),
            "accuracy": sum(1 for item in items if item["correct"]) / len(items),
            "invalid_output_rate": sum(1 for item in items if not item["valid"]) / len(items),
        }
        for group, items in sorted(groups.items())
    }


def _answer_to_text(answer: Any) -> str:
    if isinstance(answer, dict):
        return json.dumps(answer, separators=(",", ":"), sort_keys=True)
    return str(answer)


def _code_from_prompt(prompt: str) -> str:
    match = re.search(r"```python\n(?P<code>.*)```", prompt, re.DOTALL)
    return match.group("code") if match else prompt
