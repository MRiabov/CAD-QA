"""Selfcheck artifact generation for synthesized query families."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cad_qa.dataset.materialize import materialize_row
from cad_qa.dataset.preview import (
    DEFAULT_PREVIEW_EVIDENCE_FILENAME,
    dataset_preview_evidence_report,
    dataset_preview_markdown,
)
from cad_qa.io import to_jsonable, write_json, write_jsonl
from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph, Relation
from cad_qa.query.resolver import resolve_query
from cad_qa.query.synthesis import synthesize_graph_hop_queries


SYNTHESIS_SELFCHECK_FAMILIES = (
    "parameterized_feature_extreme",
    "parameterized_feature_rank",
    "parameterized_feature_effect_delta_extreme",
    "parameterized_material_region_extreme",
    "parameterized_material_region_rank",
    "parameterized_void_region_extreme",
    "parameterized_void_region_rank",
    "parameterized_kernel_face_extreme",
    "parameterized_kernel_edge_extreme",
    "parameterized_kernel_face_rank",
    "parameterized_kernel_edge_rank",
    "parameterized_face_spatial_relation_extreme",
    "parameterized_edge_spatial_relation_extreme",
    "parameterized_equal_face_metric_extreme",
    "parameterized_equal_edge_metric_extreme",
    "parameterized_equal_feature_metric_extreme",
    "parameterized_feature_reference_feature_distance",
    "parameterized_feature_reference_face_distance",
    "parameterized_feature_reference_edge_distance",
    "parameterized_feature_reference_endpoint_distance",
    "parameterized_feature_reference_entity_distance",
    "parameterized_equal_endpoint_metric_extreme",
    "parameterized_contained_endpoint_metric_extreme",
    "parameterized_endpoint_reference_feature_distance",
    "parameterized_endpoint_reference_face_distance",
    "parameterized_endpoint_reference_edge_distance",
    "parameterized_endpoint_reference_endpoint_distance",
    "parameterized_endpoint_reference_entity_distance",
    "parameterized_equal_material_region_metric_extreme",
    "parameterized_equal_void_region_metric_extreme",
    "parameterized_material_region_reference_feature_distance",
    "parameterized_material_region_reference_face_distance",
    "parameterized_material_region_reference_edge_distance",
    "parameterized_material_region_reference_endpoint_distance",
    "parameterized_material_region_reference_entity_distance",
    "parameterized_void_region_reference_feature_distance",
    "parameterized_void_region_reference_face_distance",
    "parameterized_void_region_reference_edge_distance",
    "parameterized_void_region_reference_endpoint_distance",
    "parameterized_void_region_reference_entity_distance",
    "parameterized_face_reference_feature_distance",
    "parameterized_face_reference_face_distance",
    "parameterized_face_reference_edge_distance",
    "parameterized_face_reference_endpoint_distance",
    "parameterized_face_reference_entity_distance",
    "parameterized_edge_reference_feature_distance",
    "parameterized_edge_reference_face_distance",
    "parameterized_edge_reference_edge_distance",
    "parameterized_edge_reference_endpoint_distance",
    "parameterized_edge_reference_entity_distance",
    "parameterized_path_point_extreme",
    "parameterized_path_segment_extreme",
    "parameterized_kernel_face_selector_count",
    "parameterized_kernel_edge_selector_count",
)


def synthesis_selfcheck_graphs() -> list[OntologyGraph]:
    """Return deterministic synthetic graphs that exercise synthesized families."""

    return [
        _face_metric_graph(),
        _edge_metric_graph(),
        _face_rank_graph("graph:selfcheck-face-rank-0"),
        _face_rank_graph("graph:selfcheck-face-rank-1"),
        _face_rank_graph("graph:selfcheck-face-rank-2"),
        _face_deep_rank_graph("graph:face-rank-sample:1"),
        _edge_rank_graph("graph:selfcheck-edge-rank-0"),
        _edge_rank_graph("graph:selfcheck-edge-rank-1"),
        _edge_rank_graph("graph:selfcheck-edge-rank-2"),
        _edge_deep_rank_graph("graph:rank-sample:7"),
        _feature_rank_graph("graph:feature-rank-sample:4"),
        _feature_rank_graph("graph:feature-rank-sample:0"),
        _region_rank_graph("graph:material-region-rank-sample:1"),
        _region_rank_graph("graph:material-region-rank-sample:0"),
        _region_rank_graph("graph:void-region-rank-sample:11"),
        _region_rank_graph("graph:void-region-rank-sample:0"),
        _face_spatial_relation_graph("graph:selfcheck-face-spatial-relation-0"),
        _face_spatial_relation_graph("graph:selfcheck-face-spatial-relation-2"),
        _face_spatial_relation_graph("graph:selfcheck-face-spatial-relation-4"),
        _face_spatial_relation_graph("graph:selfcheck-face-spatial-relation-8"),
        _edge_spatial_relation_graph("graph:selfcheck-edge-spatial-relation-0"),
        _edge_spatial_relation_graph("graph:selfcheck-edge-spatial-relation-1"),
        _edge_spatial_relation_graph("graph:selfcheck-edge-spatial-relation-2"),
        _edge_spatial_relation_graph("graph:selfcheck-edge-spatial-relation-4"),
        _edge_same_length_relation_graph(),
        _edge_single_relation_graph("graph:selfcheck-edge-parallel-relation", "parallel_to"),
        _edge_single_relation_graph("graph:selfcheck-edge-longer-relation", "longer_than"),
        _edge_single_relation_graph("graph:selfcheck-edge-shorter-relation", "shorter_than"),
        _face_single_relation_graph("graph:selfcheck-face-parallel-relation", "parallel_to"),
        _feature_effect_delta_graph("graph:selfcheck-feature-effect-delta-0"),
        _feature_effect_delta_graph("graph:selfcheck-feature-effect-delta-6"),
        _feature_effect_delta_graph("graph:selfcheck-feature-effect-delta-10"),
        _feature_equal_metric_graph(),
        _region_equal_metric_graph(),
        _face_equal_metric_graph(),
        _edge_equal_metric_graph(),
        _endpoint_equal_metric_graph(),
        _path_metric_graph(),
        _face_selector_count_graph(),
        _edge_selector_count_graph(),
        _face_selector_relation_count_graph(),
        _edge_selector_relation_count_graph(),
        _edge_selector_equal_metric_count_graph(),
    ]


def synthesis_selfcheck_rows() -> tuple[list[dict[str, Any]], list[OntologyGraph], list[dict[str, Any]]]:
    """Materialize resolved rows for all currently implemented synthesized families."""

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    graphs = synthesis_selfcheck_graphs()
    families = set(SYNTHESIS_SELFCHECK_FAMILIES)
    for graph in graphs:
        for query in synthesize_graph_hop_queries(graph):
            family = query.query_id.rsplit(":", 1)[-1]
            if family not in families:
                continue
            resolution = resolve_query(graph, query)
            if resolution.verifier_status == "resolved":
                rows.append(to_jsonable(materialize_row(graph, resolution)))
            else:
                failures.append(
                    {
                        "graph_id": graph.graph_id,
                        "query_id": query.query_id,
                        "verifier_status": resolution.verifier_status,
                        "failure_reason": resolution.candidate_trace.failure_reason,
                        "candidate_trace": to_jsonable(resolution.candidate_trace),
                    }
                )
    return rows, graphs, failures


def write_synthesis_selfcheck(out: Path, *, sample_per_family: int = 20, seed: int = 0) -> dict[str, Any]:
    """Write rows, graphs, Markdown preview, and machine-readable preview evidence."""

    rows, graphs, failures = synthesis_selfcheck_rows()
    dataset_dir = out / "dataset"
    graph_dir = out / "graphs"
    preview_path = out / "PREVIEW.md"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    write_jsonl(dataset_dir / "failure_manifest.jsonl", failures)
    write_jsonl(graph_dir / "graphs.jsonl", graphs)
    preview = dataset_preview_markdown(
        rows,
        graphs=graphs,
        sample_per_family=sample_per_family,
        families=list(SYNTHESIS_SELFCHECK_FAMILIES),
        seed=seed,
    )
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(preview, encoding="utf-8")
    evidence = dataset_preview_evidence_report(
        rows,
        preview_path=preview_path,
        sample_per_family=sample_per_family,
        families=list(SYNTHESIS_SELFCHECK_FAMILIES),
        seed=seed,
    )
    write_json(preview_path.with_suffix(".preview_evidence.json"), evidence)
    write_json(dataset_dir / DEFAULT_PREVIEW_EVIDENCE_FILENAME, evidence)
    return {
        "out": str(out),
        "row_count": len(rows),
        "failure_count": len(failures),
        "families": sorted({row["query_program"]["query_id"].rsplit(":", 1)[-1] for row in rows}),
        "preview": str(preview_path),
        "preview_evidence": str(dataset_dir / DEFAULT_PREVIEW_EVIDENCE_FILENAME),
    }


def _add_reference_endpoint_nodes(graph: OntologyGraph) -> None:
    for endpoint_id, coordinate in [
        ("edge_endpoint:ref", [0.0, -4.0, 0.0]),
        ("edge_endpoint:far", [50.0, 4.0, 0.0]),
    ]:
        graph.add_node(Node(endpoint_id, "edge_endpoint", endpoint_id))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate", coordinate, "mm"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_x", coordinate[0], "mm"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_y", coordinate[1], "mm"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_z", coordinate[2], "mm"))


def _add_reference_region_nodes(graph: OntologyGraph) -> None:
    for region_id, region_type, volume, centroid in [
        ("material_region:ref", "material_region", 33.0, [0.0, -6.0, 1.0]),
        ("void_region:ref", "void_region", 11.0, [45.0, 3.0, 2.0]),
    ]:
        graph.add_node(Node(region_id, region_type, region_id))
        graph.add_measurement(Measurement(region_id, "entity_geometry", "volume", volume, "mm^3"))
        graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid", centroid, "mm"))
        graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_x", centroid[0], "mm"))
        graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_y", centroid[1], "mm"))
        graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_z", centroid[2], "mm"))


def _face_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-face-metric",
        source={
            "source_id": "selfcheck-face-metric",
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).faces(\"|Z\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:faces", "selector", "faces"))
    for face_id, area in [("face:a", 30.0), ("face:b", 20.0), ("face:c", 10.0)]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
    return graph


def _edge_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-edge-metric",
        source={
            "source_id": "selfcheck-edge-metric",
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges(\"|Y\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for edge_id, length in [("edge:a", 10.0), ("edge:b", 8.0), ("edge:c", 5.0)]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
    return graph


def _face_rank_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).faces(\"|Z\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:faces", "selector", "faces"))
    for face_id, area in [("face:a", 30.0), ("face:b", 20.0), ("face:c", 10.0), ("face:d", 5.0)]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
    return graph


def _face_deep_rank_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).faces()\n"
            ),
        },
    )
    graph.add_node(Node("selector:faces", "selector", "faces"))
    for index, area in enumerate([30.0, 25.0, 20.0, 15.0, 10.0, 5.0]):
        face_id = f"face:{index}"
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
    return graph


def _edge_rank_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges(\"|Y\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for edge_id, length in [("edge:a", 10.0), ("edge:b", 8.0), ("edge:c", 5.0), ("edge:d", 1.0)]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
    return graph


def _edge_deep_rank_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges()\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for index, length in enumerate([30.0, 25.0, 20.0, 15.0, 10.0, 5.0]):
        edge_id = f"edge:{index}"
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
    return graph


def _feature_rank_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "features = [base.translate((index * 4, 0, 0)) for index in range(6)]\n"
            ),
        },
    )
    for index, volume in enumerate([60.0, 50.0, 40.0, 30.0, 20.0, 10.0]):
        feature_id = f"feature:{index}"
        centroid = [float(index), float(index * 2), float(index * 3)]
        graph.add_node(Node(feature_id, "feature", feature_id))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "volume", volume, "mm^3"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid", centroid, "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_x", centroid[0], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_y", centroid[1], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_z", centroid[2], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "bbox_span_z", volume / 10.0, "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "topology_faces", float(index + 4), "count"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "topology_edges", float(index + 8), "count"))
    return graph


def _region_rank_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane(\"XY\").box(10, 10, 3)\n"
                "regions = [base.translate((index * 4, 0, 0)) for index in range(6)]\n"
            ),
        },
    )
    for target_type, relation in [
        ("material_region", "has_kernel_material_region_geometry"),
        ("void_region", "has_kernel_void_region_geometry"),
    ]:
        for index, volume in enumerate([60.0, 50.0, 40.0, 30.0, 20.0, 10.0]):
            node_id = f"{target_type}:{index}"
            centroid = [float(index), float(index * 2), float(index * 3)]
            graph.add_node(Node(node_id, target_type, node_id))
            graph.add_relation(Relation(node_id, node_id, relation))
            graph.add_measurement(Measurement(node_id, "entity_geometry", "volume", volume, "mm^3"))
            graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid", centroid, "mm"))
            graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_x", centroid[0], "mm"))
            graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_y", centroid[1], "mm"))
            graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_z", centroid[2], "mm"))
    return graph


def _edge_spatial_relation_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges()\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for edge_id, length, midpoint in [
        ("edge:a", 10.0, [0.0, 0.0, 0.0]),
        ("edge:b", 8.0, [2.0, 0.0, 0.0]),
        ("edge:c", 5.0, [0.0, 3.0, 0.0]),
        ("edge:d", 2.0, [4.0, 3.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
        graph.add_measurement(Measurement(edge_id, "relation_metric", "midpoint_distance_to_origin", length / 2.0, "mm"))
    for source_id, target_id, relation in [
        ("edge:a", "edge:b", "adjacent_to"),
        ("edge:b", "edge:a", "adjacent_to"),
        ("edge:a", "edge:c", "intersects"),
        ("edge:c", "edge:a", "intersects"),
        ("edge:c", "edge:d", "opposite_to"),
        ("edge:d", "edge:c", "opposite_to"),
        ("edge:b", "edge:d", "perpendicular_to"),
        ("edge:d", "edge:b", "perpendicular_to"),
    ]:
        graph.add_relation(Relation(source_id, target_id, relation))
    return graph


def _edge_same_length_relation_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-edge-same-length-relation",
        source={
            "source_id": "selfcheck-edge-same-length-relation",
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges(\"|Y\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for edge_id, length, midpoint in [
        ("edge:a", 10.0, [0.0, 0.0, 0.0]),
        ("edge:b", 10.0, [2.0, 0.0, 0.0]),
        ("edge:c", 5.0, [0.0, 3.0, 0.0]),
        ("edge:d", 5.0, [4.0, 3.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
        graph.add_measurement(Measurement(edge_id, "relation_metric", "midpoint_distance_to_origin", length / 2.0, "mm"))
    for source_id, target_id in [
        ("edge:a", "edge:b"),
        ("edge:b", "edge:a"),
        ("edge:c", "edge:d"),
        ("edge:d", "edge:c"),
    ]:
        graph.add_relation(Relation(source_id, target_id, "same_length_as"))
    return graph


def _edge_single_relation_graph(graph_id: str, relation: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(12, 8, 4).edges()\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for edge_id, length, midpoint in [
        ("edge:a", 12.0, [0.0, 0.0, 0.0]),
        ("edge:b", 6.0, [2.0, 0.0, 0.0]),
        ("edge:c", 10.0, [0.0, 3.0, 0.0]),
        ("edge:d", 4.0, [4.0, 3.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
        graph.add_measurement(Measurement(edge_id, "relation_metric", "midpoint_distance_to_origin", length / 2.0, "mm"))
    for source_id, target_id in _single_relation_pairs(relation):
        graph.add_relation(Relation(source_id, target_id, relation))
    return graph


def _single_relation_pairs(relation: str) -> list[tuple[str, str]]:
    if relation == "shorter_than":
        return [("edge:b", "edge:a"), ("edge:d", "edge:c")]
    return [("edge:a", "edge:b"), ("edge:c", "edge:d")]


def _face_spatial_relation_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).faces()\n"
            ),
        },
    )
    graph.add_node(Node("selector:faces", "selector", "faces"))
    for face_id, area, center in [
        ("face:a", 60.0, [0.0, 0.0, 0.0]),
        ("face:b", 48.0, [2.0, 0.0, 1.0]),
        ("face:c", 30.0, [0.0, 3.0, 2.0]),
        ("face:d", 12.0, [4.0, 3.0, 3.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "center", center, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_x", center[0], "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_y", center[1], "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", center[2], "mm"))
        graph.add_measurement(Measurement(face_id, "relation_metric", "distance_to_origin", area / 10.0, "mm"))
    for source_id, target_id, relation in [
        ("face:a", "face:b", "adjacent_to"),
        ("face:b", "face:a", "adjacent_to"),
        ("face:a", "face:c", "intersects"),
        ("face:c", "face:a", "intersects"),
        ("face:c", "face:d", "opposite_to"),
        ("face:d", "face:c", "opposite_to"),
        ("face:b", "face:d", "perpendicular_to"),
        ("face:d", "face:b", "perpendicular_to"),
    ]:
        graph.add_relation(Relation(source_id, target_id, relation))
    return graph


def _face_single_relation_graph(graph_id: str, relation: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).faces()\n"
            ),
        },
    )
    graph.add_node(Node("selector:faces", "selector", "faces"))
    for face_id, area, center in [
        ("face:a", 60.0, [0.0, 0.0, 0.0]),
        ("face:b", 48.0, [2.0, 0.0, 1.0]),
        ("face:c", 30.0, [0.0, 3.0, 2.0]),
        ("face:d", 12.0, [4.0, 3.0, 3.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "center", center, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_x", center[0], "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_y", center[1], "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", center[2], "mm"))
        graph.add_measurement(Measurement(face_id, "relation_metric", "distance_to_origin", area / 10.0, "mm"))
    for source_id, target_id in [("face:a", "face:b"), ("face:c", "face:d")]:
        graph.add_relation(Relation(source_id, target_id, relation))
    return graph


def _feature_equal_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-feature-equal-metric",
        source={
            "source_id": "selfcheck-feature-equal-metric",
            "source_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "upper = cq.Workplane(\"XY\").box(10, 6, 4).translate((0, 0, 8))\n"
                "small = cq.Workplane(\"XY\").box(4, 4, 2)\n"
                "result = base.union(upper).union(small)\n"
            ),
        },
    )
    for feature_id, volume, centroid, bbox_span_z in [
        ("feature:base", 240.0, [0.0, 0.0, 2.0], 4.0),
        ("feature:upper", 240.0 + 1e-7, [0.0, 0.0, 8.0], 5.0),
        ("feature:small", 32.0, [20.0, 0.0, 1.0], 2.0),
    ]:
        graph.add_node(Node(feature_id, "feature", feature_id))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "volume", volume, "mm^3"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid", centroid, "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_x", centroid[0], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_y", centroid[1], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_z", centroid[2], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "bbox_span_z", bbox_span_z, "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "topology_faces", 6.0 if feature_id != "feature:small" else 4.0))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "topology_edges", 12.0 if feature_id != "feature:small" else 8.0))
    for face_id, area, coordinate_z, face_center in [
        ("face:ref", 18.0, 3.0, [0.0, 0.0, 0.0]),
        ("face:far", 7.0, 9.0, [50.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", coordinate_z, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_center", face_center, "mm"))
    for edge_id, length, midpoint in [
        ("edge:ref", 15.0, [0.0, -4.0, 0.0]),
        ("edge:far", 5.0, [50.0, 4.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
    _add_reference_endpoint_nodes(graph)
    _add_reference_region_nodes(graph)
    return graph


def _feature_effect_delta_graph(graph_id: str) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id=graph_id,
        source={
            "source_id": graph_id.rsplit(":", 1)[-1],
            "source_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane(\"XY\").box(10, 10, 3)\n"
                "boss = base.faces(\">Z\").workplane().circle(2).extrude(4)\n"
                "slot = boss.faces(\">Z\").workplane().rect(2, 5).cutBlind(-2)\n"
                "result = slot\n"
            ),
        },
    )
    for feature_id, values in {
        "feature:add_a": {
            "signed_volume_delta": 60.0,
            "volume_delta_magnitude": 60.0,
            "bbox_delta_span_z": 5.0,
            "bbox_delta_max_span": 5.0,
            "bbox_delta_min_z": 1.0,
            "centroid_delta_z": 2.0,
            "centroid_delta_magnitude": 2.0,
            "topology_delta_faces": 3.0,
            "topology_delta_edges": 6.0,
        },
        "feature:add_b": {
            "signed_volume_delta": 24.0,
            "volume_delta_magnitude": 24.0,
            "bbox_delta_span_z": 2.0,
            "bbox_delta_max_span": 8.0,
            "bbox_delta_min_z": 3.0,
            "centroid_delta_z": 6.0,
            "centroid_delta_magnitude": 6.0,
            "topology_delta_faces": 6.0,
            "topology_delta_edges": 12.0,
        },
        "feature:cut_a": {
            "signed_volume_delta": -10.0,
            "volume_delta_magnitude": 10.0,
            "bbox_delta_span_z": 1.0,
            "bbox_delta_max_span": 1.0,
            "bbox_delta_min_z": 0.5,
            "centroid_delta_z": 0.5,
            "centroid_delta_magnitude": 1.0,
            "topology_delta_faces": 2.0,
            "topology_delta_edges": 4.0,
        },
        "feature:cut_b": {
            "signed_volume_delta": -30.0,
            "volume_delta_magnitude": 30.0,
            "bbox_delta_span_z": 3.0,
            "bbox_delta_max_span": 4.0,
            "bbox_delta_min_z": 2.0,
            "centroid_delta_z": 1.0,
            "centroid_delta_magnitude": 3.0,
            "topology_delta_faces": 4.0,
            "topology_delta_edges": 8.0,
        },
    }.items():
        graph.add_node(Node(feature_id, "feature", feature_id))
        for metric, value in values.items():
            graph.add_measurement(Measurement(feature_id, "snapshot_delta", metric, value))
    return graph


def _region_equal_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-region-equal-metric",
        source={
            "source_id": "selfcheck-region-equal-metric",
            "source_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane(\"XY\").box(10, 10, 3)\n"
                "boss_a = cq.Workplane(\"XY\").circle(1).extrude(4)\n"
                "boss_b = cq.Workplane(\"XY\").circle(1).extrude(4).translate((4, 0, 0))\n"
                "cut_a = base.faces(\">Z\").workplane().circle(1).cutBlind(-2)\n"
                "cut_b = base.faces(\">Z\").workplane().center(4, 0).circle(1).cutBlind(-2)\n"
            ),
        },
    )
    for feature_id, volume, centroid in [
        ("feature:ref", 100.0, [0.0, 0.0, 0.0]),
        ("feature:far", 50.0, [100.0, 0.0, 1.0]),
    ]:
        graph.add_node(Node(feature_id, "feature", feature_id))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "volume", volume, "mm^3"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid", centroid, "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_x", centroid[0], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_y", centroid[1], "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_z", centroid[2], "mm"))
    for face_id, area, coordinate_z, face_center in [
        ("face:ref", 18.0, 3.0, [0.0, 0.0, 0.0]),
        ("face:far", 7.0, 9.0, [50.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", coordinate_z, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_center", face_center, "mm"))
    for edge_id, length, midpoint in [
        ("edge:ref", 15.0, [0.0, -4.0, 0.0]),
        ("edge:far", 5.0, [50.0, 4.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
    _add_reference_endpoint_nodes(graph)
    _add_reference_region_nodes(graph)
    for node_id, relation, volume, centroid in [
        ("material_region:a", "has_kernel_material_region_geometry", 12.0, [1.0, 0.0, 1.0]),
        ("material_region:b", "has_kernel_material_region_geometry", 12.0 + 1e-7, [6.0, 0.0, 7.0]),
        ("material_region:c", "has_kernel_material_region_geometry", 5.0, [20.0, 0.0, 20.0]),
        ("material_region:d", "has_kernel_material_region_geometry", 20.0, [30.0, 4.0, 12.0]),
        ("void_region:a", "has_kernel_void_region_geometry", 8.0, [2.0, 0.0, 2.0]),
        ("void_region:b", "has_kernel_void_region_geometry", 8.0 + 1e-7, [7.0, 0.0, 6.0]),
        ("void_region:c", "has_kernel_void_region_geometry", 3.0, [30.0, 0.0, 30.0]),
        ("void_region:d", "has_kernel_void_region_geometry", 14.0, [35.0, 5.0, 12.0]),
    ]:
        node_type = node_id.split(":", 1)[0]
        graph.add_node(Node(node_id, node_type, node_id))
        graph.add_relation(Relation(node_id, node_id, relation))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "volume", volume, "mm^3"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid", centroid, "mm"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_x", centroid[0], "mm"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_y", centroid[1], "mm"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_z", centroid[2], "mm"))
    return graph


def _face_equal_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-face-equal-metric",
        source={
            "source_id": "selfcheck-face-equal-metric",
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).faces(\"|Z\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:faces", "selector", "faces"))
    for feature_id, volume, centroid in [
        ("feature:ref", 100.0, [0.0, 0.0, 0.0]),
        ("feature:far", 50.0, [20.0, 0.0, 1.0]),
    ]:
        graph.add_node(Node(feature_id, "feature", feature_id))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid", centroid))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_z", centroid[2]))
    for face_id, area, coordinate_z, face_center in [
        ("face:a", 12.0, 0.0, [1.0, 0.0, 0.0]),
        ("face:b", 12.0 + 1e-7, 5.0, [5.0, 0.0, 0.0]),
        ("face:c", 8.0, 9.0, [12.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", coordinate_z, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_center", face_center, "mm"))
    for edge_id, length, midpoint in [
        ("edge:ref", 15.0, [0.0, -4.0, 0.0]),
        ("edge:far", 5.0, [50.0, 4.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
    _add_reference_endpoint_nodes(graph)
    _add_reference_region_nodes(graph)
    return graph


def _edge_equal_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-edge-equal-metric",
        source={
            "source_id": "selfcheck-edge-equal-metric",
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges(\"|Y\")\n"
            ),
        },
    )
    graph.add_node(Node("selector:edges", "selector", "edges"))
    for feature_id, volume, centroid in [
        ("feature:ref", 100.0, [0.0, 0.0, 0.0]),
        ("feature:far", 50.0, [100.0, 0.0, 1.0]),
    ]:
        graph.add_node(Node(feature_id, "feature", feature_id))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid", centroid))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_z", centroid[2]))
    for face_id, area, coordinate_z, face_center in [
        ("face:ref", 18.0, 3.0, [0.0, 0.0, 0.0]),
        ("face:far", 7.0, 9.0, [50.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", coordinate_z, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_center", face_center, "mm"))
    for edge_id, length, midpoint_y in [
        ("edge:a", 10.0, -3.0),
        ("edge:b", 10.0 + 1e-7, 7.0),
        ("edge:c", 4.0, 2.0),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint_y, "mm"))
        midpoint_x = 1.0 if edge_id == "edge:a" else 5.0 if edge_id == "edge:b" else 10.0
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint_x, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", 0.0, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", [midpoint_x, midpoint_y, 0.0], "mm"))
    _add_reference_endpoint_nodes(graph)
    _add_reference_region_nodes(graph)
    return graph


def _endpoint_equal_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-endpoint-equal-metric",
        source={
            "source_id": "selfcheck-endpoint-equal-metric",
            "source_code": (
                "import cadquery as cq\n"
                "result = cq.Workplane(\"XY\").box(10, 6, 4).edges(\"|Y\")\n"
            ),
        },
    )
    for feature_id, volume, centroid in [
        ("feature:ref", 100.0, [0.0, 0.0, 0.0]),
        ("feature:far", 50.0, [100.0, 0.0, 1.0]),
    ]:
        graph.add_node(Node(feature_id, "feature", feature_id))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "volume", volume, "mm^3"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid", centroid, "mm"))
        graph.add_measurement(Measurement(feature_id, "snapshot_state", "centroid_z", centroid[2], "mm"))
    for face_id, area, coordinate_z, face_center in [
        ("face:ref", 18.0, 3.0, [0.0, 0.0, 0.0]),
        ("face:far", 7.0, 9.0, [50.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", coordinate_z, "mm"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_center", face_center, "mm"))
    for edge_id, length, midpoint in [
        ("edge:a", 15.0, [0.0, -4.0, 0.0]),
        ("edge:b", 5.0, [50.0, 4.0, 0.0]),
        ("edge:c", 9.0, [10.0, 2.0, 0.0]),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm"))
    for endpoint_id, edge_id, coordinate, distance in [
        ("edge_endpoint:a", "edge:a", [0.0, 0.0, 3.0], 2.0),
        ("edge_endpoint:b", "edge:b", [4.0, 1.0, 3.0], 6.0),
        ("edge_endpoint:c", "edge:c", [8.0, 2.0, 9.0], 20.0),
    ]:
        graph.add_node(Node(endpoint_id, "edge_endpoint", endpoint_id))
        graph.add_relation(Relation(endpoint_id, edge_id, "endpoint_of"))
        graph.add_relation(Relation(endpoint_id, edge_id, "contained_in"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate", coordinate, "mm"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_x", coordinate[0], "mm"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_y", coordinate[1], "mm"))
        graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_z", coordinate[2], "mm"))
        graph.add_measurement(Measurement(endpoint_id, "relation_metric", "distance_to_origin", distance, "mm"))
    return graph


def _path_metric_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-path-metric",
        source={
            "source_id": "selfcheck-path-metric",
            "source_code": (
                "import cadquery as cq\n"
                "path = cq.Workplane(\"XY\").spline([(0, 0), (2, 1), (5, 1), (6, 4)])\n"
            ),
        },
    )
    graph.add_node(Node("path:main", "path", "path"))
    for point_id, coordinate in [
        ("path:main:point:0", [0.0, 0.0, 0.0]),
        ("path:main:point:1", [2.0, 1.0, 0.0]),
        ("path:main:point:2", [5.0, 1.0, 0.0]),
        ("path:main:point:3", [6.0, 4.0, 0.0]),
    ]:
        graph.add_node(Node(point_id, "path_point", point_id))
        graph.add_relation(Relation(point_id, "path:main", "point_on_path"))
        distance = sum(component * component for component in coordinate) ** 0.5
        graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate_x", coordinate[0], "mm"))
        graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate_y", coordinate[1], "mm"))
        graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate_z", coordinate[2], "mm"))
        graph.add_measurement(Measurement(point_id, "relation_metric", "distance_to_origin", distance, "mm"))
    for segment_id, length in [
        ("path:main:segment:0", 2.2360679),
        ("path:main:segment:1", 3.0),
        ("path:main:segment:2", 3.1622777),
    ]:
        graph.add_node(Node(segment_id, "path_segment", segment_id))
        graph.add_relation(Relation(segment_id, "path:main", "segment_on_path"))
        graph.add_measurement(Measurement(segment_id, "relation_metric", "segment_length", length, "mm"))
    return graph


def _face_selector_count_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-face-selector-count",
        source={
            "source_id": "selfcheck-face-selector-count",
            "source_code": (
                "import cadquery as cq\n"
                "box = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "sel_a = box.faces(\"<X\")\n"
                "sel_b = box.faces(\"|X\")\n"
                "sel_c = box.faces(\">X\")\n"
            ),
        },
    )
    for selector_id, selected_count, coordinate_x in [
        ("selector:a", 3, -5.0),
        ("selector:b", 4, -1.0),
        ("selector:c", 4, 8.0),
    ]:
        face_id = f"face:{selector_id.rsplit(':', 1)[-1]}"
        graph.add_node(Node(selector_id, "selector", selector_id))
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(selector_id, face_id, "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(selector_id, "snapshot_state", "selected_count", selected_count))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_x", coordinate_x, "mm"))
    return graph


def _edge_selector_count_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-edge-selector-count",
        source={
            "source_id": "selfcheck-edge-selector-count",
            "source_code": (
                "import cadquery as cq\n"
                "box = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "sel_a = box.edges(\"<Y\")\n"
                "sel_b = box.edges(\"|Y\")\n"
                "sel_c = box.edges(\">Y\")\n"
            ),
        },
    )
    for selector_id, selected_count, midpoint_y in [
        ("selector:a", 3, -5.0),
        ("selector:b", 4, -1.0),
        ("selector:c", 4, 8.0),
    ]:
        edge_id = f"edge:{selector_id.rsplit(':', 1)[-1]}"
        graph.add_node(Node(selector_id, "selector", selector_id))
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(selector_id, edge_id, "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(selector_id, "snapshot_state", "selected_count", selected_count))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint_y, "mm"))
    return graph


def _face_selector_relation_count_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-face-selector-relation-count",
        source={
            "source_id": "selfcheck-face-selector-relation-count",
            "source_code": (
                "import cadquery as cq\n"
                "box = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "sel_a = box.faces(\"<X\")\n"
                "sel_b = box.faces(\"<X\")\n"
                "sel_c = box.faces(\"|X\")\n"
                "sel_d = box.faces(\">X\")\n"
            ),
        },
    )
    for selector_id, selected_count in [
        ("selector:a", 2),
        ("selector:b", 5),
        ("selector:c", 3),
        ("selector:d", 4),
    ]:
        face_id = f"face:{selector_id.rsplit(':', 1)[-1]}"
        graph.add_node(Node(selector_id, "selector", selector_id))
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(selector_id, face_id, "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(selector_id, "snapshot_state", "selected_count", selected_count))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_x", 1.0, "mm"))
    graph.add_relation(Relation("selector:a", "selector:b", "same_selected_face_as"))
    graph.add_relation(Relation("selector:b", "selector:a", "same_selected_face_as"))
    return graph


def _edge_selector_relation_count_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selfcheck-edge-selector-relation-count",
        source={
            "source_id": "selfcheck-edge-selector-relation-count",
            "source_code": (
                "import cadquery as cq\n"
                "box = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "sel_a = box.edges(\"<Y\")\n"
                "sel_b = box.edges(\"<Y\")\n"
                "sel_c = box.edges(\"|Y\")\n"
                "sel_d = box.edges(\">Y\")\n"
            ),
        },
    )
    for selector_id, selected_count in [
        ("selector:a", 2),
        ("selector:b", 5),
        ("selector:c", 3),
        ("selector:d", 4),
    ]:
        edge_id = f"edge:{selector_id.rsplit(':', 1)[-1]}"
        graph.add_node(Node(selector_id, "selector", selector_id))
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(selector_id, edge_id, "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(selector_id, "snapshot_state", "selected_count", selected_count))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", 8.0, "mm"))
    graph.add_relation(Relation("selector:a", "selector:b", "same_selected_entity_as"))
    graph.add_relation(Relation("selector:b", "selector:a", "same_selected_entity_as"))
    return graph


def _edge_selector_equal_metric_count_graph() -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:selector-count-equal-2",
        source={
            "source_id": "selfcheck-edge-selector-equal-metric-count",
            "source_code": (
                "import cadquery as cq\n"
                "box = cq.Workplane(\"XY\").box(10, 6, 4)\n"
                "sel_a = box.edges(\"<Y\")\n"
                "sel_b = box.edges(\"|Y\")\n"
                "sel_c = box.edges(\">Y\")\n"
            ),
        },
    )
    for selector_id, selected_count, midpoint_y in [
        ("selector:a", 3, 2.0),
        ("selector:b", 5, 2.0),
        ("selector:c", 3, 8.0),
        ("selector:d", 5, 8.0),
    ]:
        edge_id = f"edge:{selector_id.rsplit(':', 1)[-1]}"
        graph.add_node(Node(selector_id, "selector", selector_id))
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(selector_id, edge_id, "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(selector_id, "snapshot_state", "selected_count", selected_count))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint_y, "mm"))
    return graph
