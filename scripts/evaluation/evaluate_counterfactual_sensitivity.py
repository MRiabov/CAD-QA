"""Evaluate paired counterfactual sensitivity from rows and predictions."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_jsonl, write_json, write_jsonl
from cad_qa.parse import grade_candidate
from cad_qa.predictions import read_prediction_artifact


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    predictions = read_prediction_artifact(args.predictions)
    pairs, report = evaluate_counterfactual_sensitivity(rows, predictions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "counterfactual_pairs.jsonl", pairs)
    write_json(args.output_dir / "counterfactual_sensitivity_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


def evaluate_counterfactual_sensitivity(rows: list[dict[str, Any]], predictions: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped = _group_rows(rows)
    pairs = []
    for group_key, group_rows in grouped.items():
        for left_index, left in enumerate(group_rows):
            for right in group_rows[left_index + 1 :]:
                pair = _pair_result(group_key, left, right, predictions)
                if pair is not None:
                    pairs.append(pair)
    changed = [pair for pair in pairs if pair["answer_changed"]]
    unchanged = [pair for pair in pairs if not pair["answer_changed"]]
    report = {
        "schema": "cadqa_counterfactual_sensitivity_report_v1",
        "row_count": len(rows),
        "pair_count": len(pairs),
        "answer_changed_pair_count": len(changed),
        "answer_unchanged_pair_count": len(unchanged),
        "answer_flip_accuracy": _rate(changed, "prediction_changed") if changed else 0.0,
        "false_invariance_rate": _rate(changed, "prediction_unchanged") if changed else 0.0,
        "false_sensitivity_rate": _rate(unchanged, "prediction_changed") if unchanged else 0.0,
        "numeric_pair_count": sum(1 for pair in pairs if pair.get("numeric_magnitude_error") is not None),
        "mean_numeric_magnitude_error": _mean(
            [float(pair["numeric_magnitude_error"]) for pair in pairs if pair.get("numeric_magnitude_error") is not None]
        ),
        "by_task_type": _by_task_type(pairs),
    }
    return pairs, report


def _group_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        group_id = provenance.get("counterfactual_group_id") or row.get("trace_id")
        if not group_id:
            continue
        key = (str(group_id), str(row.get("task_type")), str(row.get("target_feature_id")))
        grouped[key].append(row)
    return {key: items for key, items in grouped.items() if len(items) > 1}


def _pair_result(group_key: tuple[str, str, str], left: dict[str, Any], right: dict[str, Any], predictions: dict[str, str]) -> dict[str, Any] | None:
    left_id = str(left["id"])
    right_id = str(right["id"])
    if left_id not in predictions or right_id not in predictions:
        return None
    left_grade = grade_candidate(left, predictions[left_id])
    right_grade = grade_candidate(right, predictions[right_id])
    answer_changed = left.get("answer") != right.get("answer")
    prediction_changed = left_grade.get("parsed") != right_grade.get("parsed")
    return {
        "group_id": group_key[0],
        "task_type": group_key[1],
        "target_feature_id": group_key[2],
        "left_row_id": left_id,
        "right_row_id": right_id,
        "answer_changed": answer_changed,
        "prediction_changed": prediction_changed,
        "prediction_unchanged": not prediction_changed,
        "left_valid": left_grade["valid"],
        "right_valid": right_grade["valid"],
        "left_correct": left_grade["correct"],
        "right_correct": right_grade["correct"],
        "numeric_magnitude_error": _numeric_magnitude_error(left, right, left_grade, right_grade),
    }


def _numeric_magnitude_error(left: dict[str, Any], right: dict[str, Any], left_grade: dict[str, Any], right_grade: dict[str, Any]) -> float | None:
    if left.get("answer_type") != "number" or right.get("answer_type") != "number":
        return None
    if not left_grade["valid"] or not right_grade["valid"]:
        return None
    expected_delta = float(right["answer"]) - float(left["answer"])
    predicted_delta = float(right_grade["parsed"]) - float(left_grade["parsed"])
    return abs(predicted_delta - expected_delta)


def _by_task_type(pairs: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        grouped[str(pair["task_type"])].append(pair)
    return {
        task_type: {
            "pair_count": len(items),
            "answer_flip_accuracy": _rate([item for item in items if item["answer_changed"]], "prediction_changed"),
            "false_invariance_rate": _rate([item for item in items if item["answer_changed"]], "prediction_unchanged"),
            "false_sensitivity_rate": _rate([item for item in items if not item["answer_changed"]], "prediction_changed"),
        }
        for task_type, items in sorted(grouped.items())
    }


def _rate(items: list[dict[str, Any]], field: str) -> float:
    return sum(1 for item in items if item.get(field)) / len(items) if items else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


if __name__ == "__main__":
    main()
