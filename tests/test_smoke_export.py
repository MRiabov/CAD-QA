from dataclasses import replace
from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.fixtures import smoke_traces
from cad_qa.jsonio import read_jsonl
from cad_qa.materialize import materialize_rows
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


def test_public_numeric_answers_are_rounded_but_raw_labels_are_preserved():
    config = DatasetConfig()
    source, trace = smoke_traces(config)[0]
    raw_bbox = {
        "min": [-89.2360679774998, -46.47213595499959, 36.0],
        "max": [-84.76393202250023, -37.52786404500043, 46.0],
    }
    snapshots = [{**trace.snapshots[0], "bbox": raw_bbox}]
    rows = materialize_rows(source, replace(trace, snapshots=snapshots), config=config)
    bbox_row = next(row for row in rows if row.task_type == "bbox_after_step")

    assert bbox_row.answer == {"min": [-89.24, -46.47, 36.0], "max": [-84.76, -37.53, 46.0]}
    assert bbox_row.labels["bbox_after"] == raw_bbox

    hole_source, hole_trace = smoke_traces(config)[1]
    hole_rows = materialize_rows(hole_source, hole_trace, config=config)
    delta_row = next(row for row in hole_rows if row.task_type == "signed_volume_delta" and row.target_feature_id == "wp3")

    assert delta_row.answer == -31.42
    assert delta_row.labels["signed_volume_delta"] == -31.41592653589794
