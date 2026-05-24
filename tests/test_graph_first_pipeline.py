from __future__ import annotations

import ast
import json
import math
from pathlib import Path

from cad_qa.dataset.materialize import materialize_row
from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.public import private_rows, public_private_audit, public_rows, write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release import export_release_dataset
from cad_qa.dataset.release_report import release_balance_report, release_verifier_markdown, release_verifier_report
from cad_qa.dataset.report import (
    dataset_card_markdown,
    dataset_report,
    failure_report,
    shortcut_resistance_markdown,
    shortcut_resistance_report,
)
from cad_qa.dataset.sft import ablation_sft_groups, answer_sft_rows, default_training_rows, reasoning_sft_rows, scaling_sft_groups
from cad_qa.dataset.split import assign_splits, split_audit, split_manifest
from cad_qa.dataset.validate import validate_rows
from cad_qa.evaluation.baselines import run_baselines
from cad_qa.evaluation.closed_book import closed_book_request_audit, run_closed_book_evaluation
from cad_qa.evaluation.grade import grade_public_private, grade_responses
from cad_qa.evaluation.requests import few_shot_requests, oracle_responses, zero_shot_requests
from cad_qa.evaluation.tool_assisted import run_tool_assisted_upper_bound, tool_assisted_responses
from cad_qa.experiment import (
    experiment_summary,
    experiment_summary_markdown,
    package_run_artifacts,
    write_paper_results,
    run_artifact_manifest,
    run_smoke_experiment,
)
from cad_qa.io import read_jsonl, to_jsonable, write_jsonl
from cad_qa.ontology import build_graph
from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph, Relation, graph_from_dict
from cad_qa.ontology.profile_geometry import circle_profile, polyline_profile, rect_profile
from cad_qa.ontology.relations import RELATION_FAMILIES
from cad_qa.ontology.workplane_frames import project_local_point
from cad_qa.prompts.render import render_prompt
from cad_qa.prompts.templates import prompt_template_registry
from cad_qa.query.ir import Clause, QueryProgram
from cad_qa.query.resolver import resolve_query, smoke_queries
from cad_qa.source import load_sources_jsonl, source_audit, source_family_from_path, source_manifest, source_record_from_mapping
from cad_qa.trace import TraceRecord, cadquery_available, trace_report, trace_source, trace_sources_bounded
from cad_qa.cli import main as cli_main


SOURCE = """
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, 0))
wp2 = wp1.circle(2)
wp3 = wp2.extrude(5)
wp4 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, 10), xDir=cq.Vector(1, 0, 0), normal=cq.Vector(0, 0, 1)))
wp5 = wp4.rect(4, 3)
wp6 = wp5.extrude(2)
pts = [(0, 0), (2, 0), (0, 2)]
wp7 = wp1.polyline(pts).close()
result = wp3.union(wp6)
"""

LOOP_SOURCE = """
import cadquery as cq
A = 10
B = 20
base = cq.Workplane("XY").box(A, B, 5)
front_shape = [(0, 0), (2, 0), (0, 2)]
for face_tag in (">Y", "<Y"):
    base = base.faces(face_tag).workplane().polyline(front_shape).close().cutThruAll()
for z in (1, -1):
    base = base.faces(">Y").workplane().center(0, z).rect(4, 1).cutBlind(-2)
result = base
"""


def test_source_loading(tmp_path: Path) -> None:
    path = tmp_path / "sources.jsonl"
    write_jsonl(path, [{"source_id": "src_fixture", "normalized_code": SOURCE}])
    sources = load_sources_jsonl(path)
    assert sources[0].source_id == "src_fixture"
    assert sources[0].source_code.endswith("\n")


def test_graph_exact_duplicate_measurements_are_idempotent() -> None:
    graph = OntologyGraph(graph_id="graph:src", source={"source_id": "src", "source_code": ""})
    measurement = Measurement(
        "face:kernel:a",
        "entity_geometry",
        "face_area",
        12.0,
        "mm^2",
        {"source": "cadquery_selector_result"},
    )
    graph.add_measurement(measurement)
    graph.add_measurement(measurement)
    graph.add_measurement(
        Measurement(
            "face:kernel:a",
            "entity_geometry",
            "face_area",
            12.0,
            "mm^2",
            {"source": "manual_fixture"},
        )
    )
    assert len(graph.measurements_for("face:kernel:a", "face_area")) == 2


def test_graph_exact_duplicate_relations_are_idempotent() -> None:
    graph = OntologyGraph(graph_id="graph:src", source={"source_id": "src", "source_code": ""})
    relation = Relation(
        "face:kernel:a",
        "origin:global",
        "distance_to",
        evidence={"source": "cadquery_selector_result"},
    )
    graph.add_relation(relation)
    graph.add_relation(relation)
    graph.add_relation(
        Relation(
            "face:kernel:a",
            "origin:global",
            "distance_to",
            evidence={"source": "manual_fixture"},
        )
    )
    assert len(graph.relations) == 2


def test_cadevolve_source_manifest_and_audit_cli(tmp_path: Path) -> None:
    sources_path = tmp_path / "sources.jsonl"
    manifest_path = tmp_path / "source_manifest.json"
    audit_path = tmp_path / "source_audit.json"
    write_jsonl(
        sources_path,
        [
            {
                "source_id": "src_a",
                "normalized_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(1, 1, 1)\n",
                "normalized_archive_member_path": "cadquery/train/bracket__001.py",
                "generator_id": "gen_box",
            },
            {
                "source_id": "src_b",
                "normalized_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(2, 1, 1)\n",
                "normalized_archive_member_path": "cadquery/train/bracket__002.py",
                "generator_id": "gen_box",
            },
            {
                "source_id": "src_dup",
                "normalized_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(3, 1, 1)\n",
                "source_family": "manual_family",
            },
            {
                "source_id": "src_dup",
                "normalized_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(4, 1, 1)\n",
                "source_family": "manual_family",
            },
        ],
    )
    sources = load_sources_jsonl(sources_path)
    assert sources[0].metadata["path_family"] == "cadquery/train/bracket"
    assert source_family_from_path("cadquery/train/bracket+r12.py") == "cadquery/train/bracket"

    manifest = source_manifest(sources)
    audit = source_audit(sources)
    assert manifest["source_count"] == 4
    assert manifest["groups"]["path_family"]["groups"]["cadquery/train/bracket"] == ["src_a", "src_b"]
    assert manifest["groups"]["generator_id"]["groups"]["gen_box"] == ["src_a", "src_b"]
    assert manifest["duplicate_source_ids"] == {"src_dup": 2}
    assert not audit["valid"]
    assert audit["errors"][0]["error"] == "duplicate_source_id"

    assert cli_main(["sources", "manifest", "--sources-jsonl", str(sources_path), "--out", str(manifest_path)]) == 0
    assert cli_main(["sources", "audit", "--sources-jsonl", str(sources_path), "--out", str(audit_path)]) == 0
    assert manifest_path.exists()
    assert audit_path.exists()


def test_trace_worker_executes_cadquery_source_or_reports_unavailable(tmp_path: Path) -> None:
    source = source_record_from_mapping({"source_id": "src_trace", "normalized_code": SOURCE})
    trace = trace_source(source, timeout_seconds=5.0)

    sources_path = tmp_path / "sources.jsonl"
    out_dir = tmp_path / "trace"
    write_jsonl(sources_path, [{"source_id": "src_trace", "normalized_code": SOURCE}])
    assert cli_main(
        [
            "trace",
            "run",
            "--sources-jsonl",
            str(sources_path),
            "--out",
            str(out_dir),
            "--timeout-seconds",
            "5",
        ]
    ) == 0
    assert (out_dir / "traces.jsonl").exists()
    assert (out_dir / "trace_report.json").exists()

    if not cadquery_available():
        assert trace.execution_status == "failed"
        assert trace.failure_reason == "cadquery_unavailable"
        return

    assert trace.execution_status == "ok"
    assert trace.failure_reason is None
    assert trace.snapshots
    assert trace.snapshots[-1]["step"] == "final"
    assert trace.snapshots[-1]["volume"] > 0
    assert trace.snapshots[-1]["bbox"]["min"][2] <= 0
    assert len(trace.snapshots[-1]["centroid"]) == 3
    assert trace.snapshots[-1]["topology"]["faces"] is not None
    assert trace.operation_effects
    assert any(
        effect["evidence"] == "cadquery_assignment_snapshot_delta"
        for effect in trace.operation_effects
    )


def test_trace_sources_bounded_preserves_order_and_reports_timeouts() -> None:
    if not cadquery_available():
        return
    ok = source_record_from_mapping(
        {
            "source_id": "src_trace_ok",
            "normalized_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(1, 1, 1)\n",
        }
    )
    infinite = source_record_from_mapping(
        {
            "source_id": "src_trace_timeout",
            "normalized_code": "import cadquery as cq\nwhile True:\n    pass\n",
        }
    )
    traces = trace_sources_bounded([ok, infinite], timeout_seconds=5.0, worker_count=2)
    assert [trace.source_id for trace in traces] == ["src_trace_ok", "src_trace_timeout"]
    assert traces[0].execution_status == "ok"
    assert traces[1].execution_status == "failed"
    assert traces[1].failure_reason == "timeout"
    report = trace_report(traces)
    assert report["trace_count"] == 2
    assert report["failure_reasons"]["timeout"] == 1


def test_trace_skips_non_shape_workplane_cursor_values() -> None:
    if not cadquery_available():
        return
    source = source_record_from_mapping(
        {
            "source_id": "src_trace_cursor",
            "normalized_code": (
                "import cadquery as cq\n"
                "wp1 = cq.Workplane('XY')\n"
                "wp2 = wp1.moveTo(1, 1)\n"
                "result = cq.Workplane('XY').box(1, 1, 1)\n"
            ),
        }
    )
    trace = trace_source(source, timeout_seconds=5.0)
    assert trace.execution_status == "ok"
    assert trace.failure_reason is None
    assert trace.snapshots[-1]["target"] == "result"
    assert all(snapshot["target"] != "wp2" for snapshot in trace.snapshots)


def test_trace_measures_selector_subexpression_not_final_chained_solid() -> None:
    if not cadquery_available():
        return
    source = source_record_from_mapping(
        {
            "source_id": "src_trace_selector_subexpr",
            "normalized_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane('XY').box(4, 4, 2)\n"
                "result = base.faces('>Z').workplane().rect(1, 1).cutBlind(-1)\n"
            ),
        }
    )
    trace = trace_source(source, timeout_seconds=5.0)
    assert trace.execution_status == "ok"
    assert trace.selector_results
    selector = trace.selector_results[0]
    assert selector["selector_kind"] == "faces"
    assert selector["selector"] == ">Z"
    assert selector["shape_types"] == ["Face"]


def test_trace_unrolls_simple_loop_body_snapshots() -> None:
    if not cadquery_available():
        return
    source = source_record_from_mapping(
        {
            "source_id": "src_trace_loop_body",
            "normalized_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane('XY').box(10, 10, 10)\n"
                "for z in (1, 2):\n"
                "    base = base.faces('>Z').workplane().center(z, 0).circle(1).cutBlind(-1)\n"
                "result = base\n"
            ),
        }
    )
    trace = trace_source(source, timeout_seconds=5.0)
    assert trace.execution_status == "ok"
    body_snapshots = [
        snapshot
        for snapshot in trace.snapshots or []
        if snapshot.get("target") == "base" and snapshot.get("source_line") == 4
    ]
    assert len(body_snapshots) == 2
    body_effects = [
        effect
        for effect in trace.operation_effects or []
        if effect.get("to_target") == "base" and effect.get("source_line") == 4
    ]
    assert len(body_effects) == 2
    assert all(effect["signed_volume_delta"] < 0 for effect in body_effects)


