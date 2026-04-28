from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json, read_jsonl
from scripts.training.prepare_sft_ablation_datasets import main as ablation_main
from scripts.training.prepare_sft_scaling_datasets import main as scaling_main


def test_prepare_sft_ablation_datasets(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "ablations"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())

    ablation_main(["--dataset-dir", str(dataset_dir), "--output-dir", str(output_dir), "--max-train-rows", "10"])

    manifest = read_json(output_dir / "sft_ablation_manifest.json")
    assert set(manifest["ablations"]) >= {"all_tasks", "no_static", "numeric_only", "topology_selector"}
    assert read_jsonl(output_dir / "all_tasks" / "train.jsonl")
    assert all(row["task_type"] != "operation_count" for row in read_jsonl(output_dir / "no_static" / "train.jsonl"))


def test_prepare_sft_scaling_datasets(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "scaling"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())

    scaling_main(["--dataset-dir", str(dataset_dir), "--output-dir", str(output_dir), "--sizes", "3", "8"])

    manifest = read_json(output_dir / "sft_scaling_manifest.json")
    assert manifest["sizes"]["train_3"]["train_row_count"] == 3
    assert manifest["sizes"]["train_8"]["train_row_count"] == 8
    assert len(read_jsonl(output_dir / "train_3" / "train.jsonl")) == 3
