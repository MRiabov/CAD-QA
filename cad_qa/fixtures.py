"""Deterministic smoke fixtures with precomputed trace metadata."""

from __future__ import annotations

from dataclasses import asdict

from cad_qa.config import DatasetConfig
from cad_qa.hashing import sha256_json
from cad_qa.operation_graph import (
    extract_operation_graph,
    operation_graph_hash,
    operation_nodes_to_dicts,
)
from cad_qa.schema import SourceRecord, TraceRecord
from cad_qa.source import source_record_from_code


BOX_CODE = """\
import cadquery as cq

wp0 = cq.Workplane("XY")
wp1 = wp0.box(10, 20, 30)
result = wp1
"""

HOLE_CODE = """\
import cadquery as cq

wp0 = cq.Workplane("XY")
wp1 = wp0.box(10, 10, 10)
wp2 = wp1.faces(">Z").workplane()
wp3 = wp2.hole(2)
result = wp3
"""

ADVANCED_HUMAN_NOTES_CODE = """\
import cadquery as cq

wp0 = cq.Workplane("XY")
box_a = wp0.box(1, 2, 3)
box_b = cq.Workplane("XY").box(4, 5, 6)
feature_after_box_2 = box_b.extrude(2)
hole_1_wp = feature_after_box_2.faces(">Z").workplane().center(-1.5, 0)
hole_1 = hole_1_wp.hole(1)
hole_2_wp = hole_1.faces(">Z").workplane().center(0, 0)
hole_2 = hole_2_wp.hole(1)
hole_3_wp = hole_2.faces(">Z").workplane().center(1.5, 0)
hole_3 = hole_3_wp.hole(1)
result = hole_3
"""


def smoke_source_records(config: DatasetConfig) -> list[SourceRecord]:
    return [
        source_record_from_code(
            "synthetic/box.py", BOX_CODE, source="synthetic", config=config
        ),
        source_record_from_code(
            "synthetic/hole.py", HOLE_CODE, source="synthetic", config=config
        ),
        source_record_from_code(
            "synthetic/advanced_human_notes.py",
            ADVANCED_HUMAN_NOTES_CODE,
            source="synthetic",
            config=config,
        ),
    ]


def smoke_traces(config: DatasetConfig) -> list[tuple[SourceRecord, TraceRecord]]:
    records = smoke_source_records(config)
    return [
        (records[0], _box_trace(records[0], config)),
        (records[1], _hole_trace(records[1], config)),
        (records[2], _advanced_human_notes_trace(records[2], config)),
    ]


def _box_trace(source: SourceRecord, config: DatasetConfig) -> TraceRecord:
    nodes, result_variable, _ = extract_operation_graph(source.normalized_code)
    graph_hash = operation_graph_hash(nodes)
    snapshots = [
        _snapshot("wp1", 1, 10 * 20 * 30, [-5, -10, -15], [5, 10, 15], 6, 12, 8),
    ]
    payload = {
        "source_id": source.source_id,
        "graph_hash": graph_hash,
        "snapshots": snapshots,
    }
    return TraceRecord(
        trace_id="trace_" + sha256_json(payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status="ok",
        execution_status="ok",
        result_variable=result_variable,
        operation_nodes=operation_nodes_to_dicts(nodes),
        snapshots=snapshots,
        label_policy=asdict(config.label_policy),
        environment={
            "python_version": "synthetic",
            "cadquery_version": "synthetic",
            "ocp_version": "synthetic",
        },
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(payload),
            "geometry_hash": sha256_json(
                {"snapshots": snapshots, "label_policy": asdict(config.label_policy)}
            ),
            "config_hash": config.config_hash,
        },
        failure_reason=None,
        point_queries=[
            {
                "point": [0, 0, 0],
                "target_feature_id": "wp1",
                "point_classification": "inside",
                "sampling_stratum": "deep_inside",
            },
            {
                "point": [6, 0, 0],
                "target_feature_id": "wp1",
                "point_classification": "outside",
                "sampling_stratum": "deep_outside",
            },
            {
                "point": [5, 0, 0],
                "target_feature_id": "wp1",
                "point_classification": "on_boundary",
                "sampling_stratum": "on_boundary",
            },
        ],
        provenance_records=[
            {
                "target_description": "interior point [0, 0, 0]",
                "target_feature_id": "wp1",
                "provenance_relation": "created_by",
                "answer_feature_id": "wp1",
                "matching_method": "synthetic_fixture",
                "provenance_confidence": 1.0,
            }
        ],
    )


