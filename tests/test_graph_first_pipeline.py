from __future__ import annotations

from pathlib import Path

from cad_qa.dataset.materialize import materialize_row
from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.public import private_rows, public_private_audit, public_rows, write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release import export_release_dataset
from cad_qa.dataset.release_report import release_verifier_markdown, release_verifier_report
from cad_qa.dataset.report import dataset_card_markdown, dataset_report, failure_report
from cad_qa.dataset.sft import ablation_sft_groups, answer_sft_rows, reasoning_sft_rows, scaling_sft_groups
from cad_qa.dataset.split import assign_splits, split_manifest
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
from cad_qa.ontology.nodes import graph_from_dict
from cad_qa.ontology.profile_geometry import circle_profile, polyline_profile, rect_profile
from cad_qa.ontology.relations import RELATION_FAMILIES
from cad_qa.ontology.workplane_frames import project_local_point
from cad_qa.prompts.render import render_prompt
from cad_qa.query.ir import Clause, QueryProgram
from cad_qa.query.resolver import resolve_query, smoke_queries
from cad_qa.source import load_sources_jsonl, source_audit, source_family_from_path, source_manifest, source_record_from_mapping
from cad_qa.trace import cadquery_available, trace_report, trace_source, trace_sources_bounded
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


def test_kernel_selector_trace_produces_release_grade_face_identity() -> None:
    source_code = (
        "import cadquery as cq\n"
        "base = cq.Workplane('XY').box(2, 2, 2)\n"
        "sel = base.faces('>Z')\n"
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
                "target": "sel",
                "selector": ">Z",
                "source_line": 3,
                "selector_index": 0,
                "selected_count": 1,
                "shape_types": ["Face"],
                "bbox_signatures": [{"min": [-1, -1, 1], "max": [1, 1, 1]}],
                "evidence": "cadquery_selector_result",
            }
        ],
        "environment": {"cadquery_available": True},
        "failure_reason": None,
    }
    graph = build_graph(
        source_record_from_mapping({"source_id": "src_selector_kernel", "normalized_code": source_code}),
        trace=trace_record,
    )
    kernel_faces = [node for node in graph.nodes_by_type("face") if node.properties.get("kernel_backed")]
    assert len(kernel_faces) == 1
    assert any(relation.type == "has_kernel_stable_face_id" for relation in graph.relations)
    assert graph.measurements_for(kernel_faces[0].id, "bbox")
    selector = graph.nodes_by_type("selector")[0]
    assert graph.measurements_for(selector.id, "selected_count")[0].value == 1

    resolution = next(
        resolve_query(graph, query)
        for query in smoke_queries(graph)
        if query.query_id.endswith("q2:selected_face")
    )
    row = materialize_row(graph, resolution)
    assert resolution.verifier_status == "resolved"
    assert "has_kernel_stable_face_id" in resolution.relation_families
    assert row.release_ready
    assert "selector_identity_surrogate" not in row.quarantine_reasons


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
    for relation in ["before", "after", "input_to", "parameter_of", "uses_profile", "located_on", "adds_material_to", "same_selected_face_as", "has_material_region_geometry"]:
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
    assert row.candidate_trace["final_candidates"]
    report = validate_rows([to_jsonable(row)])
    assert report["valid"]


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
    assert path_graph.measurements_for("path:wp2", "initial_tangent")[0].value == [1.0, 2.0, 3.0]
    assert path_graph.measurements_for("path:wp2", "nearest_point_to_origin")
    assert path_graph.measurements_for("path:wp2", "nearest_point_distance_to_origin")
    assert any(relation.type == "nearest_point_on_path" for relation in path_graph.relations)


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
    assert baselines["oracle"]["accuracy"] == 1.0
    assert baselines["first_candidate"]["by_hop"]
    assert baselines["first_static_filter"]["by_static_hop"]
    assert "majority" in baselines
    assert len(answer_sft_rows(row_dicts)) == len(rows)
    assert "answer:" in reasoning_sft_rows(row_dicts)[0]["messages"][1]["content"]
    assert leakage_audit(row_dicts, manifest)["valid"]
    assert ablation_sft_groups(row_dicts)
    assert scaling_sft_groups(row_dicts, [1, 100])["size_1"]


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
    assert report["release_dataset"]["row_count"] < report["dataset"]["row_count"]
    assert report["release_baseline"]["oracle"]["accuracy"] == 1.0
    assert report["requests"]["zero_shot_request_count"] == report["dataset"]["row_count"]
    assert report["release_requests"]["zero_shot_request_count"] == report["release_dataset"]["row_count"]
    assert report["release_sft"]["answer_sft_rows"] == report["release_dataset"]["row_count"]
    assert report["grade"]["metrics"]["accuracy"] == 1.0
    assert report["release_grade"]["metrics"]["accuracy"] == 1.0
    assert report["tool_assisted"]["metrics"]["accuracy"] == 1.0
    assert report["release_tool_assisted"]["metrics"]["accuracy"] == 1.0
    assert report["public_private"]["public_row_count"] == report["dataset"]["row_count"]
    assert report["release_dataset"]["public_private"]["public_row_count"] == report["release_dataset"]["row_count"]
    summary = experiment_summary(report)
    assert summary["release_validation_valid"]
    assert summary["smoke_release_validation_valid"] is False
    assert "Release rows" in experiment_summary_markdown(summary)
    assert "private-key oracle accuracy" in experiment_summary_markdown(summary)
    assert "Tool-assisted upper-bound accuracy" in experiment_summary_markdown(summary)
    paper_results = write_paper_results(tmp_path / "run")
    assert "Release Composition" in Path(paper_results["paper_results"]).read_text(encoding="utf-8")
    assert (tmp_path / "run" / "experiment_report.json").exists()
    assert (tmp_path / "run" / "run_summary.json").exists()
    assert (tmp_path / "run" / "RUN_SUMMARY.md").exists()
    assert (tmp_path / "run" / "PAPER_RESULTS.md").exists()
    assert (tmp_path / "run" / "artifact_manifest.json").exists()
    assert (tmp_path / "run" / "dataset" / "DATASET_CARD.md").exists()
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


