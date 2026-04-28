from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json, read_jsonl, write_json
from cad_qa.baselines import run_baselines
from scripts.experiments.compare_experiment_runs import build_comparison_report, main as compare_main


def test_compare_experiment_runs_flattens_baseline_metrics(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())
    rows = read_jsonl(dataset_dir / "jsonl" / "train.jsonl")
    write_json(run_dir / "baseline_metrics.json", run_baselines(rows))

    report = build_comparison_report([run_dir])

    assert report["status"] == "pass"
    assert report["best_by_accuracy"]["system"] == "oracle"
    assert {row["system"] for row in report["headline_rows"]} >= {"majority", "oracle"}
    assert any(row["task_type"] == "operation_count" for row in report["task_family_rows"])


def test_compare_experiment_runs_writes_report_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    output_dir = tmp_path / "comparison"
    write_json(
        run_dir / "baseline_metrics.json",
        {
            "model_a": {
                "row_count": 2,
                "accuracy": 0.5,
                "invalid_output_rate": 0.0,
                "by_task_type": {"operation_count": {"row_count": 2, "accuracy": 0.5, "invalid_output_rate": 0.0}},
                "by_split": {"validation": {"row_count": 2, "accuracy": 0.5, "invalid_output_rate": 0.0}},
            }
        },
    )

    compare_main([str(run_dir), "--output-dir", str(output_dir)])

    assert read_json(output_dir / "experiment_comparison.json")["metric_record_count"] == 1
    assert (output_dir / "headline_comparison.csv").exists()
    assert (output_dir / "experiment_comparison.md").exists()
