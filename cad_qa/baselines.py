"""Simple baselines and metric aggregation."""

from __future__ import annotations

from collections import Counter, defaultdict
import random
import re
from typing import Any

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
    raise ValueError(f"unknown baseline: {name}")


def run_baselines(rows: list[dict[str, Any]], *, seed: int = 1234) -> dict[str, Any]:
    return {
        name: evaluate_predictions(rows, baseline_predictions(rows, name=name, seed=seed))
        for name in ("majority", "random", "static_operation_count", "regex_operation_count", "selector_heuristic", "oracle")
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
        import json

        return json.dumps(answer, separators=(",", ":"), sort_keys=True)
    return str(answer)


def _code_from_prompt(prompt: str) -> str:
    match = re.search(r"```python\n(?P<code>.*)```", prompt, re.DOTALL)
    return match.group("code") if match else prompt
