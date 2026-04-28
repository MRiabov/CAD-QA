from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json
from scripts.evaluation.tool_assisted_upper_bound import main as upper_bound_main


def test_tool_assisted_upper_bound_is_oracle(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "upper_bound"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())

    upper_bound_main([str(dataset_dir / "jsonl" / "train.jsonl"), "--output-dir", str(output_dir)])

    report = read_json(output_dir / "tool_assisted_upper_bound.json")
    assert report["mode"] == "trace_label_oracle"
    assert report["metrics"]["accuracy"] == 1.0
