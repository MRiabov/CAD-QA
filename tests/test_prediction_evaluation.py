from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json, read_jsonl, write_json, write_jsonl
from cad_qa.predictions import (
    normalize_prediction_artifact,
    normalize_prediction_records,
)
from scripts.evaluation.evaluate_prediction_responses import (
    main as evaluate_predictions_main,
)


def test_prediction_normalizer_accepts_mapping_and_records():
    assert normalize_prediction_artifact({"row_a": 3}) == {"row_a": "3"}
    assert normalize_prediction_artifact({"predictions": {"row_a": "inside"}}) == {
        "row_a": "inside"
    }
    assert normalize_prediction_records([{"row_id": "row_a", "prediction": "2"}]) == {
        "row_a": "2"
    }


def test_prediction_normalizer_accepts_provider_shapes():
    records = [
        {
            "custom_id": "row_a",
            "response": {"body": {"choices": [{"message": {"content": "4"}}]}},
        },
        {"row_id": "row_b", "output_text": "outside"},
    ]

    assert normalize_prediction_records(records) == {"row_a": "4", "row_b": "outside"}


def test_evaluate_prediction_responses_scores_jsonl(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "eval"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())
    rows_path = dataset_dir / "jsonl" / "validation.jsonl"
    rows = read_jsonl(rows_path)
    write_jsonl(
        tmp_path / "responses.jsonl",
        [{"row_id": row["id"], "prediction": row["answer"]} for row in rows],
    )

    evaluate_predictions_main(
        [
            "--rows",
            str(rows_path),
            "--responses",
            str(tmp_path / "responses.jsonl"),
            "--output-dir",
            str(output_dir),
            "--label",
            "fewshot",
        ]
    )

    report = read_json(output_dir / "prediction_evaluation_report.json")
    assert report["label"] == "fewshot"
    assert report["missing_prediction_count"] == 0
    assert report["metrics"]["accuracy"] == 1.0


def test_evaluate_prediction_responses_scores_json_mapping(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "eval"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())
    rows_path = dataset_dir / "jsonl" / "validation.jsonl"
    rows = read_jsonl(rows_path)
    write_json(tmp_path / "responses.json", {row["id"]: row["answer"] for row in rows})

    evaluate_predictions_main(
        [
            "--rows",
            str(rows_path),
            "--responses",
            str(tmp_path / "responses.json"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert read_json(output_dir / "prediction_metrics.json")["accuracy"] == 1.0
