from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json
from scripts.training.prepare_answer_sft_dataset import main as prepare_sft_main
from scripts.training.text_sft_train_unsloth import main as train_main


def test_text_sft_train_dry_run_writes_result(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    sft_dir = tmp_path / "sft"
    output_dir = tmp_path / "train"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())
    prepare_sft_main(["--dataset-dir", str(dataset_dir), "--output-dir", str(sft_dir), "--max-train-rows", "4", "--max-eval-rows", "2"])

    train_main(["--dataset-dir", str(dataset_dir), "--sft-dir", str(sft_dir), "--output-dir", str(output_dir), "--dry-run"])

    result = read_json(output_dir / "train_result.json")
    assert result["status"] == "dry_run"
    assert result["train_count"] == 4
    assert result["eval_count"] == 2
