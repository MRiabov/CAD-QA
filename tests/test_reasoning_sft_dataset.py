from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json, read_jsonl
from scripts.training.prepare_reasoning_sft_dataset import main as reasoning_sft_main


def test_prepare_reasoning_sft_dataset(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "reasoning_sft"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())

    reasoning_sft_main(
        [
            "--dataset-dir",
            str(dataset_dir),
            "--output-dir",
            str(output_dir),
            "--max-train-rows",
            "5",
            "--max-eval-rows",
            "3",
        ]
    )

    train = read_jsonl(output_dir / "train.jsonl")
    report = read_json(output_dir / "reasoning_sft_dataset_report.json")
    assert report["rationale_policy"] == "trace_grounded_template_v1"
    assert report["train_row_count"] == 5
    assert "Reasoning:" in train[0]["messages"][1]["content"]
    assert "Final answer:" in train[0]["messages"][1]["content"]