def _hole_trace(source: SourceRecord, config: DatasetConfig) -> TraceRecord:
    nodes, result_variable, _ = extract_operation_graph(source.normalized_code)
    graph_hash = operation_graph_hash(nodes)
    volume_before = 1000.0
    volume_after = 1000.0 - 3.141592653589793 * 1.0 * 1.0 * 10.0
    snapshots = [
        _snapshot("wp1", 1, volume_before, [-5, -5, -5], [5, 5, 5], 6, 12, 8),
        _snapshot("wp2", 2, volume_before, [-5, -5, -5], [5, 5, 5], 6, 12, 8),
        _snapshot("wp3", 3, volume_after, [-5, -5, -5], [5, 5, 5], 7, 15, 10),
    ]
    selector_tables = [
        {
            "selector_expression": 'wp1.faces(">Z")',
            "target_feature_id": "wp2",
            "entity_type": "face",
            "raw_entity_ids": ["face_top"],
            "dedup_entity_ids": ["face_top"],
            "selected_count": 1,
            "status": "ok",
        }
    ]
    payload = {
        "source_id": source.source_id,
        "graph_hash": graph_hash,
        "snapshots": snapshots,
        "selector_tables": selector_tables,
    }
    return TraceRecord(
        trace_id="trace_" + sha256_json(payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status="ok",
        execution_status="ok",
        result_variable=result_variable,
        operation_nodes=operation_nodes_to_dicts(nodes),
        snapshots=snapshots,
        label_policy=asdict(config.label_policy),
        environment={
            "python_version": "synthetic",
            "cadquery_version": "synthetic",
            "ocp_version": "synthetic",
        },
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(payload),
            "geometry_hash": sha256_json(
                {"snapshots": snapshots, "label_policy": asdict(config.label_policy)}
            ),
            "config_hash": config.config_hash,
        },
        failure_reason=None,
        selector_tables=selector_tables,
        point_queries=[
            {
                "point": [0, 0, 0],
                "target_feature_id": "wp3",
                "point_classification": "outside",
                "sampling_stratum": "inside_removed_cut",
            },
            {
                "point": [4, 4, 0],
                "target_feature_id": "wp3",
                "point_classification": "inside",
                "sampling_stratum": "deep_inside",
            },
        ],
        provenance_records=[
            {
                "target_description": "cylindrical hole wall",
                "target_feature_id": "wp3",
                "provenance_relation": "created_by",
                "answer_feature_id": "wp3",
                "matching_method": "synthetic_fixture",
                "provenance_confidence": 1.0,
            },
            {
                "target_description": "top circular edge bounded by the original top face and hole",
                "target_feature_id": "wp3",
                "provenance_relation": "bounded_by",
                "answer_feature_id": "wp3",
                "matching_method": "synthetic_fixture",
                "provenance_confidence": 0.95,
            },
        ],
    )