def test_release_export_cli_filters_quarantined_rows(tmp_path: Path) -> None:
    graph = build_graph(source_record_from_mapping({"source_id": "src_loop", "normalized_code": LOOP_SOURCE}))
    rows = [
        to_jsonable(materialize_row(graph, resolution))
        for resolution in (resolve_query(graph, query) for query in smoke_queries(graph))
        if resolution.verifier_status == "resolved"
    ]
    dataset_dir = tmp_path / "dataset"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    out_dir = tmp_path / "release"
    assert cli_main(["dataset", "export-release", str(dataset_dir), "--out", str(out_dir)]) == 0
    release_report = validate_rows([row for row in rows if row["release_ready"]], release=True)
    assert release_report["valid"]
    assert (out_dir / "rows.jsonl").exists()
    assert (out_dir / "release_validation_report.json").exists()


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
    result = export_release_dataset(rows, out=tmp_path / "release")
    assert result["valid"]
    assert result["excluded_quarantine_count"] > 0
    assert result["excluded_duplicate_prompt_count"] == 1
    assert result["leakage_audit"]["valid"]
    assert result["public_private"]["public_row_count"] == result["row_count"]
    assert (tmp_path / "release" / "split_manifest.json").exists()
    assert (tmp_path / "release" / "DATASET_CARD.md").exists()
    assert (tmp_path / "release" / "release_exclusions.json").exists()
    assert (tmp_path / "release" / "public.jsonl").exists()
    assert (tmp_path / "release" / "private.jsonl").exists()


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
    assert report["quarantine"]["quarantine_count"] > 0
    assert report["failure_report"]["reasons"] == {"clue_too_narrow": 1}
    assert "Release Verifier Report" in release_verifier_markdown(report)

    dataset_dir = tmp_path / "dataset"
    write_jsonl(dataset_dir / "rows.jsonl", rows)
    write_jsonl(dataset_dir / "failure_manifest.jsonl", failures)
    assert cli_main(["dataset", "release-report", str(dataset_dir)]) == 0
    assert (dataset_dir / "release_verifier_report.json").exists()
    assert (dataset_dir / "RELEASE_VERIFIER_REPORT.md").exists()


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
    assert {"prompt", "source_code", "answer_format"} <= set(public[0])
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