def test_graph_build_integrates_trace_feature_effects(tmp_path: Path) -> None:
    source = source_record_from_mapping({"source_id": "src_trace_graph", "normalized_code": SOURCE})
    trace_record = {
        "source_id": "src_trace_graph",
        "execution_status": "ok",
        "snapshots": [
            {"target": "wp2", "source_line": 4, "operation_index": 0, "volume": 1.0, "bbox": {"min": [0, 0, 0], "max": [1, 1, 0]}, "topology": {"faces": 0}},
            {"target": "wp3", "source_line": 5, "operation_index": 1, "volume": 62.8, "bbox": {"min": [-2, -2, 0], "max": [2, 2, 5]}, "topology": {"faces": 3}},
        ],
        "operation_effects": [
            {
                "from_target": "wp2",
                "to_target": "wp3",
                "source_line": 5,
                "signed_volume_delta": 61.8,
                "bbox_delta": {"min": [-2, -2, 0], "max": [1, 1, 5]},
                "topology_delta": {"faces": 3},
                "evidence": "cadquery_assignment_snapshot_delta",
            }
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }

    graph = build_graph(source, trace=trace_record)
    exact_regions = [
        node
        for node in graph.nodes_by_type("material_region")
        if node.properties.get("conservative") is False
    ]
    assert exact_regions
    region = exact_regions[0]
    assert any(relation.type == "has_kernel_material_region_geometry" for relation in graph.relations)
    assert graph.measurements_for(region.id, "volume")[0].value == 61.8
    assert graph.measurements_for("feature:wp3", "signed_volume_delta")

    query = next(query for query in smoke_queries(graph) if query.query_id.endswith("largest_added_region"))
    resolution = resolve_query(graph, query)
    row = materialize_row(graph, resolution)
    assert resolution.verifier_status == "resolved"
    assert "has_kernel_material_region_geometry" in resolution.relation_families
    assert row.release_ready
    assert "conservative_region_projection" not in row.quarantine_reasons

    sources_path = tmp_path / "sources.jsonl"
    traces_path = tmp_path / "traces.jsonl"
    graph_dir = tmp_path / "graph"
    write_jsonl(sources_path, [{"source_id": "src_trace_graph", "normalized_code": SOURCE}])
    write_jsonl(traces_path, [trace_record])
    assert cli_main(
        [
            "graph",
            "build",
            "--sources-jsonl",
            str(sources_path),
            "--traces-jsonl",
            str(traces_path),
            "--out",
            str(graph_dir),
        ]
    ) == 0
    persisted = graph_from_dict(read_jsonl(graph_dir / "graphs.jsonl")[0])
    assert any(relation.type == "has_kernel_material_region_geometry" for relation in persisted.relations)


def test_additive_trace_snapshot_does_not_become_false_void_region() -> None:
    source = source_record_from_mapping(
        {
            "source_id": "src_negative_adjacent_delta",
            "normalized_code": (
                "import cadquery as cq\n"
                "wp1 = cq.Workplane('XY').circle(5)\n"
                "wp2 = wp1.extrude(10)\n"
                "wp3 = cq.Workplane('XY').circle(1)\n"
                "wp4 = wp3.extrude(1)\n"
                "result = wp2\n"
            ),
        }
    )
    trace_record = {
        "source_id": "src_negative_adjacent_delta",
        "execution_status": "ok",
        "snapshots": [
            {
                "target": "wp2",
                "source_line": 3,
                "operation_index": 0,
                "volume": 785.398,
                "bbox": {"min": [-5, -5, 0], "max": [5, 5, 10]},
                "topology": {"faces": 3},
            },
            {
                "target": "wp4",
                "source_line": 5,
                "operation_index": 1,
                "volume": 3.14159,
                "bbox": {"min": [-1, -1, 0], "max": [1, 1, 1]},
                "topology": {"faces": 3},
            },
        ],
        "operation_effects": [
            {
                "from_target": "wp2",
                "to_target": "wp4",
                "source_line": 5,
                "signed_volume_delta": -782.25641,
                "bbox_delta": {"min": [4, 4, 0], "max": [-4, -4, -9]},
                "topology_delta": {"faces": 0},
                "evidence": "cadquery_assignment_snapshot_delta",
            }
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }

    graph = build_graph(source, trace=trace_record)
    material_region = graph.node("material_region:wp4")
    assert material_region is not None
    assert material_region.properties["conservative"] is False
    assert material_region.properties["trace_evidence"] == "cadquery_trace_snapshot"
    assert graph.measurements_for("material_region:wp4", "volume")[0].value == 3.14159
    assert graph.measurements_for("material_region:wp4", "bbox")
    assert graph.node("void_region:wp4") is None
    assert not any(
        relation.type == "has_kernel_void_region_geometry" and relation.source_id == "void_region:wp4"
        for relation in graph.relations
    )

    query = next(query for query in smoke_queries(graph) if query.query_id.endswith("largest_added_region"))
    resolution = resolve_query(graph, query)
    assert resolution.verifier_status == "resolved"
    assert resolution.gold_answer == "material_region:wp2"


def test_cut_trace_effect_creates_kernel_void_region() -> None:
    source = source_record_from_mapping(
        {
            "source_id": "src_kernel_void",
            "normalized_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane('XY').box(10, 10, 10)\n"
                "wp1 = base.faces('>Z').workplane().circle(2).cutBlind(-5)\n"
                "result = wp1\n"
            ),
        }
    )
    trace_record = {
        "source_id": "src_kernel_void",
        "execution_status": "ok",
        "snapshots": [
            {
                "target": "base",
                "source_line": 2,
                "operation_index": 0,
                "volume": 1000.0,
                "bbox": {"min": [-5, -5, -5], "max": [5, 5, 5]},
                "topology": {"faces": 6, "edges": 12, "vertices": 8},
            },
            {
                "target": "wp1",
                "source_line": 3,
                "operation_index": 1,
                "volume": 937.168,
                "bbox": {"min": [-5, -5, -5], "max": [5, 5, 5]},
                "topology": {"faces": 8, "edges": 18, "vertices": 12},
            },
        ],
        "operation_effects": [
            {
                "from_target": "base",
                "to_target": "wp1",
                "source_line": 3,
                "signed_volume_delta": -62.832,
                "bbox_delta": {"min": [0, 0, 0], "max": [0, 0, 0]},
                "topology_delta": {"faces": 2, "edges": 6, "vertices": 4},
                "evidence": "cadquery_assignment_snapshot_delta",
            }
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }

    graph = build_graph(source, trace=trace_record)
    void_region = graph.node("void_region:wp1")
    assert void_region is not None
    assert void_region.properties["conservative"] is False
    assert void_region.properties["trace_evidence"] == "cadquery_assignment_snapshot_delta"
    assert graph.measurements_for("void_region:wp1", "volume")[0].value == 62.832
    assert graph.measurements_for("void_region:wp1", "signed_volume_delta")[0].value == -62.832
    assert graph.measurements_for("void_region:wp1", "topology_delta_faces")[0].value == 2.0
    assert any(
        relation.type == "has_kernel_void_region_geometry" and relation.source_id == "void_region:wp1"
        for relation in graph.relations
    )
    assert graph.node("material_region:wp1") is None

    query = next(query for query in smoke_queries(graph) if query.query_id.endswith("largest_removed_region"))
    resolution = resolve_query(graph, query)
    row = materialize_row(graph, resolution)
    assert resolution.verifier_status == "resolved"
    assert resolution.gold_answer == "void_region:wp1"
    assert row.release_ready
    assert "conservative_region_projection" not in row.quarantine_reasons


def test_repeated_target_trace_effect_requires_source_line_match() -> None:
    source = source_record_from_mapping(
        {
            "source_id": "src_repeated_target_trace",
            "normalized_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane('XY').box(10, 10, 10)\n"
                "for z in (1, 2):\n"
                "    base = base.faces('>Z').workplane().circle(z).cutBlind(-1)\n"
                "result = base\n"
            ),
        }
    )
    trace_record = {
        "source_id": "src_repeated_target_trace",
        "execution_status": "ok",
        "snapshots": [
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 1000.0},
            {"target": "base", "source_line": 3, "operation_index": 1, "volume": 990.0},
            {"target": "base", "source_line": 3, "operation_index": 2, "volume": 970.0},
        ],
        "operation_effects": [
            {
                "from_target": "base",
                "to_target": "base",
                "source_line": 3,
                "signed_volume_delta": -10.0,
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "base",
                "to_target": "base",
                "source_line": 3,
                "signed_volume_delta": -20.0,
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }

    graph = build_graph(source, trace=trace_record)
    void_regions = graph.nodes_by_type("void_region")
    assert void_regions
    assert all(node.properties["conservative"] is True for node in void_regions)
    assert not any(relation.type == "has_kernel_void_region_geometry" for relation in graph.relations)
    assert any(relation.type == "has_void_region_geometry" for relation in graph.relations)


def test_repeated_target_trace_effects_match_loop_iterations_by_line_order() -> None:
    source = source_record_from_mapping(
        {
            "source_id": "src_repeated_target_line_order",
            "normalized_code": (
                "import cadquery as cq\n"
                "base = cq.Workplane('XY').box(10, 10, 10)\n"
                "for z in (1, 2):\n"
                "    base = base.faces('>Z').workplane().circle(z).cutBlind(-1)\n"
                "result = base\n"
            ),
        }
    )
    trace_record = {
        "source_id": "src_repeated_target_line_order",
        "execution_status": "ok",
        "snapshots": [
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 1000.0},
            {"target": "base", "source_line": 4, "operation_index": 1, "volume": 990.0},
            {"target": "base", "source_line": 4, "operation_index": 2, "volume": 970.0},
        ],
        "operation_effects": [
            {
                "from_target": "base",
                "to_target": "base",
                "source_line": 4,
                "signed_volume_delta": -10.0,
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "base",
                "to_target": "base",
                "source_line": 4,
                "signed_volume_delta": -20.0,
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }

    graph = build_graph(source, trace=trace_record)
    void_regions = graph.nodes_by_type("void_region")
    assert len(void_regions) == 2
    assert all(node.properties["conservative"] is False for node in void_regions)
    assert [measurement.value for measurement in graph.measurements_for("void_region:base", "volume")] == [10.0]
    assert [measurement.value for measurement in graph.measurements_for("void_region:base:1", "volume")] == [20.0]
    assert any(relation.type == "has_kernel_void_region_geometry" for relation in graph.relations)


def test_trace_backed_geometry_queries_target_compiled_measurements() -> None:
    trace_record = {
        "source_id": "src_geometry_queries",
        "execution_status": "ok",
        "snapshots": [
            {
                "target": "wp3",
                "source_line": 4,
                "operation_index": 0,
                "volume": 62.8,
                "bbox": {"min": [-2, -2, 0], "max": [2, 2, 5]},
                "centroid": [0.0, 0.0, 2.5],
                "topology": {"faces": 3, "edges": 6, "vertices": 4},
            },
            {
                "target": "wp6",
                "source_line": 7,
                "operation_index": 1,
                "volume": 24.0,
                "bbox": {"min": [-2, -1.5, 10], "max": [2, 1.5, 12]},
                "centroid": [0.0, 0.0, 11.0],
                "topology": {"faces": 6, "edges": 12, "vertices": 8},
            },
            {
                "target": "result",
                "source_line": 10,
                "operation_index": 2,
                "volume": 86.8,
                "bbox": {"min": [-2, -2, 0], "max": [2, 2, 12]},
                "centroid": [0.0, 0.0, 5.0],
                "topology": {"faces": 9, "edges": 18, "vertices": 12},
            },
        ],
        "operation_effects": [
            {
                "from_target": "wp2",
                "to_target": "wp3",
                "source_line": 4,
                "signed_volume_delta": 62.8,
                "bbox_delta": {"min": [-2, -2, 0], "max": [2, 2, 5]},
                "centroid_delta": [0.0, 0.0, 2.5],
                "topology_delta": {"faces": 3, "edges": 6, "vertices": 4},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "wp5",
                "to_target": "wp6",
                "source_line": 7,
                "signed_volume_delta": 24.0,
                "bbox_delta": {"min": [-2, -1.5, 10], "max": [2, 1.5, 12]},
                "centroid_delta": [0.0, 0.0, 8.5],
                "topology_delta": {"faces": 6, "edges": 12, "vertices": 8},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "wp6",
                "to_target": "result",
                "source_line": 10,
                "signed_volume_delta": 24.0,
                "bbox_delta": {"min": [None, None, 0], "max": [None, None, 12]},
                "centroid_delta": [0.0, 0.0, -6.0],
                "topology_delta": {"faces": 1, "edges": 2, "vertices": 1},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_geometry_queries", "normalized_code": SOURCE}),
        trace=trace_record,
    )
    assert graph.measurements_for("feature:result", "bbox_span_z")[0].value == 12.0
    assert graph.measurements_for("feature:result", "bbox_min_z")[0].value == 0.0
    assert graph.measurements_for("feature:result", "bbox_max_z")[0].value == 12.0
    assert graph.measurements_for("feature:wp6", "centroid_z")[0].value == 11.0
    assert graph.measurements_for("feature:wp6", "centroid_delta_z")[0].value == 8.5
    assert graph.measurements_for("feature:wp6", "centroid_delta_magnitude")[0].value == 8.5
    assert graph.measurements_for("feature:result", "topology_faces")[0].value == 9.0
    assert graph.measurements_for("feature:wp3", "bbox_delta_span_z")[0].value == 5.0
    assert graph.measurements_for("feature:result", "bbox_delta_span_z")[0].value == 12.0
    assert graph.measurements_for("feature:wp3", "volume_delta_magnitude")[0].value == 62.8
    assert graph.measurements_for("feature:wp6", "topology_delta_faces")[0].value == 6.0
    assert graph.measurements_for("feature:wp6", "topology_delta_edges")[0].value == 12.0
    assert graph.measurements_for("feature:result", "bbox_delta_max_span")[0].value == 12.0

    resolutions = {
        query.query_id.split(":")[-1]: resolve_query(graph, query)
        for query in smoke_queries(graph)
    }
    assert resolutions["largest_compiled_volume_feature"].gold_answer == "feature:result"
    assert resolutions["highest_centroid_feature"].gold_answer == "feature:wp6"
    assert resolutions["largest_compiled_face_count_feature"].gold_answer == "feature:result"
    assert resolutions["largest_positive_volume_delta_feature"].gold_answer == "feature:wp3"
    assert resolutions["largest_bbox_height_delta_feature"].gold_answer == "feature:result"
    assert resolutions["largest_bbox_expansion_feature"].gold_answer == "feature:result"
    assert resolutions["largest_upward_centroid_delta_feature"].gold_answer == "feature:wp6"
    assert resolutions["largest_centroid_shift_feature"].gold_answer == "feature:wp6"
    assert resolutions["largest_face_count_delta_feature"].gold_answer == "feature:wp6"
    assert resolutions["largest_edge_count_delta_feature"].gold_answer == "feature:wp6"
    for key in [
        "largest_compiled_volume_feature",
        "highest_centroid_feature",
        "largest_compiled_face_count_feature",
        "largest_positive_volume_delta_feature",
        "largest_bbox_height_delta_feature",
        "largest_bbox_expansion_feature",
        "largest_upward_centroid_delta_feature",
        "largest_centroid_shift_feature",
        "largest_face_count_delta_feature",
        "largest_edge_count_delta_feature",
    ]:
        row = materialize_row(graph, resolutions[key])
        assert row.release_ready
        assert row.geometry_hop_count > 0
        assert row.measurement_scopes
    report = dataset_report(
        [
            materialize_row(graph, resolution)
            for resolution in resolutions.values()
            if resolution.verifier_status == "resolved"
        ]
    )
    assert report["quality_flags"]["geometry_critical"] >= 3
    assert report["prompt_families"]["largest_compiled_volume_feature"] == 1
    assert report["prompt_families"]["highest_centroid_feature"] == 1
    assert report["prompt_families"]["largest_compiled_face_count_feature"] == 1
    assert report["prompt_families"]["largest_positive_volume_delta_feature"] == 1
    assert report["prompt_families"]["largest_bbox_height_delta_feature"] == 1
    assert report["prompt_families"]["largest_bbox_expansion_feature"] == 1
    assert report["prompt_families"]["largest_upward_centroid_delta_feature"] == 1
    assert report["prompt_families"]["largest_centroid_shift_feature"] == 1
    assert report["prompt_families"]["largest_face_count_delta_feature"] == 1
    assert report["prompt_families"]["largest_edge_count_delta_feature"] == 1


def test_removed_volume_delta_query_targets_largest_kernel_cut_effect() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(10, 10, 5)\n"
        "base = base.faces('>Z').workplane().circle(1).cutBlind(-1)\n"
        "base = base.faces('>Z').workplane().rect(3, 2).cutBlind(-2)\n"
        "result = base\n"
    )
    trace_record = {
        "source_id": "src_removed_volume_delta",
        "execution_status": "ok",
        "snapshots": [
            {
                "target": "base",
                "source_line": 2,
                "operation_index": 0,
                "volume": 500.0,
                "bbox": {"min": [-5, -5, -2.5], "max": [5, 5, 2.5]},
                "centroid": [0.0, 0.0, 0.0],
                "topology": {"faces": 6, "edges": 12, "vertices": 8},
            },
            {
                "target": "base",
                "source_line": 3,
                "operation_index": 1,
                "volume": 490.0,
                "bbox": {"min": [-5, -5, -2.5], "max": [5, 5, 2.5]},
                "centroid": [0.0, 0.0, -0.1],
                "topology": {"faces": 8, "edges": 16, "vertices": 10},
            },
            {
                "target": "base",
                "source_line": 4,
                "operation_index": 2,
                "volume": 470.0,
                "bbox": {"min": [-5, -5, -2.5], "max": [5, 5, 2.5]},
                "centroid": [0.0, 0.0, -0.3],
                "topology": {"faces": 10, "edges": 20, "vertices": 12},
            },
        ],
        "operation_effects": [
            {
                "from_target": "base",
                "to_target": "base",
                "source_line": 3,
                "signed_volume_delta": -10.0,
                "bbox_delta": {"min": [None, None, None], "max": [None, None, None]},
                "centroid_delta": [0.0, 0.0, -0.1],
                "topology_delta": {"faces": 2, "edges": 4, "vertices": 2},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "base",
                "to_target": "base",
                "source_line": 4,
                "signed_volume_delta": -20.0,
                "bbox_delta": {"min": [None, None, None], "max": [None, None, None]},
                "centroid_delta": [0.0, 0.0, -0.2],
                "topology_delta": {"faces": 2, "edges": 4, "vertices": 2},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_removed_volume_delta", "normalized_code": source_code}),
        trace=trace_record,
    )

    assert graph.measurements_for("feature:base:1", "volume_delta_magnitude")[0].value == 10.0
    assert graph.measurements_for("feature:base:2", "volume_delta_magnitude")[0].value == 20.0
    resolutions = {
        query.query_id.split(":")[-1]: resolve_query(graph, query)
        for query in smoke_queries(graph)
    }
    assert resolutions["largest_removed_volume_delta_feature"].gold_answer == "feature:base:2"
    row = materialize_row(graph, resolutions["largest_removed_volume_delta_feature"])
    assert row.release_ready
    assert row.geometry_hop_count > 0
    assert "feature_application_effect" in row.measurement_scopes


def test_bbox_bound_delta_query_targets_largest_compiled_bbox_movement() -> None:
    source_code = (
        "import cadquery as cq\n"
        "wp1 = cq.Workplane('XY').box(2, 2, 2)\n"
        "wp2 = cq.Workplane('XY', origin=(0, 0, 4)).box(2, 2, 2)\n"
        "wp3 = cq.Workplane('XY', origin=(0, 0, 9)).box(2, 2, 2)\n"
        "result = wp1.union(wp2).union(wp3)\n"
    )
    trace_record = {
        "source_id": "src_bbox_bound_delta",
        "execution_status": "ok",
        "snapshots": [
            {
                "target": "wp1",
                "source_line": 2,
                "operation_index": 0,
                "volume": 8.0,
                "bbox": {"min": [-1, -1, -1], "max": [1, 1, 1]},
                "centroid": [0.0, 0.0, 0.0],
                "topology": {"faces": 6, "edges": 12, "vertices": 8},
            },
            {
                "target": "wp2",
                "source_line": 3,
                "operation_index": 1,
                "volume": 8.0,
                "bbox": {"min": [-1, -1, 3], "max": [1, 1, 5]},
                "centroid": [0.0, 0.0, 4.0],
                "topology": {"faces": 6, "edges": 12, "vertices": 8},
            },
            {
                "target": "wp3",
                "source_line": 4,
                "operation_index": 2,
                "volume": 8.0,
                "bbox": {"min": [-1, -1, 8], "max": [1, 1, 10]},
                "centroid": [0.0, 0.0, 9.0],
                "topology": {"faces": 6, "edges": 12, "vertices": 8},
            },
            {
                "target": "result",
                "source_line": 5,
                "operation_index": 3,
                "volume": 24.0,
                "bbox": {"min": [-1, -1, -1], "max": [1, 1, 10]},
                "centroid": [0.0, 0.0, 4.3333333333],
                "topology": {"faces": 18, "edges": 36, "vertices": 24},
            },
        ],
        "operation_effects": [
            {
                "from_target": "wp1",
                "to_target": "wp2",
                "source_line": 3,
                "signed_volume_delta": 8.0,
                "bbox_delta": {"min": [0, 0, 4], "max": [0, 0, 4]},
                "centroid_delta": [0.0, 0.0, 4.0],
                "topology_delta": {"faces": 0, "edges": 0, "vertices": 0},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "wp2",
                "to_target": "wp3",
                "source_line": 4,
                "signed_volume_delta": 8.0,
                "bbox_delta": {"min": [0, 0, 5], "max": [0, 0, 5]},
                "centroid_delta": [0.0, 0.0, 5.0],
                "topology_delta": {"faces": 0, "edges": 0, "vertices": 0},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_bbox_bound_delta", "normalized_code": source_code}),
        trace=trace_record,
    )

    resolutions = {
        query.query_id.split(":")[-1]: resolve_query(graph, query)
        for query in smoke_queries(graph)
    }
    assert resolutions["largest_bbox_min_z_delta_feature"].gold_answer == "feature:wp3"
    row = materialize_row(graph, resolutions["largest_bbox_min_z_delta_feature"])
    assert row.release_ready
    assert row.geometry_hop_count > 0
    assert "feature_application_effect" in row.measurement_scopes


def test_centroid_queries_require_meaningful_geometry_margin() -> None:
    trace_record = {
        "source_id": "src_centroid_margin",
        "execution_status": "ok",
        "snapshots": [
            {
                "target": "wp3",
                "source_line": 4,
                "operation_index": 0,
                "volume": 62.8,
                "bbox": {"min": [-2, -2, 0], "max": [2, 2, 5]},
                "centroid": [0.0, 0.0, 1e-12],
                "topology": {"faces": 3},
            },
            {
                "target": "wp6",
                "source_line": 7,
                "operation_index": 1,
                "volume": 24.0,
                "bbox": {"min": [-2, -1.5, 10], "max": [2, 1.5, 12]},
                "centroid": [0.0, 0.0, 2e-12],
                "topology": {"faces": 6},
            },
        ],
        "operation_effects": [
            {
                "from_target": "wp2",
                "to_target": "wp3",
                "source_line": 4,
                "signed_volume_delta": 62.8,
                "centroid_delta": [0.0, 0.0, 1e-12],
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "wp5",
                "to_target": "wp6",
                "source_line": 7,
                "signed_volume_delta": 24.0,
                "centroid_delta": [0.0, 0.0, 2e-12],
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_centroid_margin", "normalized_code": SOURCE}),
        trace=trace_record,
    )
    families = {query.query_id.rsplit(":", 1)[-1] for query in smoke_queries(graph)}
    assert "highest_centroid_feature" not in families
    assert "largest_upward_centroid_delta_feature" not in families


def test_kernel_selector_trace_produces_release_grade_face_identity() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(2, 2, 2)\n"
        "sel_top = base.faces('>Z')\n"
        "sel_bottom = base.faces('<Z')\n"
        "sel_all = base.faces()\n"
    )
    trace_record = {
        "source_id": "src_selector_kernel",
        "execution_status": "ok",
        "snapshots": [
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 8.0, "bbox": {"min": [-1, -1, -1], "max": [1, 1, 1]}, "topology": {"faces": 6}},
        ],
        "operation_effects": [],
        "selector_results": [
            {
                "target": "sel_top",
                "selector": ">Z",
                "source_line": 3,
                "selector_index": 0,
                "selected_count": 1,
                "shape_types": ["Face"],
                "bbox_signatures": [{"min": [-1, -1, 1], "max": [1, 1, 1]}],
                "evidence": "cadquery_selector_result",
            },
            {
                "target": "sel_bottom",
                "selector": "<Z",
                "source_line": 4,
                "selector_index": 1,
                "selected_count": 1,
                "shape_types": ["Face"],
                "bbox_signatures": [{"min": [-1, -1, -1], "max": [1, 1, -1]}],
                "evidence": "cadquery_selector_result",
            },
            {
                "target": "sel_all",
                "selector": "",
                "source_line": 5,
                "selector_index": 2,
                "selected_count": 6,
                "shape_types": ["Face", "Face", "Face", "Face", "Face", "Face"],
                "bbox_signatures": [
                    {"min": [-2, -1, -0.5], "max": [2, 1, -0.5]},
                    {"min": [-1, -1, -0.4], "max": [1, 1, -0.4]},
                    {"min": [-1, 1, -0.3], "max": [1, 1, -0.3]},
                    {"min": [-1, -1, -0.2], "max": [1, -1, -0.2]},
                    {"min": [1, -1, -0.1], "max": [1, 1, -0.1]},
                    {"min": [-1, -1, 0.0], "max": [-1, 1, 0.0]},
                ],
                "evidence": "cadquery_selector_result",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_selector_kernel", "normalized_code": source_code}),
        trace=trace_record,
    )
    kernel_faces = [node for node in graph.nodes_by_type("face") if node.properties.get("kernel_backed")]
    assert len(kernel_faces) == 8
    assert any(relation.type == "has_kernel_stable_face_id" for relation in graph.relations)
    assert graph.measurements_for(kernel_faces[0].id, "bbox")
    face_z_values = sorted({graph.measurements_for(face.id, "bbox_max_z")[0].value for face in kernel_faces})
    assert face_z_values[0] == -1.0
    assert face_z_values[-1] == 1.0
    assert graph.measurements_for(kernel_faces[0].id, "face_center")
    assert graph.measurements_for(kernel_faces[0].id, "distance_to_origin")
    assert graph.measurements_for(kernel_faces[0].id, "face_area")
    assert any(relation.source_id == kernel_faces[0].id and relation.type == "distance_to" for relation in graph.relations)
    assert graph.measurements_for("selector:sel_all_faces_all", "selected_count")[0].value == 6
    assert any(
        relation.source_id == "selector:sel_all_faces_all"
        and relation.type == "has_kernel_stable_face_id"
        and relation.target_id.startswith("face:")
        for relation in graph.relations
    )
    selector = graph.nodes_by_type("selector")[0]
    assert graph.measurements_for(selector.id, "selected_count")[0].value == 1

    resolutions = {
        query.query_id.split(":")[-1]: resolve_query(graph, query)
        for query in smoke_queries(graph)
    }
    selected_face = resolutions["selected_face"]
    assert selected_face.verifier_status == "resolved"
    assert "has_kernel_stable_face_id" in selected_face.relation_families
    selected_face_row = materialize_row(graph, selected_face)
    assert selected_face_row.release_ready
    assert "selector_identity_surrogate" not in selected_face_row.quarantine_reasons

    highest_face = resolutions["highest_kernel_selected_face"]
    assert highest_face.verifier_status == "resolved"
    highest_node = graph.node(highest_face.gold_answer)
    assert highest_node is not None
    assert highest_node.properties["stable_selector"] == ">Z"
    highest_face_row = materialize_row(graph, highest_face)
    assert highest_face_row.release_ready
    assert highest_face_row.geometry_hop_count > 0
    assert "entity_geometry" in highest_face_row.measurement_scopes
    assert "has_kernel_stable_face_id" in highest_face_row.relation_families

    nearest_face_center = resolutions["nearest_kernel_selected_face_center_to_origin"]
    assert nearest_face_center.verifier_status == "resolved"
    nearest_face_node = graph.node(nearest_face_center.gold_answer)
    assert nearest_face_node is not None
    assert graph.measurements_for(nearest_face_node.id, "distance_to_origin")[0].value == 0.4
    nearest_face_center_row = materialize_row(graph, nearest_face_center)
    assert nearest_face_center_row.release_ready
    assert nearest_face_center_row.geometry_hop_count > 0
    assert "has_kernel_stable_face_id" in nearest_face_center_row.relation_families
    assert "distance_to" in nearest_face_center_row.relation_families
    assert "relation_metric" in nearest_face_center_row.measurement_scopes

    largest_face_area = resolutions["largest_kernel_selected_face_area"]
    assert largest_face_area.verifier_status == "resolved"
    largest_area_node = graph.node(largest_face_area.gold_answer)
    assert largest_area_node is not None
    assert graph.measurements_for(largest_area_node.id, "face_area")[0].value == 8.0
    largest_face_area_row = materialize_row(graph, largest_face_area)
    assert largest_face_area_row.release_ready
    assert largest_face_area_row.geometry_hop_count > 0
    assert "has_kernel_stable_face_id" in largest_face_area_row.relation_families
    assert "entity_geometry" in largest_face_area_row.measurement_scopes

    largest_selector_count = resolutions["largest_kernel_selector_count"]
    assert largest_selector_count.verifier_status == "resolved"
    assert largest_selector_count.gold_answer == "selector:sel_all_faces_all"
    selector_count_row = materialize_row(graph, largest_selector_count)
    assert selector_count_row.release_ready
    assert selector_count_row.geometry_hop_count > 0
    assert "snapshot_state" in selector_count_row.measurement_scopes
    assert "has_kernel_stable_face_id" in selector_count_row.relation_families
    assert "selector_identity_surrogate" not in selector_count_row.quarantine_reasons


def test_kernel_face_selector_trace_produces_release_grade_face_spatial_relations() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(2, 2, 2)\n"
        "all_faces = base.faces()\n"
    )
    trace_record = {
        "source_id": "src_selector_face_spatial",
        "execution_status": "ok",
        "snapshots": [
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 8.0, "bbox": {"min": [-1, -1, -1], "max": [1, 1, 1]}, "topology": {"faces": 6}},
        ],
        "operation_effects": [],
        "selector_results": [
            {
                "target": "all_faces",
                "selector": "",
                "source_line": 3,
                "selector_index": 0,
                "selected_count": 6,
                "shape_types": ["Face", "Face", "Face", "Face", "Face", "Face"],
                "bbox_signatures": [
                    {"min": [-1, -1, -1], "max": [1, 1, -1]},
                    {"min": [-1, -1, 1], "max": [1, 1, 1]},
                    {"min": [-1, -1, -1], "max": [1, -1, 1]},
                    {"min": [-1, 1, -1], "max": [1, 1, 1]},
                    {"min": [-1, -1, -1], "max": [-1, 1, 1]},
                    {"min": [1, -1, -1], "max": [1, 1, 1]},
                ],
                "evidence": "cadquery_selector_result",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_selector_face_spatial", "normalized_code": source_code}),
        trace=trace_record,
    )
    kernel_faces = [node for node in graph.nodes_by_type("face") if node.properties.get("kernel_backed")]
    assert len(kernel_faces) == 6
    assert {graph.measurements_for(face.id, "normal_axis")[0].value for face in kernel_faces} == {"x", "y", "z"}
    assert any(relation.type == "parallel_to" for relation in graph.relations)
    assert any(relation.type == "perpendicular_to" for relation in graph.relations)
    assert any(relation.type == "adjacent_to" for relation in graph.relations)
    assert any(relation.type == "intersects" for relation in graph.relations)
    assert any(relation.type == "opposite_to" for relation in graph.relations)

    resolutions = {
        query.query_id.split(":")[-1]: resolve_query(graph, query)
        for query in smoke_queries(graph)
    }
    spatial_face = resolutions["highest_positive_x_flat_opposite_adjacent_perpendicular_kernel_face"]
    assert spatial_face.verifier_status == "resolved"
    resolved_node = graph.node(spatial_face.gold_answer)
    assert resolved_node is not None
    assert graph.measurements_for(resolved_node.id, "bbox_max_z")[0].value == 1.0
    assert graph.measurements_for(resolved_node.id, "bbox_span_z")[0].value == 0.0
    spatial_face_row = materialize_row(graph, spatial_face)
    assert spatial_face_row.release_ready
    assert "has_kernel_stable_face_id" in spatial_face_row.relation_families
    assert "opposite_to" in spatial_face_row.relation_families
    assert "adjacent_to" in spatial_face_row.relation_families
    assert "perpendicular_to" in spatial_face_row.relation_families
    assert "entity_geometry" in spatial_face_row.measurement_scopes


def test_loop_variable_selectors_match_kernel_trace_by_source_line() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(2, 2, 2)\n"
        "for tag in ('>Z', '<Z'):\n"
        "    sel = base.faces(tag)\n"
    )
    trace_record = {
        "source_id": "src_selector_loop_trace",
        "execution_status": "ok",
        "snapshots": [
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 8.0, "bbox": {"min": [-1, -1, -1], "max": [1, 1, 1]}, "topology": {"faces": 6}},
        ],
        "operation_effects": [],
        "selector_results": [
            {
                "target": "sel",
                "selector": "tag",
                "source_line": 4,
                "selector_index": 0,
                "selected_count": 1,
                "shape_types": ["Face"],
                "bbox_signatures": [{"min": [-1, -1, 1], "max": [1, 1, 1]}],
                "evidence": "cadquery_selector_result",
            },
            {
                "target": "sel",
                "selector": "tag",
                "source_line": 4,
                "selector_index": 1,
                "selected_count": 1,
                "shape_types": ["Face"],
                "bbox_signatures": [{"min": [-1, -1, -1], "max": [1, 1, -1]}],
                "evidence": "cadquery_selector_result",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_selector_loop_trace", "normalized_code": source_code}),
        trace=trace_record,
    )

    selectors = graph.nodes_by_type("selector")
    assert [selector.properties["selector"] for selector in selectors] == [">Z", "<Z"]
    assert all(selector.properties["kernel_backed"] for selector in selectors)
    kernel_faces = [node for node in graph.nodes_by_type("face") if node.properties.get("kernel_backed")]
    assert len(kernel_faces) == 2
    assert sorted(graph.measurements_for(face.id, "bbox_max_z")[0].value for face in kernel_faces) == [-1.0, 1.0]


def test_trace_record_selector_results_are_preserved_for_graph_extraction() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(2, 2, 2)\n"
        "sel_top = base.faces('>Z')\n"
    )
    trace_record = TraceRecord(
        source_id="src_trace_record_selector",
        execution_status="ok",
        snapshots=[
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 8.0, "bbox": {"min": [-1, -1, -1], "max": [1, 1, 1]}, "topology": {"faces": 6}},
        ],
        operation_effects=[],
        selector_results=[
            {
                "target": "sel_top",
                "selector": ">Z",
                "selector_kind": "faces",
                "source_line": 3,
                "selector_index": 0,
                "selected_count": 1,
                "shape_types": ["Face"],
                "bbox_signatures": [{"min": [-1, -1, 1], "max": [1, 1, 1]}],
                "evidence": "cadquery_selector_result",
            }
        ],
    )
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_trace_record_selector", "normalized_code": source_code}),
        trace=trace_record,
    )
    selector = graph.nodes_by_type("selector")[0]
    assert selector.properties["kernel_backed"]
    assert any(relation.type == "has_kernel_stable_face_id" for relation in graph.relations)


def test_kernel_edge_selector_trace_produces_release_grade_edge_identity() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(2, 2, 2)\n"
        "top_edges = base.edges('|Z')\n"
        "all_edges = base.edges()\n"
    )
    trace_record = {
        "source_id": "src_selector_edges",
        "execution_status": "ok",
        "snapshots": [
            {"target": "base", "source_line": 2, "operation_index": 0, "volume": 8.0, "bbox": {"min": [-1, -1, -1], "max": [1, 1, 1]}, "topology": {"edges": 12}},
        ],
        "operation_effects": [],
        "selector_results": [
            {
                "target": "top_edges",
                "selector": "|Z",
                "selector_kind": "edges",
                "source_line": 3,
                "selector_index": 0,
                "selected_count": 4,
                "shape_types": ["Edge", "Edge", "Edge", "Edge"],
                "bbox_signatures": [
                    {"min": [-1, -1, -1], "max": [-1, -1, 1]},
                    {"min": [-1, 1, -1], "max": [-1, 1, 1]},
                    {"min": [1, -1, -1], "max": [1, -1, 1]},
                    {"min": [1, 1, -1], "max": [1, 1, 2]},
                ],
                "evidence": "cadquery_selector_result",
            },
            {
                "target": "all_edges",
                "selector": "",
                "selector_kind": "edges",
                "source_line": 4,
                "selector_index": 1,
                "selected_count": 12,
                "shape_types": ["Edge"] * 12,
                "bbox_signatures": [
                    {"min": [-1, -1, -1], "max": [1, -1, -1]},
                    {"min": [-1, 1, -1], "max": [1, 1, -1]},
                    {"min": [-1, -1, 1], "max": [1, -1, 1]},
                    {"min": [-1, 1, 1], "max": [1, 1, 1]},
                    {"min": [-1, -1, -1], "max": [-1, 1, -1]},
                    {"min": [1, -1, -1], "max": [1, 1, -1]},
                    {"min": [-1, -1, 1], "max": [-1, 1, 1]},
                    {"min": [1, -1, 1], "max": [1, 1, 1]},
                    {"min": [-1, -1, -1], "max": [-1, -1, 1]},
                    {"min": [-1, 1, -1], "max": [-1, 1, 1]},
                    {"min": [1, -1, -1], "max": [1, -1, 1]},
                    {"min": [1, 1, -1], "max": [1, 1, 1]},
                ],
                "evidence": "cadquery_selector_result",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_selector_edges", "normalized_code": source_code}),
        trace=trace_record,
    )
    kernel_edges = [node for node in graph.nodes_by_type("edge") if node.properties.get("kernel_backed")]
    kernel_endpoints = [node for node in graph.nodes_by_type("edge_endpoint") if node.properties.get("kernel_backed")]
    assert len(kernel_edges) == 16
    assert len(kernel_endpoints) >= 8
    assert graph.node("origin:global") is not None
    assert any(relation.type == "has_kernel_stable_edge_id" for relation in graph.relations)
    assert any(relation.type == "endpoint_of" for relation in graph.relations)
    assert any(relation.type == "contained_in" for relation in graph.relations)
    assert any(
        relation.type == "distance_to" and relation.target_id == "origin:global"
        for relation in graph.relations
    )
    assert any(relation.type == "has_endpoint" for relation in graph.relations)
    assert graph.measurements_for(kernel_edges[0].id, "bbox")
    assert graph.measurements_for(kernel_edges[0].id, "midpoint")
    assert graph.measurements_for(kernel_edges[0].id, "midpoint_distance_to_origin")
    assert graph.measurements_for(kernel_endpoints[0].id, "coordinate_z")
    assert graph.measurements_for(kernel_endpoints[0].id, "distance_to_origin")
    assert graph.measurements_for(kernel_edges[0].id, "dominant_axis")
    assert any(relation.type == "perpendicular_to" for relation in graph.relations)
    assert any(relation.type == "parallel_to" for relation in graph.relations)
    assert any(relation.type == "adjacent_to" for relation in graph.relations)
    assert any(relation.type == "intersects" for relation in graph.relations)
    assert any(relation.type == "opposite_to" for relation in graph.relations)
    assert any(relation.type == "same_length_as" for relation in graph.relations)
    assert any(relation.type == "longer_than" for relation in graph.relations)
    assert any(relation.type == "shorter_than" for relation in graph.relations)

    resolutions = {
        query.query_id.split(":")[-1]: resolve_query(graph, query)
        for query in smoke_queries(graph)
    }
    highest_edge = resolutions["highest_kernel_selected_edge"]
    assert highest_edge.verifier_status == "resolved"
    highest_edge_row = materialize_row(graph, highest_edge)
    assert highest_edge_row.release_ready
    assert "has_kernel_stable_edge_id" in highest_edge_row.relation_families
    assert "selector_identity_surrogate" not in highest_edge_row.quarantine_reasons

    selector_count = resolutions["largest_kernel_edge_selector_count"]
    assert selector_count.verifier_status == "resolved"
    assert selector_count.gold_answer == "selector:all_edges_edges_all"
    selector_count_row = materialize_row(graph, selector_count)
    assert selector_count_row.release_ready
    assert "has_kernel_stable_edge_id" in selector_count_row.relation_families

    spatial_edge = resolutions["highest_negative_y_x_span_opposite_intersecting_adjacent_perpendicular_kernel_edge"]
    assert spatial_edge.verifier_status == "resolved"
    spatial_edge_row = materialize_row(graph, spatial_edge)
    assert spatial_edge_row.release_ready
    assert spatial_edge_row.geometry_hop_count > 0
    assert "has_kernel_stable_edge_id" in spatial_edge_row.relation_families
    assert "perpendicular_to" in spatial_edge_row.relation_families
    assert "adjacent_to" in spatial_edge_row.relation_families
    assert "intersects" in spatial_edge_row.relation_families
    assert "opposite_to" in spatial_edge_row.relation_families
    assert "entity_geometry" in spatial_edge_row.measurement_scopes

    midpoint_edge = resolutions["highest_y_positive_z_x_span_kernel_edge_midpoint"]
    assert midpoint_edge.verifier_status == "resolved"
    midpoint_edge_row = materialize_row(graph, midpoint_edge)
    assert midpoint_edge_row.release_ready
    midpoint_edge_node = graph.node(midpoint_edge.gold_answer)
    assert midpoint_edge_node is not None
    assert graph.measurements_for(midpoint_edge_node.id, "midpoint_y")[0].value > 0
    assert graph.measurements_for(midpoint_edge_node.id, "midpoint_z")[0].value > 0
    assert "has_kernel_stable_edge_id" in midpoint_edge_row.relation_families
    assert "distance_to" in midpoint_edge_row.relation_families
    assert "relation_metric" in midpoint_edge_row.measurement_scopes
    assert "entity_geometry" in midpoint_edge_row.measurement_scopes

    endpoint_resolution = resolutions["highest_positive_x_negative_y_contained_kernel_edge_endpoint"]
    assert endpoint_resolution.verifier_status == "resolved"
    endpoint_row = materialize_row(graph, endpoint_resolution)
    assert endpoint_row.release_ready
    assert endpoint_row.gold_answer
    assert "endpoint_of" in endpoint_row.relation_families
    assert "contained_in" in endpoint_row.relation_families
    assert "distance_to" in endpoint_row.relation_families
    assert "relation_metric" in endpoint_row.measurement_scopes
    assert "entity_geometry" in endpoint_row.measurement_scopes


def test_kernel_edge_length_query_uses_compiled_midpoint_geometry() -> None:
    source_code = (
        "import cadquery as cq\n"
        "body = cq.Workplane('XY').box(120, 33, 54).edges()\n"
    )
    edge_bboxes = [
        {"min": [-60.0, -16.5, -27.0], "max": [-60.0, -16.5, 27.0]},
        {"min": [-60.0, -16.5, 27.0], "max": [-60.0, 16.5, 27.0]},
        {"min": [-60.0, 16.5, -27.0], "max": [-60.0, 16.5, 27.0]},
        {"min": [-60.0, -16.5, -27.0], "max": [-60.0, 16.5, -27.0]},
        {"min": [60.0, -16.5, -27.0], "max": [60.0, -16.5, 27.0]},
        {"min": [60.0, -16.5, 27.0], "max": [60.0, 16.5, 27.0]},
        {"min": [60.0, 16.5, -27.0], "max": [60.0, 16.5, 27.0]},
        {"min": [60.0, -16.5, -27.0], "max": [60.0, 16.5, -27.0]},
        {"min": [-60.0, -16.5, -27.0], "max": [60.0, -16.5, -27.0]},
        {"min": [-60.0, -16.5, 27.0], "max": [60.0, -16.5, 27.0]},
        {"min": [-60.0, 16.5, -27.0], "max": [60.0, 16.5, -27.0]},
        {"min": [-60.0, 16.5, 27.0], "max": [60.0, 16.5, 27.0]},
    ]
    trace_record = {
        "source_id": "src_edge_length_query",
        "execution_status": "ok",
        "snapshots": [
            {"target": "body", "source_line": 2, "operation_index": 0, "volume": 213840.0, "bbox": {"min": [-60.0, -16.5, -27.0], "max": [60.0, 16.5, 27.0]}, "topology": {"edges": 12}},
        ],
        "operation_effects": [],
        "selector_results": [
            {
                "target": "body",
                "selector": "",
                "selector_kind": "edges",
                "source_line": 2,
                "selector_index": 0,
                "selected_count": 12,
                "shape_types": ["Edge"] * 12,
                "bbox_signatures": edge_bboxes,
                "evidence": "cadquery_selector_result",
            },
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_edge_length_query", "normalized_code": source_code}),
        trace=trace_record,
    )
    queries = {
        query.query_id.split(":")[-1]: query
        for query in smoke_queries(graph)
    }
    resolution = resolve_query(graph, queries["rightmost_short_positive_z_kernel_edge"])
    assert resolution.verifier_status == "resolved"
    edge = graph.node(resolution.gold_answer)
    assert edge is not None
    assert graph.measurements_for(edge.id, "edge_length")[0].value == 33.0
    assert graph.measurements_for(edge.id, "midpoint_x")[0].value == 60.0
    assert graph.measurements_for(edge.id, "midpoint_z")[0].value == 27.0
    row = materialize_row(graph, resolution)
    assert row.release_ready
    assert "has_kernel_stable_edge_id" in row.relation_families
    assert "relation_metric" in row.measurement_scopes
    assert "entity_geometry" in row.measurement_scopes

    ordering_resolution = resolve_query(graph, queries["frontmost_longer_positive_z_kernel_edge"])
    assert ordering_resolution.verifier_status == "resolved"
    ordered_edge = graph.node(ordering_resolution.gold_answer)
    assert ordered_edge is not None
    assert graph.measurements_for(ordered_edge.id, "edge_length")[0].value == 120.0
    assert graph.measurements_for(ordered_edge.id, "midpoint_y")[0].value == 16.5
    assert graph.measurements_for(ordered_edge.id, "midpoint_z")[0].value == 27.0
    ordering_row = materialize_row(graph, ordering_resolution)
    assert ordering_row.release_ready
    assert "has_kernel_stable_edge_id" in ordering_row.relation_families
    assert "longer_than" in ordering_row.relation_families
    assert "entity_geometry" in ordering_row.measurement_scopes

    same_length_resolution = resolve_query(graph, queries["frontmost_same_length_longer_positive_z_kernel_edge"])
    assert same_length_resolution.verifier_status == "resolved"
    same_length_edge = graph.node(same_length_resolution.gold_answer)
    assert same_length_edge is not None
    assert graph.measurements_for(same_length_edge.id, "edge_length")[0].value == 120.0
    assert graph.measurements_for(same_length_edge.id, "midpoint_y")[0].value == 16.5
    assert graph.measurements_for(same_length_edge.id, "midpoint_z")[0].value == 27.0
    same_length_row = materialize_row(graph, same_length_resolution)
    assert same_length_row.release_ready
    assert "has_kernel_stable_edge_id" in same_length_row.relation_families
    assert "same_length_as" in same_length_row.relation_families
    assert "longer_than" in same_length_row.relation_families
    assert "entity_geometry" in same_length_row.measurement_scopes

    shorter_resolution = resolve_query(graph, queries["rightmost_shorter_positive_z_kernel_edge"])
    assert shorter_resolution.verifier_status == "resolved"
    shorter_edge = graph.node(shorter_resolution.gold_answer)
    assert shorter_edge is not None
    assert graph.measurements_for(shorter_edge.id, "edge_length")[0].value == 33.0
    assert graph.measurements_for(shorter_edge.id, "midpoint_x")[0].value == 60.0
    assert graph.measurements_for(shorter_edge.id, "midpoint_z")[0].value == 27.0
    shorter_row = materialize_row(graph, shorter_resolution)
    assert shorter_row.release_ready
    assert "has_kernel_stable_edge_id" in shorter_row.relation_families
    assert "shorter_than" in shorter_row.relation_families
    assert "entity_geometry" in shorter_row.measurement_scopes


def test_operation_graph_extraction_covers_assignments_and_chains() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    operations = graph.nodes_by_type("operation")
    assert any(node.properties["operation"] == "circle" for node in operations)
    assert any(node.properties["operation"] == "close" for node in operations)
    assert graph.node("feature:wp3") is not None
    assert any(relation.type == "before" for relation in graph.relations)
    assert any(relation.type == "input_to" for relation in graph.relations)
    assert any(relation.type == "parameter_of" for relation in graph.relations)


def test_profile_geometry_helpers() -> None:
    assert round(circle_profile(2)["area"], 6) == 12.566371
    assert rect_profile(4, 3)["edge_count"] == 4
    poly = polyline_profile([(0, 0), (2, 0), (0, 2)])
    assert poly["area"] == 2
    assert poly["vertex_count"] == 3


def test_profiles_and_workplanes_are_linked() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    profiles = graph.nodes_by_type("profile")
    assert {node.properties["kind"] for node in profiles} >= {"circle", "rect", "polyline"}
    assert graph.node("workplane:wp4").properties["origin"] == [0.0, 0.0, 10.0]
    assert project_local_point(graph.node("workplane:wp4").properties, [1.0, 2.0]) == [1.0, 2.0, 10.0]
    assert any(relation.type == "located_on" for relation in graph.relations)
    assert graph.measurements_for("profile:wp2", "area")


def test_relation_registry_contains_required_families() -> None:
    for relation in ["before", "after", "input_to", "parameter_of", "uses_profile", "located_on", "adds_material_to", "same_selected_face_as", "has_material_region_geometry", "point_on_path", "segment_on_path"]:
        assert relation in RELATION_FAMILIES


def test_query_resolver_argmax_and_reject_unless_unique() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    query = QueryProgram(
        query_id="q_largest_profile",
        target_type="profile",
        aggregation="argmax",
        aggregation_metric="area",
        hop_count=1,
    )
    resolution = resolve_query(graph, query)
    assert resolution.verifier_status == "resolved"
    assert resolution.gold_answer == "profile:wp2"

    ambiguous = QueryProgram(query_id="q_many_profiles", target_type="profile")
    ambiguous_resolution = resolve_query(graph, ambiguous)
    assert ambiguous_resolution.verifier_status == "failed"
    assert ambiguous_resolution.candidate_trace.failure_reason == "not_unique"


def test_low_and_multi_hop_smoke_queries_render_and_materialize() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    queries = smoke_queries(graph)
    assert {query.hop_count for query in queries} >= {0, 1, 2, 3}
    resolved = [resolve_query(graph, query) for query in queries]
    assert any(resolution.verifier_status == "resolved" for resolution in resolved)
    row = materialize_row(graph, next(resolution for resolution in resolved if resolution.verifier_status == "resolved"))
    prompt = render_prompt(graph.source["source_code"], resolved[0].query_program)
    assert "Given the CadQuery script" in prompt.prompt
    assert prompt.prompt_version == "cadqa_prompt_v2"
    assert prompt.prompt_template_id.startswith("checklist_constraints_v1:")
    assert all(clue["template_id"] == prompt.prompt_template_id for clue in prompt.clue_map)
    assert row.prompt_template_id.startswith("checklist_constraints_v1:")
    assert row.candidate_trace["final_candidates"]
    report = validate_rows([to_jsonable(row)])
    assert report["valid"]


def test_prompt_templates_yaml_controls_generated_prompt_wording() -> None:
    registry = prompt_template_registry()
    query = QueryProgram(
        query_id="graph:src:q3:highest_kernel_selected_face",
        target_type="face",
        clauses=[
            Clause(
                id="has_kernel_selector_identity",
                kind="has_relation",
                relation="has_kernel_stable_face_id",
                target_type="selector",
            ),
            Clause(
                id="has_selected_face_bbox",
                kind="has_measurement",
                metric="bbox_max_z",
            ),
        ],
        aggregation="argmax",
        aggregation_metric="bbox_max_z",
        hop_count=3,
    )

    rendered = render_prompt("import cadquery as cq\n", query)

    assert registry["clause_templates"]["has_kernel_selector_identity"] in rendered.prompt
    assert registry["clause_templates"]["has_selected_face_bbox"] in rendered.prompt
    assert registry["aggregation_templates"]["argmax"].format(
        metric="bbox_max_z",
        metric_label=registry["metric_labels"]["bbox_max_z"],
    ) in rendered.prompt
    assert rendered.prompt_template_id == (
        "checklist_constraints_v1:face:"
        "relation_has_kernel_stable_face_id_measurement_bbox_max_z:argmax_bbox_max_z"
    )


def test_prompt_clause_templates_use_domain_wording() -> None:
    implementation_terms = {
        "cadquery",
        "compiled",
        "computed",
        "extracted",
        "implementation",
        "kernel",
        "script",
        "selector",
        "selector-result",
        "snapshot",
        "visible",
    }
    clause_templates = prompt_template_registry()["clause_templates"]
    for key, template in clause_templates.items():
        lowered = template.lower()
        assert not implementation_terms & set(lowered.replace("-", " ").split()), key
        assert "selector-result" not in lowered, key


def test_prompt_metric_labels_hide_internal_measurement_names() -> None:
    rendered = render_prompt(
        "import cadquery as cq\n",
        QueryProgram(
            query_id="graph:src:q3:highest_kernel_selected_face",
            target_type="face",
            aggregation="argmax",
            aggregation_metric="bbox_max_z",
        ),
    )

    assert "greatest maximum Z height" in rendered.prompt
    assert "bbox_max_z" not in rendered.prompt


def test_value_bearing_measurement_clause_resolves_and_renders() -> None:
    graph = OntologyGraph(graph_id="graph:value", source={"source_id": "src_value", "source_code": "import cadquery as cq\n"})
    for node_id, volume, centroid_z in [
        ("feature:a", 12.0, 1.0),
        ("feature:b", 12.0 + 1e-7, 3.0),
        ("feature:c", 8.0, 9.0),
    ]:
        graph.add_node(Node(node_id, "feature", node_id))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid_z", centroid_z))
    query = QueryProgram(
        query_id="graph:value:q4:highest_equal_volume_feature",
        target_type="feature",
        clauses=[
            Clause(
                id="has_compiled_volume_value",
                kind="has_measurement",
                metric="volume",
                value=12.0,
            ),
            Clause(
                id="has_compiled_centroid",
                kind="has_measurement",
                metric="centroid_z",
            ),
        ],
        aggregation="argmax",
        aggregation_metric="centroid_z",
        hop_count=3,
        min_individual_clause_candidates=2,
    )

    resolution = resolve_query(graph, query)
    row = materialize_row(graph, resolution)

    assert resolution.verifier_status == "resolved"
    assert resolution.gold_answer == "feature:b"
    assert "solid volume of 12.0" in row.prompt
    assert "greatest centroid height" in row.prompt
    assert row.candidate_trace["steps"][1]["after"] == ["feature:a", "feature:b"]
    assert dataset_report([row])["quality_flags"]["value_bearing_measurement"] == 1
    assert dataset_report([row])["measurement_value_policy"] == {
        "value_bucket_decimals": 6,
        "value_match_tolerance": 1e-6,
    }
    assert release_balance_report([to_jsonable(row)])["measurement_value_policy"] == {
        "value_bucket_decimals": 6,
        "value_match_tolerance": 1e-6,
    }


def test_smoke_queries_mine_equal_value_measurement_distractors() -> None:
    graph = OntologyGraph(graph_id="graph:equal", source={"source_id": "src_equal", "source_code": "import cadquery as cq\n"})
    for node_id, volume, centroid_z in [
        ("feature:a", 20.0, 1.0),
        ("feature:b", 20.0, 4.0),
        ("feature:c", 5.0, 9.0),
    ]:
        graph.add_node(Node(node_id, "feature", node_id))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid_z", centroid_z))

    queries = {query.query_id.rsplit(":", 1)[-1]: query for query in smoke_queries(graph)}
    query = queries["highest_equal_volume_feature"]
    resolution = resolve_query(graph, query)
    row = materialize_row(graph, resolution)

    assert query.clauses[0].value == 20.0
    assert resolution.verifier_status == "resolved"
    assert resolution.gold_answer == "feature:b"
    assert "solid volume of 20.0" in row.prompt
    assert row.logical_hop_count == 3
    assert row.geometry_hop_count == 3


def test_smoke_queries_mine_equal_centroid_and_height_values() -> None:
    graph = OntologyGraph(graph_id="graph:equal_more", source={"source_id": "src_equal_more", "source_code": "import cadquery as cq\n"})
    for node_id, volume, centroid_z, bbox_span_z in [
        ("feature:a", 10.0, -0.0, 5.0),
        ("feature:b", 20.0, 0.0, 5.0),
        ("feature:c", 5.0, 9.0, 1.0),
    ]:
        graph.add_node(Node(node_id, "feature", node_id))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid_z", centroid_z))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "bbox_span_z", bbox_span_z))

    queries = {query.query_id.rsplit(":", 1)[-1]: query for query in smoke_queries(graph)}
    centroid_query = queries["largest_equal_centroid_height_feature"]
    height_query = queries["largest_equal_bbox_height_feature"]
    centroid_row = materialize_row(graph, resolve_query(graph, centroid_query))
    height_row = materialize_row(graph, resolve_query(graph, height_query))

    assert centroid_query.clauses[0].value == 0.0
    assert centroid_row.gold_answer == "feature:b"
    assert "solid centroid height of 0.0" in centroid_row.prompt
    assert "-0.0" not in centroid_row.prompt
    assert height_query.clauses[0].value == 5.0
    assert height_row.gold_answer == "feature:b"
    assert "overall height of 5.0" in height_row.prompt


def test_smoke_queries_mine_equal_feature_axis_coordinate_values() -> None:
    graph = OntologyGraph(
        graph_id="graph:equal_axis",
        source={"source_id": "src_equal_axis", "source_code": "import cadquery as cq\n"},
    )
    for node_id, volume, centroid_x, centroid_y in [
        ("feature:a", 10.0, 7.0, -2.0),
        ("feature:b", 30.0, 7.0, -2.0),
        ("feature:c", 25.0, 1.0, 9.0),
    ]:
        graph.add_node(Node(node_id, "feature", node_id))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid_x", centroid_x))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid_y", centroid_y))

    queries = {query.query_id.rsplit(":", 1)[-1]: query for query in smoke_queries(graph)}
    centroid_x_row = materialize_row(graph, resolve_query(graph, queries["largest_equal_centroid_x_feature"]))
    centroid_y_row = materialize_row(graph, resolve_query(graph, queries["largest_equal_centroid_y_feature"]))

    assert centroid_x_row.gold_answer == "feature:b"
    assert "solid centroid X coordinate of 7.0" in centroid_x_row.prompt
    assert "greatest volume" in centroid_x_row.prompt
    assert centroid_y_row.gold_answer == "feature:b"
    assert "solid centroid Y coordinate of -2.0" in centroid_y_row.prompt
    assert "greatest volume" in centroid_y_row.prompt


def test_smoke_queries_mine_equal_face_and_endpoint_coordinate_values() -> None:
    graph = OntologyGraph(
        graph_id="graph:equal_coordinates",
        source={"source_id": "src_equal_coordinates", "source_code": "import cadquery as cq\n"},
    )
    graph.add_node(Node("selector:faces", "selector", "selected faces"))
    for node_id, coordinate_z, distance_to_origin in [
        ("face:a", 5.0, 10.0),
        ("face:b", 5.0, 2.0),
        ("face:c", 9.0, 1.0),
    ]:
        graph.add_node(Node(node_id, "face", node_id))
        graph.add_relation(Relation(node_id, "selector:faces", "has_kernel_stable_face_id"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "coordinate_z", coordinate_z))
        graph.add_measurement(Measurement(node_id, "relation_metric", "distance_to_origin", distance_to_origin))

    graph.add_node(Node("selector:edges", "selector", "selected edges"))
    for node_id in ["edge:a", "edge:b", "edge:c"]:
        graph.add_node(Node(node_id, "edge", node_id))
        graph.add_relation(Relation(node_id, "selector:edges", "has_kernel_stable_edge_id"))
    for node_id, edge_id, coordinate_z, distance_to_origin in [
        ("endpoint:a", "edge:a", 3.0, 2.0),
        ("endpoint:b", "edge:b", 3.0, 6.0),
        ("endpoint:c", "edge:c", 8.0, 20.0),
    ]:
        graph.add_node(Node(node_id, "edge_endpoint", node_id))
        graph.add_relation(Relation(node_id, edge_id, "endpoint_of"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "coordinate_z", coordinate_z))
        graph.add_measurement(Measurement(node_id, "relation_metric", "distance_to_origin", distance_to_origin))

    queries = {query.query_id.rsplit(":", 1)[-1]: query for query in smoke_queries(graph)}
    face_row = materialize_row(graph, resolve_query(graph, queries["nearest_equal_center_z_kernel_selected_face"]))
    endpoint_row = materialize_row(graph, resolve_query(graph, queries["farthest_equal_z_kernel_edge_endpoint"]))

    assert face_row.gold_answer == "face:b"
    assert "face center has a global Z coordinate of 5.0" in face_row.prompt
    assert "smallest distance to the global origin" in face_row.prompt
    assert endpoint_row.gold_answer == "endpoint:b"
    assert "endpoint has a global Z coordinate of 3.0" in endpoint_row.prompt
    assert "greatest distance to the global origin" in endpoint_row.prompt


def test_smoke_queries_mine_equal_region_volume_values() -> None:
    graph = OntologyGraph(
        graph_id="graph:equal_regions",
        source={"source_id": "src_equal_regions", "source_code": "import cadquery as cq\n"},
    )
    for node_id, volume, centroid_z in [
        ("material_region:a", 42.0, 1.0),
        ("material_region:b", 42.0, 7.0),
        ("material_region:c", 9.0, 20.0),
    ]:
        graph.add_node(Node(node_id, "material_region", node_id))
        graph.add_relation(Relation(node_id, node_id, "has_kernel_material_region_geometry"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "volume", volume))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_z", centroid_z))
    for node_id, volume, centroid_z in [
        ("void_region:a", 8.0, 2.0),
        ("void_region:b", 8.0, 6.0),
        ("void_region:c", 3.0, 30.0),
    ]:
        graph.add_node(Node(node_id, "void_region", node_id))
        graph.add_relation(Relation(node_id, node_id, "has_kernel_void_region_geometry"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "volume", volume))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_z", centroid_z))

    queries = {query.query_id.rsplit(":", 1)[-1]: query for query in smoke_queries(graph)}
    material_row = materialize_row(graph, resolve_query(graph, queries["highest_equal_volume_added_region"]))
    void_row = materialize_row(graph, resolve_query(graph, queries["highest_equal_volume_removed_region"]))

    assert material_row.gold_answer == "material_region:b"
    assert "added-material region has a volume of 42.0" in material_row.prompt
    assert "greatest centroid height" in material_row.prompt
    assert void_row.gold_answer == "void_region:b"
    assert "removed-material region has a volume of 8.0" in void_row.prompt
    assert "greatest centroid height" in void_row.prompt


def test_smoke_queries_generate_cross_feature_reference_distance_tasks() -> None:
    graph = OntologyGraph(
        graph_id="graph:cross_value",
        source={"source_id": "src_cross_value", "source_code": "import cadquery as cq\n"},
    )
    for node_id, volume, centroid in [
        ("feature:ref", 100.0, [0.0, 0.0, 0.0]),
        ("feature:z", 50.0, [100.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(node_id, "feature", node_id))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "volume", volume))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid", centroid))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "centroid_z", centroid[2]))
    graph.add_node(Node("selector:edges", "selector", "selected edges"))
    for node_id, midpoint in [
        ("edge:a", [1.0, 0.0, 0.0]),
        ("edge:b", [5.0, 0.0, 0.0]),
    ]:
        graph.add_node(Node(node_id, "edge", node_id))
        graph.add_relation(Relation(node_id, "selector:edges", "has_kernel_stable_edge_id"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "bbox_max_z", 0.0))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "edge_length", 10.0))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "midpoint", midpoint))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "midpoint_y", midpoint[1]))

    queries = {query.query_id.rsplit(":", 1)[-1]: query for query in smoke_queries(graph)}
    query = queries["nearest_equal_length_edge_to_reference_feature_centroid"]
    row = materialize_row(graph, resolve_query(graph, query))

    assert row.gold_answer == "edge:a"
    assert "The target edge has a length of 10.0." in row.prompt
    assert "solid volume 100.0 and centroid height 0.0" in row.prompt
    assert "closest to the reference feature's solid centroid" in row.prompt
    assert row.logical_hop_count == 5


def test_generated_smoke_query_clauses_are_yaml_backed() -> None:
    for source_id, source_code in {
        "src_fixture": SOURCE,
        "src_loop": LOOP_SOURCE,
    }.items():
        graph = build_graph(source_record_from_mapping({"source_id": source_id, "normalized_code": source_code}))
        for query in smoke_queries(graph):
            render_prompt(graph.source["source_code"], query)


def test_resolver_does_not_inline_generated_prompt_text() -> None:
    tree = ast.parse(Path("cad_qa/query/resolver.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "Clause":
            continue
        assert all(keyword.arg != "text" for keyword in node.keywords)


def test_metric_filter_clause() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    query = QueryProgram(
        query_id="q_area_filter",
        target_type="profile",
        clauses=[
            Clause(
                id="large_area",
                kind="metric_compare",
                metric="area",
                operator=">",
                value=12.5,
                text="The target profile has area greater than 12.5.",
            )
        ],
    )
    resolution = resolve_query(graph, query)
    assert resolution.verifier_status == "resolved"
    assert resolution.gold_answer == "profile:wp2"


def test_loop_unrolling_extracts_selectors_faces_sketches_and_void_regions() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_loop", "normalized_code": LOOP_SOURCE}))
    selectors = graph.nodes_by_type("selector")
    faces = graph.nodes_by_type("face")
    sketches = graph.nodes_by_type("sketch")
    void_regions = graph.nodes_by_type("void_region")
    assert len(selectors) >= 4
    assert any(node.properties["stable_selector"] == ">Y" for node in faces)
    assert sketches
    assert void_regions
    assert any(relation.type == "same_selected_face_as" for relation in graph.relations)
    assert any(relation.type == "has_sketch_center" for relation in graph.relations)
    assert any(relation.type == "has_void_region_geometry" for relation in graph.relations)
    assert graph.diagnostics and all(item["kind"] == "loop_unrolled" for item in graph.diagnostics)


def test_material_region_projection_and_path_metrics() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    material_region = graph.nodes_by_type("material_region")[0]
    assert graph.measurements_for(material_region.id, "bbox")
    assert graph.measurements_for(material_region.id, "height")
    assert graph.measurements_for(material_region.id, "start_centroid")
    assert graph.measurements_for(material_region.id, "end_centroid")
    assert graph.measurements_for("path:wp7", "initial_tangent") == []
    path_source = """
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.splineApprox([(0, 0, 0), (1, 2, 3), (3, 2, 1)], makeWire=1)
"""
    path_graph = build_graph(source_record_from_mapping({"source_id": "src_path", "normalized_code": path_source}))
    assert path_graph.nodes_by_type("path")
    assert path_graph.nodes_by_type("path_point")
    assert path_graph.nodes_by_type("path_segment")
    assert path_graph.measurements_for("path:wp2", "initial_tangent")[0].value == [1.0, 2.0, 3.0]
    assert path_graph.measurements_for("path:wp2", "nearest_point_to_origin")
    assert path_graph.measurements_for("path:wp2", "nearest_point_distance_to_origin")
    assert path_graph.measurements_for("path:wp2:point:1", "coordinate_z")[0].value == 3.0
    assert path_graph.measurements_for("path:wp2:point:1", "distance_to_origin")[0].value == math.sqrt(14.0)
    assert path_graph.measurements_for("path:wp2:segment:0", "segment_length")[0].value == math.sqrt(14.0)
    assert any(relation.type == "nearest_point_on_path" for relation in path_graph.relations)
    assert any(relation.type == "point_on_path" for relation in path_graph.relations)
    assert any(relation.type == "segment_on_path" for relation in path_graph.relations)


def test_high_hop_clue_breadth_gate_rejects_narrow_clue() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    query = QueryProgram(
        query_id="q_narrow_high_hop",
        target_type="profile",
        clauses=[
            Clause(
                id="large_area",
                kind="metric_compare",
                metric="area",
                operator=">",
                value=12.5,
                text="The target profile has area greater than 12.5.",
            )
        ],
        hop_count=3,
        difficulty="cad_browsecomp",
    )
    resolution = resolve_query(graph, query)
    assert resolution.verifier_status == "failed"
    assert resolution.candidate_trace.failure_reason == "clue_too_narrow"


def test_materialized_rows_audit_clue_traceability_and_breadth() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    resolution = next(
        resolution
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved" and resolution.query_program.hop_count >= 3
    )
    row = to_jsonable(materialize_row(graph, resolution))
    assert validate_rows([row])["valid"]
    assert any("candidate_count_after" in clue for clue in row["clue_map"] if clue["clause_id"] != "aggregation")

    narrow = {**row, "candidate_trace": {**row["candidate_trace"], "steps": [dict(step) for step in row["candidate_trace"]["steps"]]}}
    clause_id = row["query_program"]["clauses"][0]["id"]
    for step in narrow["candidate_trace"]["steps"]:
        if step.get("step") == clause_id:
            step["after"] = [step["after"][0]]
            break
    report = validate_rows([narrow])
    assert not report["valid"]
    assert any(error["error"] == "clue_too_narrow" for error in report["errors"])

    unmapped = {**row, "clue_map": row["clue_map"][1:]}
    traceability = validate_rows([unmapped])
    assert not traceability["valid"]
    assert any(error["error"] == "missing_clue_clause_map" for error in traceability["errors"])


def test_path_and_repeated_selector_queries_use_cad_relations() -> None:
    path_source = """
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.splineApprox([(3, 0, 0), (2, 0, 0)], makeWire=1)
wp3 = wp1.splineApprox([(1, 0, 0), (4, 0, 0)], makeWire=1)
"""
    path_graph = build_graph(source_record_from_mapping({"source_id": "src_path_queries", "normalized_code": path_source}))
    path_resolution = next(
        resolve_query(path_graph, query)
        for query in smoke_queries(path_graph)
        if query.query_id.endswith("q2:path_nearest_origin")
    )
    assert path_resolution.verifier_status == "resolved"
    assert path_resolution.gold_answer == "path:wp3"
    assert "has_path_tangent" in path_resolution.relation_families
    path_resolutions = {
        query.query_id.split(":")[-1]: resolve_query(path_graph, query)
        for query in smoke_queries(path_graph)
    }
    assert path_resolutions["nearest_path_point_to_origin"].gold_answer == "path:wp3:point:0"
    assert path_resolutions["longest_path_segment"].gold_answer == "path:wp3:segment:0"
    for key in ["nearest_path_point_to_origin", "longest_path_segment"]:
        row = materialize_row(path_graph, path_resolutions[key])
        assert row.release_ready
        assert row.geometry_hop_count > 0
        assert "relation_metric" in row.measurement_scopes

    selector_graph = build_graph(source_record_from_mapping({"source_id": "src_loop_queries", "normalized_code": LOOP_SOURCE}))
    selector_resolution = next(
        resolve_query(selector_graph, query)
        for query in smoke_queries(selector_graph)
        if query.query_id.endswith("q3:latest_repeated_selector")
    )
    assert selector_resolution.verifier_status == "resolved"
    assert "same_selected_face_as" in selector_resolution.relation_families


def test_split_report_baseline_and_sft_exports() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        materialize_row(graph, resolution)
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    row_dicts = [to_jsonable(row) for row in rows]
    splits = assign_splits(rows)
    manifest = split_manifest(rows)
    report = dataset_report(rows)
    baselines = run_baselines(row_dicts)
    assert sum(len(items) for items in splits.values()) == len(rows)
    assert manifest["source_count"] == 1
    assert report["row_count"] == len(rows)
    assert report["prompt_families"]
    assert report["prompt_template_ids"]
    assert report["quality_flags"]["syntax_only_calibration"] >= 1
    assert baselines["oracle"]["accuracy"] == 1.0
    assert baselines["first_candidate"]["by_hop"]
    assert baselines["first_static_filter"]["by_static_hop"]
    assert "majority" in baselines
    assert len(answer_sft_rows(row_dicts)) == len(rows)
    assert all(row["geometry_hop_count"] > 0 for row in default_training_rows(row_dicts))
    assert "answer:" in reasoning_sft_rows(row_dicts)[0]["messages"][1]["content"]
    assert leakage_audit(row_dicts, manifest)["valid"]
    assert ablation_sft_groups(row_dicts)
    assert scaling_sft_groups(row_dicts, [1, 100])["size_1"]


def test_release_balance_report_checks_family_entropy_and_geometry_hops() -> None:
    rows = [
        {
            "row_id": f"row:src:{index}:family_{index % 10}",
            "source_id": "src",
            "prompt": f"geometry prompt {index}",
            "prompt_template_id": f"template_{index % 10}",
            "gold_answer": f"entity:{index}",
            "geometry_hop_count": 2,
            "static_hop_count": index % 3,
            "query_program": {
                "query_id": f"graph:src:q{index}:family_{index % 10}",
                "aggregation_metric": "volume",
            },
        }
        for index in range(100)
    ]
    report = release_balance_report(rows)
    assert report["applicable"]
    assert report["passes_prompt_family_balance"]
    assert report["passes_prompt_template_balance"]
    assert report["passes_answer_entropy"]
    assert report["passes_geometry_hop_coverage"]
    assert report["passes_syntax_only_calibration_cap"]
    assert not report["passes_value_bearing_measurement_coverage"]
    assert not report["passes_cross_feature_value_bearing_coverage"]
    assert report["prompt_family_count"] == 10
    assert report["prompt_template_count"] == 10
    assert report["unique_answer_count"] == 100
    assert report["geometry_critical_count"] == 100
    assert report["syntax_only_calibration_count"] == 0
    assert report["minimum_prompt_family_share"] == 0.01
    assert report["maximum_prompt_family_share"] == 0.10
    assert report["underrepresented_prompt_families"] == []
    assert report["overrepresented_prompt_families"] == []

    skewed_rows = [
        {
            "row_id": f"row:src:{index}:same_family",
            "gold_answer": "same-answer",
            "geometry_hop_count": 0,
            "static_hop_count": 1,
            "query_program": {"query_id": f"graph:src:q{index}:same_family"},
        }
        for index in range(20)
    ]
    skewed_report = release_balance_report(skewed_rows)
    assert skewed_report["applicable"]
    assert not skewed_report["passes_prompt_family_balance"]
    assert not skewed_report["passes_prompt_template_balance"]
    assert not skewed_report["passes_answer_entropy"]
    assert not skewed_report["passes_geometry_hop_coverage"]
    assert not skewed_report["passes_syntax_only_calibration_cap"]

    sparse_rows = [
        {
            "row_id": f"row:src:{index}:family",
            "prompt_template_id": f"template_{index % 10}",
            "gold_answer": f"entity:{index}",
            "geometry_hop_count": 2,
            "static_hop_count": 1,
            "query_program": {
                "query_id": f"graph:src:q{index}:{'dominant' if index < 191 else f'rare_{index}'}",
                "aggregation_metric": "volume",
            },
        }
        for index in range(200)
    ]
    sparse_report = release_balance_report(sparse_rows)
    assert not sparse_report["passes_prompt_family_balance"]
    assert sparse_report["overrepresented_prompt_families"] == [
        {"prompt_family": "dominant", "count": 191, "share": 0.955}
    ]
    assert len(sparse_report["underrepresented_prompt_families"]) == 9

    value_rows = []
    for index, row in enumerate(rows):
        query = dict(row["query_program"])
        clauses = [{"kind": "has_measurement", "metric": "volume", "value": float(index)}]
        if index == 0:
            clauses.append({"kind": "reference_measurement", "metric": "distance_to_reference_feature_centroid"})
            query["aggregation_metric"] = "distance_to_reference_feature_centroid"
        query["clauses"] = clauses
        value_rows.append({**row, "query_program": query})
    value_report = release_balance_report(value_rows)
    assert value_report["passes_value_bearing_measurement_coverage"]
    assert value_report["passes_cross_feature_value_bearing_coverage"]
    assert value_report["cross_feature_value_bearing_count"] == 1


def test_benchmark_release_tier_applies_stricter_numeric_gates() -> None:
    rows = [
        {
            "row_id": f"row:src:{index}:family_{index % 10}",
            "source_id": f"src_{index}",
            "prompt": f"geometry prompt {index}",
            "prompt_template_id": f"template_{index % 10}",
            "gold_answer": f"entity:{index}",
            "logical_hop_count": 3,
            "geometry_hop_count": 2,
            "static_hop_count": 0,
            "query_program": {
                "query_id": f"graph:src:q{index}:family_{index % 10}",
                "aggregation_metric": "volume",
                "clauses": [{"kind": "has_measurement", "metric": "volume", "value": float(index)}],
            },
            "candidate_trace": {
                "steps": [
                    {"step": "initial", "candidate_ids": [f"entity:{i}" for i in range(8)]},
                    {
                        "step": "aggregation",
                        "before": [f"entity:{i}" for i in range(4)],
                        "after": [f"entity:{index}"],
                    },
                ],
                "final_candidates": [f"entity:{index}"],
            },
        }
        for index in range(100)
    ]

    release_candidate = release_balance_report(rows)
    assert release_candidate["release_tier"] == "release-candidate"
    assert release_candidate["passes_prompt_template_balance"]
    assert release_candidate["passes_answer_entropy"]
    assert release_candidate["passes_geometry_hop_coverage"]

    benchmark = release_balance_report(rows, release_tier="benchmark-release")
    assert benchmark["release_tier"] == "benchmark-release"
    assert benchmark["maximum_prompt_template_share"] == 0.05
    assert benchmark["minimum_unique_answer_count"] == 1000
    assert benchmark["minimum_answer_entropy_bits"] == 8.0
    assert benchmark["minimum_geometry_hop_positive_share"] == 0.95
    assert benchmark["minimum_logical_hop_ge_3_share"] == 0.90
    assert benchmark["minimum_value_bearing_measurement_share"] == 0.15
    assert benchmark["maximum_value_bearing_measurement_share"] == 0.30
    assert benchmark["minimum_cross_feature_value_bearing_share"] == 0.05
    assert benchmark["minimum_required_pre_final_candidate_count"] == 2
    assert benchmark["minimum_required_median_pre_final_candidate_count"] == 4.0
    assert not benchmark["passes_prompt_template_balance"]
    assert not benchmark["passes_answer_entropy"]
    assert benchmark["passes_geometry_hop_coverage"]
    assert benchmark["passes_main_browsecomp_hop_coverage"]
    assert not benchmark["passes_value_bearing_measurement_coverage"]
    assert not benchmark["passes_cross_feature_value_bearing_coverage"]
    assert benchmark["passes_candidate_breadth"]


def test_release_verifier_blocks_non_calibration_low_geometry_critical_families() -> None:
    rows = [
        {
            "row_id": f"row:src:{index}:family_{index % 4}",
            "source_id": "src",
            "prompt": f"geometry prompt {index}",
            "gold_answer": f"entity:{index}",
            "logical_hop_count": 2,
            "geometry_hop_count": 2,
            "static_hop_count": index % 2,
            "difficulty_bucket": "bridge",
            "verifier_status": "resolved",
            "answer_format": "entity_id",
            "relation_families": [],
            "measurement_scopes": ["snapshot_state"],
            "query_program": {
                "query_id": f"graph:src:q{index}:family_{index % 4}",
                "aggregation_metric": "volume",
            },
        }
        for index in range(20)
    ]
    rows.append(
        {
            "row_id": "row:src:weak:highest_workplane",
            "source_id": "src",
            "prompt": "noncritical geometry prompt",
            "gold_answer": "workplane:wp9",
            "logical_hop_count": 2,
            "geometry_hop_count": 1,
            "static_hop_count": 0,
            "difficulty_bucket": "bridge",
            "verifier_status": "resolved",
            "answer_format": "entity_id",
            "relation_families": [],
            "measurement_scopes": ["entity_geometry"],
            "query_program": {"query_id": "graph:src:qweak:highest_workplane"},
        }
    )

    report = release_verifier_report(rows)
    assert not report["stop_gates"]["geometry_critical_prompt_family_coverage"]
    assert "geometry_critical_prompt_family_coverage" in report["blocking_gates"]
    assert "highest_workplane" in report["shortcut_resistance"]["low_geometry_critical_families"]

    rows[-1] = {
        "row_id": "row:src:calibration:first_operation",
        "source_id": "src",
        "prompt": "calibration prompt",
        "gold_answer": "operation:wp1",
        "logical_hop_count": 0,
        "geometry_hop_count": 0,
        "static_hop_count": 1,
        "difficulty_bucket": "low",
        "verifier_status": "resolved",
        "answer_format": "entity_id",
        "relation_families": [],
        "measurement_scopes": [],
        "query_program": {"query_id": "graph:src:qcal:first_operation"},
    }
    calibration_report = release_verifier_report(rows)
    assert calibration_report["stop_gates"]["geometry_critical_prompt_family_coverage"]
    assert "first_operation" in calibration_report["shortcut_resistance"]["syntax_only_families"]


def test_shortcut_resistance_report_breaks_down_prompt_family_risk(tmp_path: Path) -> None:
    rows = [
        {
            "row_id": "row:src:syntax:first_operation",
            "gold_answer": "operation:wp1",
            "static_hop_count": 1,
            "geometry_hop_count": 0,
            "query_program": {"query_id": "graph:src:q0:first_operation"},
        },
        {
            "row_id": "row:src:geometry:largest_compiled_volume_feature",
            "gold_answer": "feature:cut",
            "static_hop_count": 1,
            "geometry_hop_count": 2,
            "release_ready": True,
            "query_program": {
                "query_id": "graph:src:q1:largest_compiled_volume_feature",
                "aggregation_metric": "volume",
            },
        },
        {
            "row_id": "row:src:geometry:largest_compiled_volume_feature",
            "gold_answer": "feature:boss",
            "static_hop_count": 2,
            "geometry_hop_count": 3,
            "release_ready": True,
            "query_program": {
                "query_id": "graph:src:q2:largest_compiled_volume_feature",
                "aggregation_metric": "volume",
            },
        },
        {
            "row_id": "row:src:mixed:profile_on_workplane",
            "gold_answer": "profile:p1",
            "static_hop_count": 2,
            "geometry_hop_count": 0,
            "query_program": {"query_id": "graph:src:q3:profile_on_workplane"},
        },
        {
            "row_id": "row:src:mixed:profile_on_workplane",
            "gold_answer": "profile:p2",
            "static_hop_count": 2,
            "geometry_hop_count": 1,
            "query_program": {"query_id": "graph:src:q4:profile_on_workplane"},
        },
    ]

    report = shortcut_resistance_report(rows)
    assert report["row_count"] == 5
    assert report["prompt_family_count"] == 3
    assert report["geometry_hop_counts"] == {"0": 2, "1": 1, "2": 1, "3": 1}
    assert report["geometry_hop_positive_count"] == 3
    assert report["geometry_critical_count"] == 2
    assert report["syntax_only_calibration_count"] == 2
    assert report["zero_geometry_hop_families"] == ["first_operation"]
    assert report["syntax_only_families"] == ["first_operation"]
    assert set(report["low_geometry_coverage_families"]) == {"first_operation", "profile_on_workplane"}
    assert set(report["low_geometry_critical_families"]) == {"first_operation", "profile_on_workplane"}

    volume_family = report["by_prompt_family"]["largest_compiled_volume_feature"]
    assert volume_family["geometry_hop_positive_share"] == 1.0
    assert volume_family["geometry_critical_share"] == 1.0
    assert volume_family["unique_answer_count"] == 2

    markdown = shortcut_resistance_markdown(report)
    assert "Shortcut Resistance Report" in markdown
    assert "Weakest Geometry-Hop Families" in markdown
    assert "Weakest Geometry-Critical Families" in markdown

    dataset_dir = tmp_path / "dataset"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    assert cli_main(["dataset", "shortcut-report", str(dataset_dir)]) == 0
    assert (dataset_dir / "shortcut_resistance_report.json").exists()
    assert (dataset_dir / "SHORTCUT_RESISTANCE_REPORT.md").exists()


def test_training_export_cli_defaults_to_geometry_critical_rows(tmp_path: Path) -> None:
    rows = [
        {
            "row_id": "row:syntax:first_operation",
            "prompt": "syntax prompt",
            "gold_answer": "operation:wp1",
            "logical_hop_count": 0,
            "geometry_hop_count": 0,
            "difficulty_bucket": "low",
            "measurement_scopes": [],
            "relation_families": [],
            "query_program": {"query_id": "graph:src:q0:first_operation"},
        },
        {
            "row_id": "row:geometry:largest_compiled_volume_feature",
            "prompt": "geometry prompt",
            "gold_answer": "feature:result",
            "logical_hop_count": 2,
            "geometry_hop_count": 2,
            "difficulty_bucket": "bridge",
            "measurement_scopes": ["snapshot_state"],
            "relation_families": [],
            "query_program": {
                "query_id": "graph:src:q2:largest_compiled_volume_feature",
                "aggregation_metric": "volume",
                "clauses": [{"metric": "bbox_span_z"}],
            },
        },
        {
            "row_id": "row:noncritical:profile_on_workplane",
            "prompt": "profile prompt",
            "gold_answer": "profile:wp2",
            "logical_hop_count": 2,
            "geometry_hop_count": 2,
            "difficulty_bucket": "bridge",
            "measurement_scopes": ["entity_geometry"],
            "relation_families": ["located_on"],
            "query_program": {"query_id": "graph:src:q2:profile_on_workplane"},
        },
        {
            "row_id": "row:quarantine:largest_removed_region",
            "prompt": "quarantined geometry prompt",
            "gold_answer": "void_region:wp1",
            "logical_hop_count": 3,
            "geometry_hop_count": 3,
            "difficulty_bucket": "cad_browsecomp",
            "measurement_scopes": ["snapshot_state"],
            "relation_families": ["has_void_region_geometry"],
            "release_ready": False,
            "quarantine_reasons": ["conservative_region_projection"],
            "query_program": {"query_id": "graph:src:q3:largest_removed_region"},
        },
    ]
    rows_path = tmp_path / "rows.jsonl"
    default_out = tmp_path / "sft_default"
    calibration_out = tmp_path / "sft_calibration"
    benchmark_out = tmp_path / "sft_benchmark"
    write_jsonl(rows_path, rows)

    assert cli_main(["training", "export-sft", "--rows", str(rows_path), "--out", str(default_out)]) == 0
    default_report = read_jsonl(default_out / "answer_sft.jsonl")
    default_sft_report = json.loads((default_out / "sft_report.json").read_text())
    assert len(default_report) == 1
    assert default_report[0]["messages"][1]["content"] == "feature:result"
    assert default_sft_report["input_rows"] == 4
    assert default_sft_report["training_rows"] == 1
    assert default_sft_report["excluded_calibration_or_noncritical_rows"] == 3
    assert default_sft_report["excluded_calibration_noncritical_or_quarantined_rows"] == 3
    assert default_sft_report["training_readiness"]["passes_geometry_critical_dominance"]
    assert default_sft_report["training_readiness"]["geometry_critical_training_rows"] == 1
    assert default_sft_report["training_readiness"]["syntax_only_training_rows"] == 0
    assert default_sft_report["training_balance"]["row_count"] == 1
    assert default_sft_report["training_balance"]["syntax_only_calibration_count"] == 0
    assert default_sft_report["training_stop_gates"]["geometry_critical_dominance"]
    assert "prompt_family_balance" in default_sft_report["training_stop_gates"]
    assert "input_balance" in default_sft_report
    assert default_sft_report["valid_for_training"]
    assert default_sft_report["blocking_training_gates"] == []
    assert default_sft_report["enforced_training_gates"]

    assert cli_main(
        [
            "training",
            "export-sft",
            "--rows",
            str(rows_path),
            "--out",
            str(benchmark_out),
            "--release-tier",
            "benchmark-release",
            "--allow-failing-training-gates",
        ]
    ) == 0
    benchmark_sft_report = json.loads((benchmark_out / "sft_report.json").read_text())
    assert benchmark_sft_report["release_tier"] == "benchmark-release"
    assert not benchmark_sft_report["valid_for_training"]
    assert "default_sft_row_count" in benchmark_sft_report["blocking_training_gates"]
    assert benchmark_sft_report["training_balance"]["release_gate_profile"]["min_default_sft_rows"] == 10000

    assert cli_main(
        [
            "training",
            "export-sft",
            "--rows",
            str(rows_path),
            "--out",
            str(calibration_out),
            "--include-calibration",
        ]
    ) == 0
    calibration_sft_report = json.loads((calibration_out / "sft_report.json").read_text())
    assert calibration_sft_report["training_rows"] == 4
    assert calibration_sft_report["include_calibration"] is True
    assert not calibration_sft_report["training_readiness"]["passes_geometry_critical_dominance"]
    assert calibration_sft_report["training_readiness"]["syntax_only_training_rows"] == 1
    assert calibration_sft_report["training_balance"]["syntax_only_calibration_count"] == 1
    assert not calibration_sft_report["training_stop_gates"]["geometry_critical_dominance"]
    assert not calibration_sft_report["valid_for_training"]
    assert "geometry_critical_dominance" in calibration_sft_report["blocking_training_gates"]
    assert not calibration_sft_report["enforced_training_gates"]


def test_training_export_cli_blocks_failed_applicable_training_gates(tmp_path: Path) -> None:
    rows = [
        {
            "row_id": f"row:src:{index}:same_family",
            "prompt": f"geometry prompt {index}",
            "gold_answer": "same-answer",
            "logical_hop_count": 2,
            "geometry_hop_count": 2,
            "difficulty_bucket": "cad_browsecomp",
            "measurement_scopes": ["snapshot_state"],
            "relation_families": [],
            "query_program": {
                "query_id": f"graph:src:q{index}:same_family",
                "aggregation_metric": "volume",
            },
        }
        for index in range(20)
    ]
    rows_path = tmp_path / "rows.jsonl"
    write_jsonl(rows_path, rows)

    blocked_out = tmp_path / "sft_blocked"
    assert cli_main(["training", "export-sft", "--rows", str(rows_path), "--out", str(blocked_out)]) == 1
    blocked_report = json.loads((blocked_out / "sft_report.json").read_text())
    assert not blocked_report["valid_for_training"]
    assert set(blocked_report["blocking_training_gates"]) >= {
        "prompt_family_balance",
        "prompt_template_balance",
        "answer_entropy",
    }

    allowed_out = tmp_path / "sft_allowed"
    assert cli_main(
        [
            "training",
            "export-sft",
            "--rows",
            str(rows_path),
            "--out",
            str(allowed_out),
            "--allow-failing-training-gates",
        ]
    ) == 0
    allowed_report = json.loads((allowed_out / "sft_report.json").read_text())
    assert not allowed_report["valid_for_training"]


def test_group_safe_splits_use_source_family_metadata() -> None:
    rows = [
        {"row_id": "row:a1", "source_id": "src_a1", "source_metadata": {"source_family": "family_a"}},
        {"row_id": "row:a2", "source_id": "src_a2", "source_metadata": {"source_family": "family_a"}},
        {"row_id": "row:b", "source_id": "src_b"},
        {"row_id": "row:c", "source_id": "src_c"},
        {"row_id": "row:d", "source_id": "src_d"},
    ]
    splits = assign_splits(rows)
    manifest = split_manifest(rows)
    source_splits = manifest["sources"]
    assert source_splits["src_a1"] == source_splits["src_a2"]
    assert manifest["source_count"] == 5
    assert manifest["group_count"] == 4
    assert sum(len(items) for items in splits.values()) == len(rows)
    assert split_audit(rows, manifest)["valid"]

    stale_rows = [dict(row) for row in rows]
    stale_rows[0]["split"] = "test" if source_splits["src_a1"] != "test" else "validation"
    stale_audit = split_audit(stale_rows, manifest)
    assert not stale_audit["valid"]
    assert stale_audit["errors"][0]["error"] == "row_split_mismatch"


def test_quarantine_policy_marks_non_release_ready_rows() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_loop", "normalized_code": LOOP_SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    report = quarantine_report(rows)
    assert report["quarantine_count"] > 0
    assert "selector_identity_surrogate" in report["reasons"]
    assert "conservative_region_projection" in report["reasons"]
    assert validate_rows(rows)["valid"]
    release_report = validate_rows(rows, release=True)
    assert not release_report["valid"]
    assert any(error.get("error") == "not_release_ready" for error in release_report["errors"])


def test_validation_rejects_banned_prompt_terms() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    resolution = next(
        resolution
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    )
    row = to_jsonable(materialize_row(graph, resolution))
    row["prompt"] += "\nThis mentions ontology."
    report = validate_rows([row])
    assert not report["valid"]
    assert report["errors"][0]["error"] == "banned_prompt_terms"


def test_validation_reports_geometry_first_prompt_policy() -> None:
    base = {
        "source_id": "src_policy",
        "source_code": "import cadquery as cq\n",
        "prompt": "Identify the target.",
        "answer_format": "entity_id",
        "candidate_trace": {"final_candidates": ["entity:1"], "steps": []},
        "relation_families": [],
        "measurement_scopes": [],
        "logical_hop_count": 1,
        "static_hop_count": 0,
        "difficulty_bucket": "bridge",
        "verifier_status": "resolved",
        "evidence_tier": "source_static_or_analytic",
        "release_ready": True,
        "quarantine_reasons": [],
        "clue_map": [{"clause_id": "aggregation"}],
    }
    noncritical = {
        **base,
        "row_id": "row:src_policy:highest_workplane",
        "gold_answer": "workplane:wp2",
        "geometry_hop_count": 1,
        "query_program": {
            "query_id": "graph:src_policy:q1:highest_workplane",
            "target_type": "workplane",
            "clauses": [],
            "aggregation": "argmax",
            "aggregation_metric": "origin_z",
        },
    }
    geometry = {
        **base,
        "row_id": "row:src_policy:largest_compiled_volume_feature",
        "gold_answer": "feature:wp2",
        "geometry_hop_count": 2,
        "query_program": {
            "query_id": "graph:src_policy:q2:largest_compiled_volume_feature",
            "target_type": "feature",
            "clauses": [],
            "aggregation": "argmax",
            "aggregation_metric": "volume",
        },
    }
    literal_geometry = {
        **base,
        "row_id": "row:src_policy:selected_face",
        "gold_answer": "face:selector",
        "geometry_hop_count": 2,
        "relation_families": ["has_kernel_stable_face_id"],
        "query_program": {
            "query_id": "graph:src_policy:q3:selected_face",
            "target_type": "face",
            "clauses": [
                {
                    "id": "stable_selector",
                    "kind": "property_equals",
                    "metric": "stable_selector",
                    "value": ">Z",
                }
            ],
        },
        "clue_map": [{"clause_id": "stable_selector"}],
    }
    calibration = {
        **base,
        "row_id": "row:src_policy:first_operation",
        "gold_answer": "operation:wp1",
        "logical_hop_count": 0,
        "geometry_hop_count": 0,
        "query_program": {
            "query_id": "graph:src_policy:q0:first_operation",
            "target_type": "operation",
            "clauses": [
                {
                    "id": "operation_target",
                    "kind": "property_equals",
                    "metric": "target",
                    "value": "wp1",
                }
            ],
        },
        "clue_map": [{"clause_id": "operation_target"}],
    }

    nonrelease = validate_rows([noncritical, geometry, literal_geometry, calibration])
    assert nonrelease["valid"]
    assert any(
        warning.get("prompt_policy_issue") == "non_geometry_critical_prompt"
        for warning in nonrelease["warnings"]
    )
    assert any(
        warning.get("prompt_policy_issue") == "literal_property_clause"
        for warning in nonrelease["warnings"]
    )
    assert any(
        warning.get("prompt_policy_issue") == "syntax_only_calibration_row"
        for warning in nonrelease["warnings"]
    )

    release = validate_rows([noncritical, geometry, literal_geometry, calibration], release=True)
    assert not release["valid"]
    assert any(
        error.get("error") == "geometry_first_prompt_policy"
        and error.get("prompt_policy_issue") == "non_geometry_critical_prompt"
        for error in release["errors"]
    )
    assert any(
        error.get("error") == "geometry_first_prompt_policy"
        and error.get("prompt_policy_issue") == "literal_property_clause"
        for error in release["errors"]
    )
    assert not any(error.get("row_id") == geometry["row_id"] for error in release["errors"])
    assert not any(
        error.get("prompt_policy_issue") == "syntax_only_calibration_row"
        for error in release["errors"]
    )


def test_prediction_grading_reports_breakdowns() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    responses = [
        {"row_id": rows[0]["row_id"], "answer": rows[0]["gold_answer"]},
        *[
            {"row_id": row["row_id"], "answer": "wrong"}
            for row in rows[1:]
        ],
    ]
    result = grade_responses(rows, responses)
    assert result["correct"] == 1
    assert result["by_hop"]
    assert result["by_difficulty"]
    assert result["by_static_hop"]
    assert result["by_geometry_hop"]
    assert result["by_relation_family"]
    assert result["by_measurement_scope"]
    assert result["invalid_output_rate"] == 0.0
    assert result["missing_response_rate"] == 0.0
    assert result["input_response_count"] == len(rows)
    assert result["extra_response_count"] == 0
    assert result["duplicate_response_count"] == 0

    parse_row = {**rows[0], "answer_format": "integer", "gold_answer": 7}
    calibrated = grade_responses(
        [parse_row, {**parse_row, "row_id": "row:missing"}],
        [
            {"row_id": parse_row["row_id"], "answer": "not-an-int", "confidence": 0.9},
            {"row_id": "row:extra", "answer": "7"},
            {"row_id": "row:extra", "answer": "8"},
        ],
    )
    assert calibrated["invalid_output_count"] == 1
    assert calibrated["invalid_output_rate"] == 1.0
    assert calibrated["missing_response_count"] == 1
    assert calibrated["extra_response_count"] == 2
    assert calibrated["duplicate_response_count"] == 1
    assert calibrated["calibration"]["count"] == 1
    assert calibrated["graded"][0]["confidence"] == 0.9


def test_public_private_grading_uses_private_key_without_public_gold(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    public = public_rows(rows)
    private = private_rows(rows)
    responses = [{"row_id": public[0]["row_id"], "answer": private[0]["gold_answer"]}]
    oracle = oracle_responses(private)
    assert len(oracle) == len(private)
    assert oracle[0] == {"row_id": private[0]["row_id"], "answer": private[0]["gold_answer"]}
    assert public_private_audit(public, private)["valid"]
    result = grade_public_private(public, private, responses)
    assert "gold_answer" not in public[0]
    assert result["correct"] == 1
    assert result["by_hop"]
    assert result["by_relation_family"]
    assert result["by_measurement_scope"]

    missing_key = grade_public_private(public[:1], [], responses)
    assert missing_key["correct"] == 0
    assert missing_key["errors"] == {"missing_private_key": 1}
    assert missing_key["response_count"] == 1
    assert missing_key["missing_response_count"] == 0

    dataset_dir = tmp_path / "dataset"
    response_path = tmp_path / "responses.jsonl"
    out_dir = tmp_path / "graded"
    write_public_private_artifacts(rows, dataset_dir)
    write_jsonl(response_path, responses)
    assert cli_main(
        [
            "evaluation",
            "grade-private",
            "--public",
            str(dataset_dir / "public.jsonl"),
            "--private",
            str(dataset_dir / "private.jsonl"),
            "--responses",
            str(response_path),
            "--out",
            str(out_dir),
        ]
    ) == 0
    assert (out_dir / "prediction_metrics.json").exists()

    oracle_path = tmp_path / "oracle_responses.jsonl"
    assert cli_main(
        [
            "evaluation",
            "export-oracle-responses",
            "--private",
            str(dataset_dir / "private.jsonl"),
            "--out",
            str(oracle_path),
        ]
    ) == 0
    assert oracle_path.exists()


def test_tool_assisted_upper_bound_exports_and_grades_private_artifacts(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    public = public_rows(rows)
    private = private_rows(rows)
    responses = tool_assisted_responses(public, private)
    assert len(responses) == len(public)
    assert responses[0]["tool"] == "private_graph_resolver"
    assert responses[0]["provenance"]["query_id"]
    result = run_tool_assisted_upper_bound(public, private)
    assert result["setting"] == "tool_assisted_upper_bound"
    assert result["coverage"] == 1.0
    assert result["metrics"]["accuracy"] == 1.0
    assert result["metrics"]["invalid_output_rate"] == 0.0

    dataset_dir = tmp_path / "dataset"
    out_dir = tmp_path / "tool"
    write_public_private_artifacts(rows, dataset_dir)
    assert cli_main(
        [
            "evaluation",
            "tool-assisted-upper-bound",
            "--public",
            str(dataset_dir / "public.jsonl"),
            "--private",
            str(dataset_dir / "private.jsonl"),
            "--out",
            str(out_dir),
        ]
    ) == 0
    assert (out_dir / "tool_assisted_responses.jsonl").exists()
    assert (out_dir / "tool_assisted_report.json").exists()


def test_request_exports_do_not_include_gold_answers() -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    zero = zero_shot_requests(rows)
    few = few_shot_requests(rows[:1], rows, shots=2)
    assert zero[0]["row_id"] == rows[0]["row_id"]
    assert "gold_answer" not in zero[0]
    assert len(few[0]["messages"]) == 5
    assert few[0]["metadata"]["shots"] == 2


def test_closed_book_evaluation_audits_requests_and_grades_private_key(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    public = public_rows(rows)
    private = private_rows(rows)
    requests = zero_shot_requests(rows)
    responses = [{"row_id": row["row_id"], "answer": key["gold_answer"]} for row, key in zip(public, private, strict=True)]
    audit = closed_book_request_audit(public, requests)
    assert audit["valid"]
    result = run_closed_book_evaluation(public, private, requests, responses, model_id="fixture-model", setting="zero-shot")
    assert result["valid"]
    assert result["closed_book"]
    assert result["metrics"]["accuracy"] == 1.0
    assert result["response_coverage"] == 1.0

    leaked = [{**requests[0], "gold_answer": private[0]["gold_answer"]}, *requests[1:]]
    leaked_report = run_closed_book_evaluation(public, private, leaked, responses, model_id="fixture-model")
    assert not leaked_report["valid"]
    assert leaked_report["request_audit"]["errors"][0]["error"] == "request_hidden_field_leak"

    dataset_dir = tmp_path / "dataset"
    request_path = tmp_path / "requests.jsonl"
    response_path = tmp_path / "responses.jsonl"
    out_dir = tmp_path / "closed_book"
    write_public_private_artifacts(rows, dataset_dir)
    write_jsonl(request_path, requests)
    write_jsonl(response_path, responses)
    assert cli_main(
        [
            "evaluation",
            "closed-book",
            "--public",
            str(dataset_dir / "public.jsonl"),
            "--private",
            str(dataset_dir / "private.jsonl"),
            "--requests",
            str(request_path),
            "--responses",
            str(response_path),
            "--model-id",
            "fixture-model",
            "--out",
            str(out_dir),
        ]
    ) == 0
    assert (out_dir / "closed_book_report.json").exists()
    assert (out_dir / "prediction_metrics.json").exists()


def test_smoke_experiment_orchestrates_artifacts(tmp_path: Path) -> None:
    sources_path = tmp_path / "sources.jsonl"
    write_jsonl(
        sources_path,
        [
            {"source_id": "src_fixture", "normalized_code": SOURCE},
            {"source_id": "src_loop", "normalized_code": LOOP_SOURCE},
            {"source_id": "src_path", "normalized_code": "import cadquery as cq\nwp1 = cq.Workplane('XY')\nwp2 = wp1.splineApprox([(0,0,0),(1,0,0)], makeWire=1)\n"},
        ],
    )
    report = run_smoke_experiment(sources_jsonl=sources_path, out=tmp_path / "run", limit=3, scaling_sizes=[1, 2])
    assert report["validation"]["valid"]
    assert report["dataset"]["row_count"] > 0
    assert report["release_dataset"]["valid"]
    assert report["release_dataset"]["blocking_release_gates"] == []
    assert report["release_dataset"]["excluded_release_validation_count"] > 0
    assert report["release_dataset"]["excluded_prompt_policy_count"] > 0
    assert report["release_dataset"]["row_count"] < report["dataset"]["row_count"]
    assert report["release_baseline"]["oracle"]["accuracy"] == 1.0
    assert report["requests"]["zero_shot_request_count"] == report["dataset"]["row_count"]
    assert report["release_requests"]["zero_shot_request_count"] == report["release_dataset"]["row_count"]
    assert report["release_sft"]["answer_sft_rows"] == report["release_sft"]["training_rows"]
    assert report["release_sft"]["answer_sft_rows"] <= report["release_dataset"]["row_count"]
    assert report["grade"]["metrics"]["accuracy"] == 1.0
    assert report["release_grade"]["metrics"]["accuracy"] == 1.0
    assert report["tool_assisted"]["metrics"]["accuracy"] == 1.0
    assert report["release_tool_assisted"]["metrics"]["accuracy"] == 1.0
    assert report["public_private"]["public_row_count"] == report["dataset"]["row_count"]
    assert report["release_dataset"]["public_private"]["public_row_count"] == report["release_dataset"]["row_count"]
    summary = experiment_summary(report)
    assert summary["release_validation_valid"]
    assert summary["excluded_release_validation_count"] == report["release_dataset"]["excluded_release_validation_count"]
    assert summary["excluded_prompt_policy_count"] == report["release_dataset"]["excluded_prompt_policy_count"]
    assert (
        summary["excluded_syntax_only_calibration_cap_count"]
        == report["release_dataset"]["excluded_syntax_only_calibration_cap_count"]
    )
    assert summary["release_blocking_gates"] == report["release_dataset"]["blocking_release_gates"]
    assert summary["smoke_release_validation_valid"] is False
    assert "Release rows" in experiment_summary_markdown(summary)
    assert "Prompt-policy rows excluded from release" in experiment_summary_markdown(summary)
    assert "Syntax-only calibration rows excluded by cap" in experiment_summary_markdown(summary)
    assert "Release blocking gates" in experiment_summary_markdown(summary)
    assert "private-key oracle accuracy" in experiment_summary_markdown(summary)
    assert "Tool-assisted upper-bound accuracy" in experiment_summary_markdown(summary)
    paper_results = write_paper_results(tmp_path / "run")
    paper_text = Path(paper_results["paper_results"]).read_text(encoding="utf-8")
    assert "Release Composition" in paper_text
    assert "Prompt-policy rows excluded from release" in paper_text
    assert "Syntax-only calibration rows excluded by cap" in paper_text
    assert "Release blocking gates" in paper_text
    assert (tmp_path / "run" / "experiment_report.json").exists()
    assert (tmp_path / "run" / "run_summary.json").exists()
    assert (tmp_path / "run" / "RUN_SUMMARY.md").exists()
    assert (tmp_path / "run" / "PAPER_RESULTS.md").exists()
    assert (tmp_path / "run" / "artifact_manifest.json").exists()
    assert (tmp_path / "run" / "dataset" / "DATASET_CARD.md").exists()
    assert (tmp_path / "run" / "dataset" / "GENERATED_PREVIEW.md").exists()
    assert (tmp_path / "run" / "dataset" / "public.jsonl").exists()
    assert (tmp_path / "run" / "dataset" / "private.jsonl").exists()
    assert (tmp_path / "run" / "dataset" / "public_private_report.json").exists()
    assert (tmp_path / "run" / "dataset" / "failure_report.json").exists()
    assert (tmp_path / "run" / "dataset" / "quarantine_report.json").exists()
    assert (tmp_path / "run" / "dataset" / "release_validation_report.json").exists()
    assert (tmp_path / "run" / "dataset" / "release_verifier_report.json").exists()
    assert (tmp_path / "run" / "release_dataset" / "rows.jsonl").exists()
    assert (tmp_path / "run" / "release_dataset" / "public.jsonl").exists()
    assert (tmp_path / "run" / "release_dataset" / "private.jsonl").exists()
    assert (tmp_path / "run" / "release_dataset" / "release_validation_report.json").exists()
    assert (tmp_path / "run" / "release_dataset" / "RELEASE_VERIFIER_REPORT.md").exists()
    assert (tmp_path / "run" / "release_baseline" / "baseline_metrics.json").exists()
    assert (tmp_path / "run" / "grade" / "oracle_responses.jsonl").exists()
    assert (tmp_path / "run" / "release_grade" / "prediction_metrics.json").exists()
    assert (tmp_path / "run" / "tool_assisted" / "tool_assisted_report.json").exists()
    assert (tmp_path / "run" / "release_tool_assisted" / "prediction_metrics.json").exists()
    assert (tmp_path / "run" / "requests" / "zero_shot_requests.jsonl").exists()
    assert (tmp_path / "run" / "release_requests" / "zero_shot_requests.jsonl").exists()
    assert (tmp_path / "run" / "sft" / "scaling" / "size_1.jsonl").exists()
    assert (tmp_path / "run" / "release_sft" / "scaling" / "size_1.jsonl").exists()
    assert cli_main(["experiment", "paper-results", "--run", str(tmp_path / "run")]) == 0


def test_dataset_card_failure_report_and_run_package(tmp_path: Path) -> None:
    report = {
        "row_count": 2,
        "hop_counts": {"0": 1, "3": 1},
        "difficulty_buckets": {"cad_browsecomp": 1, "low": 1},
        "split_counts": {"train": 1, "test": 1},
        "relation_families": {"before": 1},
        "measurement_scopes": {"profile.area": 1},
        "answer_formats": {"node_id": 2},
    }
    failures = failure_report(
        [
            {
                "graph_id": "graph:src",
                "query_id": "q",
                "reason": "clue_too_narrow",
                "candidate_trace": {"final_candidates": ["profile:a"]},
            }
        ]
    )
    card = dataset_card_markdown(
        dataset_path=tmp_path / "dataset",
        report=report,
        validation={"valid": True},
        audit={"valid": True},
        failures=failures,
    )
    assert "BrowseComp-style" in card
    assert failures["reasons"] == {"clue_too_narrow": 1}

    run_dir = tmp_path / "run"
    write_jsonl(run_dir / "dataset" / "rows.jsonl", [{"row_id": "row:1"}])
    manifest = run_artifact_manifest(run_dir)
    assert manifest["file_count"] == 1
    package = package_run_artifacts(run_dir, tmp_path / "package.tar.gz")
    assert package["size_bytes"] > 0
    assert (run_dir / "artifact_manifest.json").exists()


def test_dataset_preview_cli_shows_task_and_node_samples(tmp_path: Path) -> None:
    trace_record = {
        "source_id": "src_preview",
        "execution_status": "ok",
        "snapshots": [
            {"target": "wp3", "source_line": 4, "operation_index": 0, "volume": 62.8, "bbox": {"min": [-2, -2, 0], "max": [2, 2, 5]}, "topology": {"faces": 3}},
            {"target": "result", "source_line": 10, "operation_index": 1, "volume": 86.8, "bbox": {"min": [-2, -2, 0], "max": [2, 2, 12]}, "topology": {"faces": 9}},
        ],
        "operation_effects": [
            {
                "from_target": "wp2",
                "to_target": "wp3",
                "source_line": 4,
                "signed_volume_delta": 62.8,
                "bbox_delta": {"min": [-2, -2, 0], "max": [2, 2, 5]},
                "topology_delta": {"faces": 3},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
            {
                "from_target": "wp6",
                "to_target": "result",
                "source_line": 10,
                "signed_volume_delta": 24.0,
                "bbox_delta": {"min": [None, None, 0], "max": [None, None, 12]},
                "topology_delta": {"faces": 1},
                "evidence": "cadquery_assignment_snapshot_delta",
            },
        ],
        "selector_results": [],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(source_record_from_mapping({"source_id": "src_preview", "normalized_code": SOURCE}), trace=trace_record)
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    dataset_dir = tmp_path / "dataset"
    graph_dir = tmp_path / "graph"
    out = tmp_path / "preview.md"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    write_jsonl(graph_dir / "graphs.jsonl", [graph])

    assert cli_main(
        [
            "dataset",
            "preview",
            str(dataset_dir),
            "--graphs",
            str(graph_dir),
            "--out",
            str(out),
            "--family",
            "largest_compiled_volume_feature",
            "--node-type",
            "feature",
            "--node-type",
            "void_region",
            "--sample-per-family",
            "1",
            "--seed",
            "0",
        ]
    ) == 0
    text = out.read_text(encoding="utf-8")
    assert "largest_compiled_volume_feature" in text
    assert "geometry_critical" in text
    assert "Node Samples" in text
    assert "`feature`" in text
    assert "measurement_count" in text
    assert "### `void_region`" in text
    assert "- Nodes: `0`" in text


def test_release_export_cli_filters_quarantined_rows(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_loop", "normalized_code": LOOP_SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    dataset_dir = tmp_path / "dataset"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    blocked_out = tmp_path / "release_blocked"
    assert cli_main(["dataset", "export-release", str(dataset_dir), "--out", str(blocked_out)]) == 1
    assert (blocked_out / "release_verifier_report.json").exists()
    out_dir = tmp_path / "release_review"
    assert cli_main(
        [
            "dataset",
            "export-release",
            str(dataset_dir),
            "--out",
            str(out_dir),
            "--allow-failing-release-gates",
        ]
    ) == 0
    release_report = validate_rows([row for row in rows if row["release_ready"]], release=True)
    assert release_report["valid"]
    assert (out_dir / "rows.jsonl").exists()
    assert (out_dir / "release_validation_report.json").exists()
    verifier_report = json.loads((out_dir / "release_verifier_report.json").read_text())
    assert not verifier_report["valid_for_release"]
    assert "default_sft_geometry_critical_dominance" in verifier_report["blocking_gates"]


def test_release_export_helper_writes_reports(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_loop", "normalized_code": LOOP_SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    duplicate = next(dict(row) for row in rows if row["release_ready"])
    duplicate["row_id"] = duplicate["row_id"] + ":duplicate"
    rows.append(duplicate)
    result = export_release_dataset(rows, out=tmp_path / "release", allow_failing_release_gates=True)
    assert not result["valid"]
    assert "default_sft_geometry_critical_dominance" in result["blocking_release_gates"]
    assert result["excluded_quarantine_count"] > 0
    assert result["excluded_duplicate_prompt_count"] == 1
    assert result["leakage_audit"]["valid"]
    assert result["split_audit"]["valid"]
    assert result["public_private"]["public_row_count"] == result["row_count"]
    assert (tmp_path / "release" / "split_manifest.json").exists()
    assert (tmp_path / "release" / "split_audit.json").exists()
    assert (tmp_path / "release" / "DATASET_CARD.md").exists()
    assert (tmp_path / "release" / "release_exclusions.json").exists()
    assert (tmp_path / "release" / "public.jsonl").exists()
    assert (tmp_path / "release" / "private.jsonl").exists()


def _mark_value_bearing_release_fixture_rows(rows: list[dict]) -> None:
    for index in range(2):
        row = rows[index]
        query = row["query_program"]
        query["clauses"] = [
            {
                "id": "has_compiled_volume_value",
                "kind": "has_measurement",
                "metric": "volume",
                "value": float(index + 1),
            }
        ]
        row["clue_map"] = [
            {"clause_id": "has_compiled_volume_value"},
            {"clause_id": "aggregation"},
        ]
    rows[0]["query_program"]["aggregation_metric"] = "distance_to_reference_feature_centroid"
    rows[0]["query_program"]["clauses"].append(
        {
            "id": "reference_feature_volume_and_centroid",
            "kind": "reference_measurement",
            "metric": "distance_to_reference_feature_centroid",
        }
    )
    rows[0]["clue_map"].insert(1, {"clause_id": "reference_feature_volume_and_centroid"})


def test_release_export_filters_prompt_policy_invalid_rows_before_verifier(tmp_path: Path) -> None:
    rows = []
    for index in range(24):
        rows.append(
            {
                "row_id": f"row:src:{index}:family_{index % 12}",
                "source_id": "src",
                "source_code": "import cadquery as cq\n",
                "prompt": f"geometry prompt {index}",
                "prompt_template_id": f"checklist_constraints_v1:fixture:template_{index % 12}",
                "answer_format": "entity_id",
                "gold_answer": f"feature:{index}",
                "query_program": {
                    "query_id": f"graph:src:q{index}:family_{index % 12}",
                    "target_type": "feature",
                    "aggregation": "argmax",
                    "aggregation_metric": "volume",
                    "clauses": [],
                },
                "candidate_trace": {"final_candidates": [f"feature:{index}"], "steps": []},
                "relation_families": [],
                "measurement_scopes": ["snapshot_state"],
                "logical_hop_count": 2,
                "static_hop_count": 0,
                "geometry_hop_count": 2,
                "difficulty_bucket": "bridge",
                "verifier_status": "resolved",
                "evidence_tier": "source_static_or_analytic",
                "release_ready": True,
                "quarantine_reasons": [],
                "clue_map": [{"clause_id": "aggregation"}],
                "split": "stale",
            }
        )
    rows.append(
        {
            "row_id": "row:src:weak:highest_workplane",
            "source_id": "src",
            "source_code": "import cadquery as cq\n",
            "prompt": "noncritical prompt",
            "answer_format": "entity_id",
            "gold_answer": "workplane:wp9",
            "query_program": {
                "query_id": "graph:src:qweak:highest_workplane",
                "target_type": "workplane",
                "aggregation": "argmax",
                "aggregation_metric": "origin_z",
                "clauses": [],
            },
            "candidate_trace": {"final_candidates": ["workplane:wp9"], "steps": []},
            "relation_families": [],
            "measurement_scopes": ["entity_geometry"],
            "logical_hop_count": 1,
            "static_hop_count": 0,
            "geometry_hop_count": 1,
            "difficulty_bucket": "low",
            "verifier_status": "resolved",
            "evidence_tier": "source_static_or_analytic",
            "release_ready": True,
            "quarantine_reasons": [],
            "clue_map": [{"clause_id": "aggregation"}],
            "split": "stale",
        }
    )
    _mark_value_bearing_release_fixture_rows(rows)

    result = export_release_dataset(rows, out=tmp_path / "release")
    exclusions = json.loads((tmp_path / "release" / "release_exclusions.json").read_text())
    release_rows = read_jsonl(tmp_path / "release" / "rows.jsonl")
    split_quality = json.loads((tmp_path / "release" / "split_audit.json").read_text())
    assert result["valid"]
    assert result["blocking_release_gates"] == []
    assert result["row_count"] == 24
    assert result["excluded_release_validation_count"] == 1
    assert result["excluded_prompt_policy_count"] == 1
    assert len(release_rows) == 24
    assert {row["split"] for row in release_rows} == {"train"}
    assert all(row["prompt_template_id"].startswith("checklist_constraints_v1:") for row in release_rows)
    assert result["split_audit"]["valid"]
    assert split_quality["valid"]
    assert exclusions["release_validation_exclusions"][0]["row_id"] == "row:src:weak:highest_workplane"
    assert exclusions["release_validation_exclusions"][0]["errors"][0]["error"] == "geometry_first_prompt_policy"


def test_release_export_caps_syntax_only_calibration_rows(tmp_path: Path) -> None:
    rows = []
    for index in range(36):
        rows.append(
            {
                "row_id": f"row:src:geometry:{index}:family_{index % 9}",
                "source_id": "src",
                "source_code": "import cadquery as cq\n",
                "prompt": f"geometry prompt {index}",
                "prompt_template_id": f"checklist_constraints_v1:fixture:geometry_template_{index % 9}",
                "answer_format": "entity_id",
                "gold_answer": f"feature:{index}",
                "query_program": {
                    "query_id": f"graph:src:q{index}:family_{index % 9}",
                    "target_type": "feature",
                    "aggregation": "argmax",
                    "aggregation_metric": "volume",
                    "clauses": [],
                },
                "candidate_trace": {"final_candidates": [f"feature:{index}"], "steps": []},
                "relation_families": [],
                "measurement_scopes": ["snapshot_state"],
                "logical_hop_count": 2,
                "static_hop_count": 0,
                "geometry_hop_count": 2,
                "difficulty_bucket": "bridge",
                "verifier_status": "resolved",
                "evidence_tier": "source_static_or_analytic",
                "release_ready": True,
                "quarantine_reasons": [],
                "clue_map": [{"clause_id": "aggregation"}],
            }
        )
    for index in range(10):
        rows.append(
            {
                "row_id": f"row:src:calibration:{index}:first_operation",
                "source_id": "src",
                "source_code": "import cadquery as cq\n",
                "prompt": f"calibration prompt {index}",
                "prompt_template_id": "checklist_constraints_v1:operation:property_target_property_operation:no_aggregation",
                "answer_format": "entity_id",
                "gold_answer": f"operation:wp{index}",
                "query_program": {
                    "query_id": f"graph:src:qcal{index}:first_operation",
                    "target_type": "operation",
                    "clauses": [
                        {
                            "id": "operation_target",
                            "kind": "property_equals",
                            "metric": "target",
                            "value": f"wp{index}",
                        }
                    ],
                },
                "candidate_trace": {"final_candidates": [f"operation:wp{index}"], "steps": []},
                "relation_families": [],
                "measurement_scopes": [],
                "logical_hop_count": 0,
                "static_hop_count": 2,
                "geometry_hop_count": 0,
                "difficulty_bucket": "low",
                "verifier_status": "resolved",
                "evidence_tier": "source_static_or_analytic",
                "release_ready": True,
                "quarantine_reasons": [],
                "clue_map": [{"clause_id": "operation_target"}],
            }
        )
    _mark_value_bearing_release_fixture_rows(rows)

    result = export_release_dataset(rows, out=tmp_path / "release")
    exclusions = json.loads((tmp_path / "release" / "release_exclusions.json").read_text())
    release_rows = read_jsonl(tmp_path / "release" / "rows.jsonl")
    verifier = json.loads((tmp_path / "release" / "release_verifier_report.json").read_text())

    assert result["valid"]
    assert result["excluded_syntax_only_calibration_cap_count"] == 6
    assert exclusions["excluded_syntax_only_calibration_cap_count"] == 6
    assert len(exclusions["syntax_only_calibration_cap_exclusions"]) == 6
    assert len(release_rows) == 40
    assert verifier["stop_gates"]["syntax_only_calibration_cap"]
    assert verifier["release_balance"]["syntax_only_calibration_count"] == 4
    assert verifier["release_balance"]["syntax_only_calibration_share"] == 0.1


def test_release_verifier_report_stop_gates_and_cli(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_loop", "normalized_code": LOOP_SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    failures = [
        {
            "graph_id": "graph:src_loop",
            "query_id": "q_failed",
            "reason": "clue_too_narrow",
            "candidate_trace": {"final_candidates": ["selector:a"]},
        }
    ]
    report = release_verifier_report(rows, failures=failures)
    assert not report["valid_for_release"]
    assert "release_validation" in report["blocking_gates"]
    assert "default_sft_geometry_critical_dominance" in report["stop_gates"]
    assert "group_safe_split_audit" in report["stop_gates"]
    assert "prompt_family_balance" in report["stop_gates"]
    assert "prompt_template_balance" in report["stop_gates"]
    assert "answer_entropy" in report["stop_gates"]
    assert "geometry_hop_coverage" in report["stop_gates"]
    assert "syntax_only_calibration_cap" in report["stop_gates"]
    assert "geometry_critical_prompt_family_coverage" in report["stop_gates"]
    assert "training_readiness" in report
    assert "split_audit" in report
    assert "release_balance" in report
    assert "shortcut_resistance" in report
    assert report["release_balance"]["applicable"] is False
    assert report["quarantine"]["quarantine_count"] > 0
    assert report["failure_report"]["reasons"] == {"clue_too_narrow": 1}
    markdown = release_verifier_markdown(report)
    assert "Release Verifier Report" in markdown
    assert "Release Balance" in markdown
    assert "Shortcut Resistance" in markdown

    dataset_dir = tmp_path / "dataset"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    write_jsonl(dataset_dir / "failure_manifest.jsonl", failures)
    assert cli_main(["dataset", "release-report", str(dataset_dir)]) == 0
    assert (dataset_dir / "release_verifier_report.json").exists()
    assert (dataset_dir / "RELEASE_VERIFIER_REPORT.md").exists()
    assert cli_main(["dataset", "release-report", str(dataset_dir), "--release-tier", "benchmark-release"]) == 0
    benchmark_report = json.loads((dataset_dir / "release_verifier_report.json").read_text())
    assert benchmark_report["release_tier"] == "benchmark-release"
    assert benchmark_report["release_gate_profile"]["min_release_rows"] == 10000
    assert "release_row_count" in benchmark_report["blocking_gates"]
    assert "default_sft_row_count" in benchmark_report["blocking_gates"]
    assert "benchmark_split_group_coverage" in benchmark_report["blocking_gates"]


def test_public_private_exports_do_not_leak_hidden_fields(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    public = public_rows(rows)
    private = private_rows(rows)
    hidden_fields = {"gold_answer", "query_program", "candidate_trace", "clue_map"}
    assert public
    assert hidden_fields.isdisjoint(public[0])
    assert {"prompt", "source_code", "answer_format", "prompt_template_id"} <= set(public[0])
    assert {"gold_answer", "query_program", "candidate_trace"} <= set(private[0])
    assert public_private_audit(public, private)["valid"]
    leak = public_private_audit([{**public[0], "gold_answer": "leak"}], private[:1])
    assert not leak["valid"]
    assert leak["errors"][0]["error"] == "public_hidden_field_leak"
    report = write_public_private_artifacts(rows, tmp_path / "views")
    assert report["public_row_count"] == len(rows)
    assert report["private_row_count"] == len(rows)
    assert report["audit"]["valid"]
    assert (tmp_path / "views" / "public.jsonl").exists()
    assert (tmp_path / "views" / "private.jsonl").exists()


def test_public_private_cli_writes_views(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_fixture", "normalized_code": SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    dataset_dir = tmp_path / "dataset"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    assert cli_main(["dataset", "export-public-private", str(dataset_dir)]) == 0
    assert (dataset_dir / "public.jsonl").exists()
    assert (dataset_dir / "private.jsonl").exists()
