from pathlib import Path

from cad_qa.jsonio import read_json, write_json, write_jsonl
from scripts.evaluation.evaluate_cadedit_predictions import cadedit_report
from scripts.evaluation.evaluate_counterfactual_sensitivity import (
    evaluate_counterfactual_sensitivity,
)
from scripts.experiments.build_task_transfer_matrix import (
    build_transfer_matrix,
    main as transfer_main,
)


def test_counterfactual_sensitivity_reports_prediction_flips():
    rows = [
        _row("a", "g", 1, "1"),
        _row("b", "g", 2, "2"),
    ]
    pairs, report = evaluate_counterfactual_sensitivity(rows, {"a": "1", "b": "2"})

    assert len(pairs) == 1
    assert report["answer_flip_accuracy"] == 1.0
    assert report["false_invariance_rate"] == 0.0


def test_cadedit_report_exposes_verifier_metrics():
    rows = [
        {
            "id": "edit1",
            "task_type": "parameter_edit_direction",
            "split": "validation",
            "parse_policy": "strict_enum_v1",
            "answer": "increase",
            "choices": ["increase", "decrease"],
            "diagnostics": {"failure_reason": None},
        }
    ]
    metrics = {
        "accuracy": 1.0,
        "invalid_output_rate": 0.0,
        "by_task_type": {
            "parameter_edit_direction": {
                "accuracy": 1.0,
                "row_count": 1,
                "invalid_output_rate": 0.0,
            }
        },
    }

    report = cadedit_report(rows, {"edit1": "increase"}, metrics)

    assert report["exact_candidate_accuracy"] == 1.0
    assert report["target_satisfaction_rate"] == 1.0


def test_task_transfer_matrix_writes_json_and_csv(tmp_path: Path):
    metrics = tmp_path / "metrics.json"
    output_dir = tmp_path / "transfer"
    write_json(
        metrics,
        {
            "by_task_type": {
                "operation_count": {
                    "row_count": 2,
                    "accuracy": 0.5,
                    "invalid_output_rate": 0.0,
                },
                "point_membership": {
                    "row_count": 1,
                    "accuracy": 1.0,
                    "invalid_output_rate": 0.0,
                },
            }
        },
    )

    report = build_transfer_matrix([f"static={metrics}"])
    transfer_main(["--metric", f"static={metrics}", "--output-dir", str(output_dir)])

    assert report["cell_count"] == 2
    assert read_json(output_dir / "task_transfer_matrix.json")["cell_count"] == 2
    assert (output_dir / "task_transfer_matrix.csv").exists()


def _row(row_id: str, group_id: str, answer: int, prediction: str) -> dict[str, object]:
    del prediction
    return {
        "id": row_id,
        "task_type": "operation_count",
        "target_feature_id": "wp1",
        "trace_id": group_id,
        "answer_type": "integer",
        "parse_policy": "strict_integer_v1",
        "answer": answer,
        "provenance": {"counterfactual_group_id": group_id},
    }
