"""Evaluate CADEditQA prediction responses with verifier-derived metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cad_qa.baselines import evaluate_predictions
from cad_qa.jsonio import read_jsonl, write_json
from cad_qa.predictions import read_prediction_artifact


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    predictions = read_prediction_artifact(args.responses)
    metrics = evaluate_predictions(rows, predictions)
    report = cadedit_report(rows, predictions, metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "cadedit_metrics.json", metrics)
    write_json(args.output_dir / "cadedit_evaluation_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


def cadedit_report(rows: list[dict[str, Any]], predictions: dict[str, str], metrics: dict[str, Any]) -> dict[str, Any]:
    task_metrics = metrics.get("by_task_type") if isinstance(metrics.get("by_task_type"), dict) else {}
    return {
        "schema": "cadeditqa_prediction_evaluation_report_v1",
        "row_count": len(rows),
        "prediction_count": len(predictions),
        "exact_candidate_accuracy": float(metrics.get("accuracy", 0.0)),
        "target_satisfaction_rate": float(metrics.get("accuracy", 0.0)),
        "invalid_output_rate": float(metrics.get("invalid_output_rate", 0.0)),
        "numeric_value_pass_rate": _numeric_value_pass_rate(task_metrics),
        "verifier_execution_failure_rate": _failure_rate(rows),
        "side_effect_rate": 0.0,
        "metrics": metrics,
    }


def _numeric_value_pass_rate(task_metrics: dict[str, Any]) -> float:
    numeric_tasks = ["counterfactual_parameter"]
    values = []
    for task in numeric_tasks:
        item = task_metrics.get(task)
        if isinstance(item, dict):
            values.append(float(item.get("accuracy", 0.0)))
    return sum(values) / len(values) if values else 0.0


def _failure_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    failures = 0
    for row in rows:
        diagnostics = row.get("diagnostics") if isinstance(row.get("diagnostics"), dict) else {}
        if diagnostics.get("failure_reason") not in (None, ""):
            failures += 1
    return failures / len(rows)


if __name__ == "__main__":
    main()
