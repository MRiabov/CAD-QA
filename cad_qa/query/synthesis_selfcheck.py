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
    "parameterized_kernel_face_extreme",
    "parameterized_kernel_edge_extreme",
    "parameterized_kernel_face_rank",
    "parameterized_kernel_edge_rank",
    "parameterized_equal_face_metric_extreme",
    "parameterized_equal_edge_metric_extreme",
    "parameterized_kernel_face_selector_count",
    "parameterized_kernel_edge_selector_count",
)


def synthesis_selfcheck_graphs() -> list[OntologyGraph]:
    """Return deterministic synthetic graphs that exercise synthesized families."""

    return [
        _face_metric_graph(),
        _edge_metric_graph(),
        _face_equal_metric_graph(),
        _edge_equal_metric_graph(),
        _face_selector_count_graph(),
        _edge_selector_count_graph(),
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
    for face_id, area, coordinate_z in [
        ("face:a", 12.0, 0.0),
        ("face:b", 12.0 + 1e-7, 5.0),
        ("face:c", 8.0, 9.0),
    ]:
        graph.add_node(Node(face_id, "face", face_id))
        graph.add_relation(Relation(face_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", area, "mm^2"))
        graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", coordinate_z, "mm"))
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
    for edge_id, length, midpoint_y in [
        ("edge:a", 10.0, -3.0),
        ("edge:b", 10.0 + 1e-7, 7.0),
        ("edge:c", 4.0, 2.0),
    ]:
        graph.add_node(Node(edge_id, "edge", edge_id))
        graph.add_relation(Relation(edge_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "edge_length", length, "mm"))
        graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint_y, "mm"))
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
