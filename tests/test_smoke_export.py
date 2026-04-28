from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_jsonl
from cad_qa.validation import validate_dataset_dir


def test_smoke_export_is_valid(tmp_path: Path):
    metadata = export_smoke_dataset(output_dir=tmp_path, config=DatasetConfig())

    report = validate_dataset_dir(tmp_path)
    rows = []
    for path in sorted((tmp_path / "jsonl").glob("*.jsonl")):
        rows.extend(read_jsonl(path))

    assert report["status"] == "pass"
    assert metadata["row_count"] == len(rows)
    assert {"operation_count", "bbox_after_step", "signed_volume_delta", "topology_count_after_step", "point_membership", "feature_provenance_choice", "workplane_state", "coordinate_frame"} <= {
        row["task_type"] for row in rows
    }
    assert (tmp_path / "metadata.json").exists()
    assert (tmp_path / "split_manifest.json").exists()
    assert (tmp_path / "failure_manifest.jsonl").exists()
    assert metadata["parquet_export"]["status"] in {"skipped", "written"}


def test_public_rows_do_not_leak_local_paths(tmp_path: Path):
    export_smoke_dataset(output_dir=tmp_path, config=DatasetConfig())

    for path in sorted((tmp_path / "jsonl").glob("*.jsonl")):
        for row in read_jsonl(path):
            assert "source_root" not in row["provenance"]
            assert "cache_path" not in row["provenance"]
