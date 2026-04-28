from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json, read_jsonl
from cad_qa.validation import validate_record_file
from scripts.dataset.materialize_cadedit_repair_tasks import main as repair_main


def test_materialize_selector_repair_rows(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "repairs"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())

    repair_main([str(dataset_dir), "--output-dir", str(output_dir)])

    rows = []
    for path in sorted((output_dir / "jsonl").glob("*.jsonl")):
        assert validate_record_file(path, "row")["status"] == "pass"
        rows.extend(read_jsonl(path))
    metadata = read_json(output_dir / "metadata.json")
    assert metadata["row_count"] == len(rows)
    assert rows
    assert {"selector_repair", "workplane_offset_repair"} <= {row["task_type"] for row in rows}
    assert all(row["answer"] in row["choices"] for row in rows)