def _advanced_human_notes_trace(source: SourceRecord, config: DatasetConfig) -> TraceRecord:
    nodes, result_variable, _ = extract_operation_graph(source.normalized_code)
    graph_hash = operation_graph_hash(nodes)
    hole_removed_volume = 3.141592653589793 * 0.5 * 0.5 * 8.0
    snapshots = [
        _snapshot("box_a", 1, 6.0, [-0.5, -1.0, -1.5], [0.5, 1.0, 1.5], 6, 12, 8),
        _snapshot("box_b", 3, 120.0, [-2.0, -2.5, -3.0], [2.0, 2.5, 3.0], 6, 12, 8),
        _snapshot("feature_after_box_2", 4, 160.0, [-2.0, -2.5, -3.0], [2.0, 2.5, 5.0], 8, 20, 12),
        _snapshot("hole_1", 8, 160.0 - hole_removed_volume, [-2.0, -2.5, -3.0], [2.0, 2.5, 5.0], 9, 23, 14),
        _snapshot("hole_2", 12, 160.0 - (2 * hole_removed_volume), [-2.0, -2.5, -3.0], [2.0, 2.5, 5.0], 10, 26, 16),
        _snapshot("hole_3", 16, 160.0 - (3 * hole_removed_volume), [-2.0, -2.5, -3.0], [2.0, 2.5, 5.0], 11, 29, 18),
    ]
    spatial_queries = [
        {
            "query_id": "component_distance__hole__1__hole__3__x",
            "target_feature_id": "hole_3",
            "query_kind": "axis_component_distance",
            "component_axis": "X",
            "reference_a": {
                "name": "hole #1 center",
                "operation": "hole",
                "ordinal": 1,
                "point": [-1.5, 0.0, 0.0],
                "source": "hole_1",
            },
            "reference_b": {
                "name": "hole #3 center",
                "operation": "hole",
                "ordinal": 3,
                "point": [1.5, 0.0, 0.0],
                "source": "hole_3",
            },
            "answer": 3.0,
            "reference_status": "ok",
        },
        {
            "query_id": "centerline_distance__hole__1__hole__2",
            "target_feature_id": "hole_2",
            "query_kind": "centerline_to_centerline_distance",
            "reference_a": {
                "name": "hole #1",
                "reference_kind": "centerline",
                "operation": "hole",
                "ordinal": 1,
                "axis_point": [-1.5, 0.0, 0.0],
                "axis_direction": [0.0, 0.0, 1.0],
                "source": "hole_1",
            },
            "reference_b": {
                "name": "hole #2",
                "reference_kind": "centerline",
                "operation": "hole",
                "ordinal": 2,
                "axis_point": [0.0, 0.0, 0.0],
                "axis_direction": [0.0, 0.0, 1.0],
                "source": "hole_2",
            },
            "answer": 1.5,
            "reference_status": "ok",
        },
    ]
    payload = {
        "source_id": source.source_id,
        "graph_hash": graph_hash,
        "snapshots": snapshots,
        "spatial_queries": spatial_queries,
    }
    return TraceRecord(
        trace_id="trace_" + sha256_json(payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status="ok",
        execution_status="ok",
        result_variable=result_variable,
        operation_nodes=operation_nodes_to_dicts(nodes),
        snapshots=snapshots,
        label_policy=asdict(config.label_policy),
        environment={
            "python_version": "synthetic",
            "cadquery_version": "synthetic",
            "ocp_version": "synthetic",
        },
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(payload),
            "geometry_hash": sha256_json(
                {"snapshots": snapshots, "label_policy": asdict(config.label_policy)}
            ),
            "config_hash": config.config_hash,
        },
        failure_reason=None,
        spatial_queries=spatial_queries,
        point_queries=[
            {
                "point": [0.0, 0.0, 0.0],
                "target_feature_id": "feature_after_box_2",
                "point_classification": "inside",
                "sampling_stratum": "deep_inside",
            }
        ],
        provenance_records=[
            {
                "target_description": "material added by the extrude after box #2",
                "target_feature_id": "feature_after_box_2",
                "provenance_relation": "created_by",
                "answer_feature_id": "feature_after_box_2",
                "matching_method": "synthetic_fixture",
                "provenance_confidence": 1.0,
            }
        ],
    )


def _snapshot(
    feature_id: str,
    step_index: int,
    volume: float,
    bbox_min: list[float],
    bbox_max: list[float],
    faces: int,
    edges: int,
    vertices: int,
) -> dict[str, object]:
    return {
        "snapshot_id": f"snap_{feature_id}_{step_index:04d}",
        "feature_id": feature_id,
        "step_index": step_index,
        "shape_status": "ok",
        "volume": volume,
        "bbox": {"min": bbox_min, "max": bbox_max},
        "topology": {
            "solid_count": 1,
            "face_count": faces,
            "edge_count": edges,
            "vertex_count": vertices,
            "wire_count": None,
            "planar_face_count": None,
            "cylindrical_face_count": None,
            "circular_edge_count": None,
            "x_parallel_edge_count": None,
            "y_parallel_edge_count": None,
            "z_parallel_edge_count": None,
        },
        "entity_ids": None,
        "diagnostics": {"source": "synthetic_fixture"},
    }
