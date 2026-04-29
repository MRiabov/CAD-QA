from dataclasses import replace
from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.fixtures import smoke_traces
from cad_qa.jsonio import read_jsonl
from cad_qa.materialize import materialize_rows, materialize_rows_with_manifest
from cad_qa.schema import validate_public_row
from cad_qa.validation import validate_dataset_dir


def test_smoke_export_is_valid(tmp_path: Path):
    metadata = export_smoke_dataset(output_dir=tmp_path, config=DatasetConfig())

    report = validate_dataset_dir(tmp_path)
    rows = []
    for path in sorted((tmp_path / "jsonl").glob("*.jsonl")):
        rows.extend(read_jsonl(path))

    assert report["status"] == "pass"
    assert metadata["row_count"] == len(rows)
    assert metadata["row_counts_by_task_type"] == metadata[
        "exported_row_counts_by_task_type"
    ]
    assert metadata["descriptor_counts_by_task_type"]
    assert metadata["scheduled_label_counts_by_task_type"]
    assert "label_failure_counts_by_task_type" in metadata
    assert {
        "operation_count",
        "bbox_after_step",
        "signed_volume_delta",
        "topology_count_after_step",
        "point_membership",
        "feature_provenance_choice",
        "workplane_state",
        "coordinate_frame",
        "graph_query",
        "spatial_distance",
        "bbox_region_query",
        "validity_failure_prediction",
    } <= {row["task_type"] for row in rows}
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


def test_point_membership_rows_are_crisp_only():
    config = DatasetConfig()
    source, trace = smoke_traces(config)[0]
    ambiguous_query = {
        **trace.point_queries[0],
        "point": [4.99999, 0, 0],
        "point_classification": "ambiguous",
        "sampling_stratum": "near_boundary_inside",
    }

    rows = materialize_rows(
        source,
        replace(trace, point_queries=[*trace.point_queries, ambiguous_query]),
        config=config,
    )
    point_rows = [row for row in rows if row.task_type == "point_membership"]

    assert point_rows
    assert all(row.answer != "ambiguous" for row in point_rows)
    assert all("ambiguous" not in row.choices for row in point_rows if row.choices)
    assert all("ambiguous" not in row.prompt for row in point_rows)


def test_schema_rejects_ambiguous_point_membership_answer():
    errors = validate_public_row(
        {
            "id": "row",
            "dataset_version": "cadqa-v0.1",
            "task_type": "point_membership",
            "source_id": "src",
            "trace_id": "trace",
            "target_feature_id": "wp1",
            "split": "train",
            "prompt": "prompt",
            "answer_type": "enum",
            "answer": "ambiguous",
            "choices": ["inside", "outside", "on_boundary", "ambiguous"],
            "unit": None,
            "numeric_tolerance": None,
            "requires": [],
            "difficulty_tags": [],
            "labels": {},
            "diagnostics": {},
            "provenance": {"source_id": "src", "split_group": "src"},
            "parse_policy": "strict_enum_v1",
        }
    )

    assert "point_membership answer must be a point classification" in errors


def test_schema_rejects_ambiguous_provenance_answer():
    errors = validate_public_row(
        {
            "id": "row",
            "dataset_version": "cadqa-v0.1",
            "task_type": "feature_provenance_choice",
            "source_id": "src",
            "trace_id": "trace",
            "target_feature_id": "wp1",
            "split": "train",
            "prompt": "prompt",
            "answer_type": "choice",
            "answer": "ambiguous" + "_or_merged",
            "choices": ["wp1", "wp2"],
            "unit": None,
            "numeric_tolerance": None,
            "requires": [],
            "difficulty_tags": [],
            "labels": {},
            "diagnostics": {},
            "provenance": {"source_id": "src", "split_group": "src"},
            "parse_policy": "strict_enum_v1",
        }
    )

    assert "feature_provenance_choice answer must be in choices" in errors


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
    first_delta_row = next(
        row
        for row in rows
        if row.task_type == "signed_volume_delta" and row.target_feature_id == "wp1"
    )

    assert bbox_row.answer == {
        "min": [-89.24, -46.47, 36.0],
        "max": [-84.76, -37.53, 46.0],
    }
    assert bbox_row.labels["bbox_after"] == raw_bbox
    assert first_delta_row.answer == 6000
    assert first_delta_row.labels["volume_before"] == 0.0

    hole_source, hole_trace = smoke_traces(config)[1]
    hole_rows = materialize_rows(hole_source, hole_trace, config=config)
    delta_row = next(
        row
        for row in hole_rows
        if row.task_type == "signed_volume_delta" and row.target_feature_id == "wp3"
    )

    assert delta_row.answer == -31.42
    assert delta_row.labels["signed_volume_delta"] == -31.41592653589794


def test_materialization_dedupes_public_row_ids_after_scheduling():
    config = DatasetConfig()
    source, trace = smoke_traces(config)[0]
    duplicate_query = {
        **trace.point_queries[0],
        "sampling_stratum": "near_boundary_inside",
        "sample_source": "near_boundary_inside_max_x",
    }

    rows, manifest = materialize_rows_with_manifest(
        source,
        replace(trace, point_queries=[*trace.point_queries, duplicate_query]),
        config=config,
    )
    row_ids = [row.id for row in rows]

    assert len(row_ids) == len(set(row_ids))
    assert manifest["exported_row_counts_by_task_type"]["point_membership"] == len(
        [row for row in rows if row.task_type == "point_membership"]
    )
