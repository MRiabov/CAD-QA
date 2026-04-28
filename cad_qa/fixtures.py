"""Deterministic smoke fixtures with precomputed trace metadata."""

from __future__ import annotations

from dataclasses import asdict

from cad_qa.config import DatasetConfig
from cad_qa.hashing import sha256_json
from cad_qa.operation_graph import extract_operation_graph, operation_graph_hash, operation_nodes_to_dicts
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


def smoke_source_records(config: DatasetConfig) -> list[SourceRecord]:
    return [
        source_record_from_code("synthetic/box.py", BOX_CODE, source="synthetic", config=config),
        source_record_from_code("synthetic/hole.py", HOLE_CODE, source="synthetic", config=config),
    ]


def smoke_traces(config: DatasetConfig) -> list[tuple[SourceRecord, TraceRecord]]:
    records = smoke_source_records(config)
    return [(records[0], _box_trace(records[0], config)), (records[1], _hole_trace(records[1], config))]


def _box_trace(source: SourceRecord, config: DatasetConfig) -> TraceRecord:
    nodes, result_variable, _ = extract_operation_graph(source.normalized_code)
    graph_hash = operation_graph_hash(nodes)
    snapshots = [
        _snapshot("wp1", 1, 10 * 20 * 30, [-5, -10, -15], [5, 10, 15], 6, 12, 8),
    ]
    payload = {"source_id": source.source_id, "graph_hash": graph_hash, "snapshots": snapshots}
    return TraceRecord(
        trace_id="trace_" + sha256_json(payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status="ok",
        execution_status="ok",
        result_variable=result_variable,
        operation_nodes=operation_nodes_to_dicts(nodes),
        snapshots=snapshots,
        label_policy=asdict(config.label_policy),
        environment={"python_version": "synthetic", "cadquery_version": "synthetic", "ocp_version": "synthetic"},
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(payload),
            "geometry_hash": sha256_json({"snapshots": snapshots, "label_policy": asdict(config.label_policy)}),
            "config_hash": config.config_hash,
        },
        failure_reason=None,
        point_queries=[
            {"point": [0, 0, 0], "target_feature_id": "wp1", "point_classification": "inside", "sampling_stratum": "deep_inside"},
            {"point": [6, 0, 0], "target_feature_id": "wp1", "point_classification": "outside", "sampling_stratum": "deep_outside"},
            {"point": [5, 0, 0], "target_feature_id": "wp1", "point_classification": "on_boundary", "sampling_stratum": "on_boundary"},
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
    payload = {"source_id": source.source_id, "graph_hash": graph_hash, "snapshots": snapshots, "selector_tables": selector_tables}
    return TraceRecord(
        trace_id="trace_" + sha256_json(payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status="ok",
        execution_status="ok",
        result_variable=result_variable,
        operation_nodes=operation_nodes_to_dicts(nodes),
        snapshots=snapshots,
        label_policy=asdict(config.label_policy),
        environment={"python_version": "synthetic", "cadquery_version": "synthetic", "ocp_version": "synthetic"},
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(payload),
            "geometry_hash": sha256_json({"snapshots": snapshots, "label_policy": asdict(config.label_policy)}),
            "config_hash": config.config_hash,
        },
        failure_reason=None,
        selector_tables=selector_tables,
        point_queries=[
            {"point": [0, 0, 0], "target_feature_id": "wp3", "point_classification": "outside", "sampling_stratum": "inside_removed_cut"},
            {"point": [4, 4, 0], "target_feature_id": "wp3", "point_classification": "inside", "sampling_stratum": "deep_inside"},
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
