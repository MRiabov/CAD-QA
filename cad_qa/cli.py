"""Graph-first CAD-QA command line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.family_test_evidence import DEFAULT_FAMILY_TEST_EVIDENCE, family_test_evidence_gate_report
from cad_qa.dataset.parameter_balance import parameter_balance_report
from cad_qa.dataset.preview import (
    DEFAULT_PREVIEW_EVIDENCE_FILENAME,
    dataset_preview_evidence_report,
    dataset_preview_markdown,
    preview_evidence_gate_report,
)
from cad_qa.dataset.public import write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release import export_release_dataset
from cad_qa.dataset.release_report import (
    DEFAULT_RELEASE_TIER,
    RELEASE_TIERS,
    intended_family_share_feasibility_report,
    release_balance_report,
    release_gate_profile,
    write_release_verifier_report,
)
from cad_qa.dataset.report import (
    dataset_card_markdown,
    dataset_report,
    failure_report,
    shortcut_resistance_markdown,
    shortcut_resistance_report,
)
from cad_qa.dataset.sft import (
    ablation_sft_groups,
    answer_sft_rows,
    default_training_rows,
    reasoning_sft_rows,
    scaling_sft_groups,
    training_readiness_report,
)
from cad_qa.dataset.split import assign_splits, split_audit, split_manifest
from cad_qa.dataset.materialize import materialize_row
from cad_qa.dataset.validate import validate_dataset_dir
from cad_qa.evaluation.baselines import run_baselines
from cad_qa.evaluation.closed_book import run_closed_book_evaluation
from cad_qa.evaluation.grade import grade_public_private, grade_responses
from cad_qa.evaluation.requests import few_shot_requests, oracle_responses, zero_shot_requests
from cad_qa.evaluation.tool_assisted import run_tool_assisted_upper_bound
from cad_qa.experiment import package_run_artifacts, run_smoke_experiment, run_artifact_manifest, write_paper_results
from cad_qa.io import read_jsonl, write_json, write_jsonl
from cad_qa.ontology import build_graph
from cad_qa.ontology.nodes import OntologyGraph, graph_from_dict
from cad_qa.query.family_manifest import (
    DEFAULT_FAMILY_MANIFEST,
    RELEASE_STATUSES,
    intended_family_coverage_report,
    load_family_manifest,
)
from cad_qa.query.ir import query_from_dict
from cad_qa.query.resolver import resolve_query, smoke_queries
from cad_qa.query.synthesis import synthesize_graph_hop_queries
from cad_qa.query.synthesis_selfcheck import write_synthesis_selfcheck
from cad_qa.source import (
    cadevolve_tar_source_rows,
    load_sources_jsonl,
    source_audit,
    source_manifest,
    source_record_from_mapping,
)
from cad_qa.trace import trace_report, trace_sources_bounded


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except Exception as exc:
        print(f"cadqa: error: {exc}", file=sys.stderr)
        return 1
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cadqa")
    subparsers = parser.add_subparsers(required=True)

    sources = subparsers.add_parser("sources")
    sources_sub = sources.add_subparsers(required=True)
    inspect = sources_sub.add_parser("inspect")
    inspect.add_argument("--sources-jsonl", type=Path, required=True)
    inspect.add_argument("--limit", type=int)
    inspect.set_defaults(func=_cmd_sources_inspect)
    source_manifest_cmd = sources_sub.add_parser("manifest")
    source_manifest_cmd.add_argument("--sources-jsonl", type=Path, required=True)
    source_manifest_cmd.add_argument("--limit", type=int)
    source_manifest_cmd.add_argument("--out", type=Path, required=True)
    source_manifest_cmd.set_defaults(func=_cmd_sources_manifest)
    source_audit_cmd = sources_sub.add_parser("audit")
    source_audit_cmd.add_argument("--sources-jsonl", type=Path, required=True)
    source_audit_cmd.add_argument("--limit", type=int)
    source_audit_cmd.add_argument("--out", type=Path, required=True)
    source_audit_cmd.set_defaults(func=_cmd_sources_audit)
    source_from_cadevolve_tar = sources_sub.add_parser("from-cadevolve-tar")
    source_from_cadevolve_tar.add_argument("--tar", type=Path, required=True)
    source_from_cadevolve_tar.add_argument("--out", type=Path, required=True)
    source_from_cadevolve_tar.add_argument("--limit", type=int)
    source_from_cadevolve_tar.add_argument("--path-prefix", action="append", dest="path_prefixes")
    source_from_cadevolve_tar.add_argument("--max-member-bytes", type=int, default=1_000_000)
    source_from_cadevolve_tar.set_defaults(func=_cmd_sources_from_cadevolve_tar)

    graph = subparsers.add_parser("graph")
    graph_sub = graph.add_subparsers(required=True)
    build = graph_sub.add_parser("build")
    build.add_argument("--sources-jsonl", type=Path, required=True)
    build.add_argument("--limit", type=int)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--traces-jsonl", type=Path)
    build.set_defaults(func=_cmd_graph_build)

    trace = subparsers.add_parser("trace")
    trace_sub = trace.add_subparsers(required=True)
    trace_run = trace_sub.add_parser("run")
    trace_run.add_argument("--sources-jsonl", type=Path, required=True)
    trace_run.add_argument("--limit", type=int)
    trace_run.add_argument("--out", type=Path, required=True)
    trace_run.add_argument("--timeout-seconds", type=float, default=10.0)
    trace_run.add_argument("--workers", type=int, default=1)
    trace_run.set_defaults(func=_cmd_trace_run)

    query = subparsers.add_parser("query")
    query_sub = query.add_subparsers(required=True)
    smoke = query_sub.add_parser("smoke")
    smoke.add_argument("--graph", type=Path, required=True)
    smoke.add_argument("--out", type=Path, required=True)
    smoke.set_defaults(func=_cmd_query_smoke)
    synthesize = query_sub.add_parser("synthesize")
    synthesize.add_argument("--graph", type=Path, required=True)
    synthesize.add_argument("--out", type=Path, required=True)
    synthesize.add_argument("--max-per-family", type=int, default=3)
    synthesize.add_argument("--family-manifest", type=Path, default=DEFAULT_FAMILY_MANIFEST)
    synthesize.add_argument(
        "--include-review-only",
        action="store_true",
        help="Include synthesized review-only families instead of only release families.",
    )
    synthesize.set_defaults(func=_cmd_query_synthesize)

    dataset = subparsers.add_parser("dataset")
    dataset_sub = dataset.add_subparsers(required=True)
    materialize = dataset_sub.add_parser("materialize")
    materialize.add_argument("--queries", type=Path, required=True)
    materialize.add_argument("--graphs", type=Path, help="Optional graph directory or graphs.jsonl file for compact query records.")
    materialize.add_argument("--out", type=Path, required=True)
    materialize.set_defaults(func=_cmd_dataset_materialize)
    validate = dataset_sub.add_parser("validate")
    validate.add_argument("path", type=Path)
    validate.add_argument("--release", action="store_true")
    validate.set_defaults(func=_cmd_dataset_validate)
    audit = dataset_sub.add_parser("audit")
    audit.add_argument("path", type=Path)
    audit.set_defaults(func=_cmd_dataset_audit)
    quarantine = dataset_sub.add_parser("quarantine")
    quarantine.add_argument("path", type=Path)
    quarantine.set_defaults(func=_cmd_dataset_quarantine)
    export_release = dataset_sub.add_parser("export-release")
    export_release.add_argument("path", type=Path)
    export_release.add_argument("--out", type=Path, required=True)
    export_release.add_argument("--release-tier", choices=RELEASE_TIERS, default=DEFAULT_RELEASE_TIER)
    export_release.add_argument("--family-manifest", type=Path, default=DEFAULT_FAMILY_MANIFEST)
    export_release.add_argument("--preview-evidence", type=Path)
    export_release.add_argument("--family-test-evidence", type=Path, default=DEFAULT_FAMILY_TEST_EVIDENCE)
    export_release.add_argument(
        "--allow-failing-release-gates",
        action="store_true",
        help="Write release artifacts even when verifier stop gates fail.",
    )
    export_release.set_defaults(func=_cmd_dataset_export_release)
    export_public_private = dataset_sub.add_parser("export-public-private")
    export_public_private.add_argument("path", type=Path)
    export_public_private.set_defaults(func=_cmd_dataset_export_public_private)
    card = dataset_sub.add_parser("card")
    card.add_argument("path", type=Path)
    card.add_argument("--out", type=Path)
    card.set_defaults(func=_cmd_dataset_card)
    release_report = dataset_sub.add_parser("release-report")
    release_report.add_argument("path", type=Path)
    release_report.add_argument("--out", type=Path)
    release_report.add_argument("--release-tier", choices=RELEASE_TIERS, default=DEFAULT_RELEASE_TIER)
    release_report.add_argument("--family-manifest", type=Path, default=DEFAULT_FAMILY_MANIFEST)
    release_report.add_argument("--preview-evidence", type=Path)
    release_report.add_argument("--family-test-evidence", type=Path, default=DEFAULT_FAMILY_TEST_EVIDENCE)
    release_report.set_defaults(func=_cmd_dataset_release_report)
    shortcut_report = dataset_sub.add_parser("shortcut-report")
    shortcut_report.add_argument("path", type=Path, help="Dataset directory or rows.jsonl file.")
    shortcut_report.add_argument("--out", type=Path, help="Output directory. Defaults to the dataset directory.")
    shortcut_report.set_defaults(func=_cmd_dataset_shortcut_report)
    preview = dataset_sub.add_parser("preview")
    preview.add_argument("path", type=Path, help="Dataset directory or rows.jsonl file.")
    preview.add_argument("--graphs", type=Path, help="Optional graph directory or graphs.jsonl file for node samples.")
    preview.add_argument("--out", type=Path, required=True)
    preview.add_argument("--sample-per-family", type=int, default=1)
    preview.add_argument("--family", action="append", dest="families")
    preview.add_argument("--node-type", action="append", dest="node_types")
    preview.add_argument("--seed", type=int, default=0)
    preview.add_argument("--max-prompt-chars", type=int, default=12000)
    preview.set_defaults(func=_cmd_dataset_preview)
    synthesis_selfcheck = dataset_sub.add_parser("synthesis-selfcheck")
    synthesis_selfcheck.add_argument("--out", type=Path, required=True)
    synthesis_selfcheck.add_argument("--sample-per-family", type=int, default=20)
    synthesis_selfcheck.add_argument("--seed", type=int, default=0)
    synthesis_selfcheck.set_defaults(func=_cmd_dataset_synthesis_selfcheck)

    evaluation = subparsers.add_parser("evaluation")
    evaluation_sub = evaluation.add_subparsers(required=True)
    baseline = evaluation_sub.add_parser("baseline")
    baseline.add_argument("--rows", type=Path, required=True)
    baseline.add_argument("--out", type=Path, required=True)
    baseline.set_defaults(func=_cmd_evaluation_baseline)
    grade = evaluation_sub.add_parser("grade")
    grade.add_argument("--rows", type=Path, required=True)
    grade.add_argument("--responses", type=Path, required=True)
    grade.add_argument("--out", type=Path, required=True)
    grade.set_defaults(func=_cmd_evaluation_grade)
    grade_private = evaluation_sub.add_parser("grade-private")
    grade_private.add_argument("--public", type=Path, required=True)
    grade_private.add_argument("--private", type=Path, required=True)
    grade_private.add_argument("--responses", type=Path, required=True)
    grade_private.add_argument("--out", type=Path, required=True)
    grade_private.set_defaults(func=_cmd_evaluation_grade_private)
    closed_book = evaluation_sub.add_parser("closed-book")
    closed_book.add_argument("--public", type=Path, required=True)
    closed_book.add_argument("--private", type=Path, required=True)
    closed_book.add_argument("--requests", type=Path, required=True)
    closed_book.add_argument("--responses", type=Path, required=True)
    closed_book.add_argument("--out", type=Path, required=True)
    closed_book.add_argument("--model-id", required=True)
    closed_book.add_argument("--setting", default="zero-shot")
    closed_book.set_defaults(func=_cmd_evaluation_closed_book)
    export_requests = evaluation_sub.add_parser("export-requests")
    export_requests.add_argument("--rows", type=Path, required=True)
    export_requests.add_argument("--out", type=Path, required=True)
    export_requests.add_argument("--mode", choices=["zero-shot", "few-shot"], default="zero-shot")
    export_requests.add_argument("--examples", type=Path)
    export_requests.add_argument("--shots", type=int, default=3)
    export_requests.set_defaults(func=_cmd_evaluation_export_requests)
    export_oracle_responses = evaluation_sub.add_parser("export-oracle-responses")
    export_oracle_responses.add_argument("--private", type=Path, required=True)
    export_oracle_responses.add_argument("--out", type=Path, required=True)
    export_oracle_responses.set_defaults(func=_cmd_evaluation_export_oracle_responses)
    tool_assisted = evaluation_sub.add_parser("tool-assisted-upper-bound")
    tool_assisted.add_argument("--public", type=Path, required=True)
    tool_assisted.add_argument("--private", type=Path, required=True)
    tool_assisted.add_argument("--out", type=Path, required=True)
    tool_assisted.set_defaults(func=_cmd_evaluation_tool_assisted_upper_bound)

    training = subparsers.add_parser("training")
    training_sub = training.add_subparsers(required=True)
    export_sft = training_sub.add_parser("export-sft")
    export_sft.add_argument("--rows", type=Path, required=True)
    export_sft.add_argument("--out", type=Path, required=True)
    export_sft.add_argument("--scaling-sizes", type=int, nargs="*", default=[8, 16, 32])
    export_sft.add_argument("--release-tier", choices=RELEASE_TIERS, default=DEFAULT_RELEASE_TIER)
    export_sft.add_argument("--family-manifest", type=Path, default=DEFAULT_FAMILY_MANIFEST)
    export_sft.add_argument("--preview-evidence", type=Path)
    export_sft.add_argument("--family-test-evidence", type=Path, default=DEFAULT_FAMILY_TEST_EVIDENCE)
    export_sft.add_argument(
        "--include-calibration",
        action="store_true",
        help="Include syntax-only calibration rows instead of the default geometry-critical training subset.",
    )
    export_sft.add_argument(
        "--allow-failing-training-gates",
        action="store_true",
        help="Write SFT artifacts even when applicable default training gates fail.",
    )
    export_sft.set_defaults(func=_cmd_training_export_sft)

    experiment = subparsers.add_parser("experiment")
    experiment_sub = experiment.add_subparsers(required=True)
    smoke_exp = experiment_sub.add_parser("smoke")
    smoke_exp.add_argument("--sources-jsonl", type=Path, required=True)
    smoke_exp.add_argument("--limit", type=int, default=10)
    smoke_exp.add_argument("--out", type=Path, required=True)
    smoke_exp.add_argument("--scaling-sizes", type=int, nargs="*", default=[8, 16, 32])
    smoke_exp.set_defaults(func=_cmd_experiment_smoke)
    package = experiment_sub.add_parser("package")
    package.add_argument("--run", type=Path, required=True)
    package.add_argument("--out", type=Path)
    package.set_defaults(func=_cmd_experiment_package)
    paper_results = experiment_sub.add_parser("paper-results")
    paper_results.add_argument("--run", type=Path, required=True)
    paper_results.add_argument("--out", type=Path)
    paper_results.set_defaults(func=_cmd_experiment_paper_results)

    return parser


def _cmd_sources_inspect(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    audit = source_audit(sources)
    return {
        "source_count": len(sources),
        "first_source_id": sources[0].source_id if sources else None,
        "paths": [source.source_path for source in sources[:5]],
        "audit_valid": audit["valid"],
        "audit_warning_count": audit["warning_count"],
    }


def _cmd_sources_manifest(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    manifest = source_manifest(sources)
    write_json(args.out, manifest)
    return {
        "source_count": manifest["source_count"],
        "unique_source_id_count": manifest["unique_source_id_count"],
        "unique_source_hash_count": manifest["unique_source_hash_count"],
        "group_keys": sorted(manifest["groups"]),
    }


def _cmd_sources_audit(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    report = source_audit(sources)
    write_json(args.out, report)
    return {
        "valid": report["valid"],
        "source_count": report["source_count"],
        "error_count": report["error_count"],
        "warning_count": report["warning_count"],
    }


def _cmd_sources_from_cadevolve_tar(args: argparse.Namespace) -> dict[str, Any]:
    rows, report = cadevolve_tar_source_rows(
        args.tar,
        limit=args.limit,
        path_prefixes=args.path_prefixes,
        max_member_bytes=args.max_member_bytes,
    )
    write_jsonl(args.out, rows)
    manifest = source_manifest([source_record_from_mapping(row) for row in rows])
    report = {**report, "source_manifest": manifest}
    write_json(args.out.with_suffix(".manifest.json"), manifest)
    write_json(args.out.with_suffix(".report.json"), report)
    return {
        "out": str(args.out),
        "source_count": len(rows),
        "member_count": report["member_count"],
        "python_member_count": report["python_member_count"],
        "skipped_non_cadquery_count": report["skipped_non_cadquery_count"],
        "manifest": str(args.out.with_suffix(".manifest.json")),
        "report": str(args.out.with_suffix(".report.json")),
    }


def _cmd_graph_build(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    traces_by_source = _trace_records_by_source(args.traces_jsonl)
    graphs = [build_graph(source, trace=traces_by_source.get(source.source_id)) for source in sources]
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "graphs.jsonl", graphs)
    report = {
        "graph_count": len(graphs),
        "node_count": sum(len(graph.nodes) for graph in graphs),
        "relation_count": sum(len(graph.relations) for graph in graphs),
        "measurement_count": sum(len(graph.measurements) for graph in graphs),
        "diagnostic_count": sum(len(graph.diagnostics) for graph in graphs),
    }
    write_json(args.out / "graph_report.json", report)
    return report


def _trace_records_by_source(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    return {
        str(record["source_id"]): record
        for record in read_jsonl(path)
        if record.get("source_id")
    }


def _cmd_trace_run(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    traces = trace_sources_bounded(
        sources,
        timeout_seconds=args.timeout_seconds,
        worker_count=args.workers,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "traces.jsonl", traces)
    report = trace_report(traces)
    write_json(args.out / "trace_report.json", report)
    return report


def _cmd_query_smoke(args: argparse.Namespace) -> dict[str, Any]:
    graphs = _load_graphs(args.graph)
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for graph in graphs:
        for query in smoke_queries(graph):
            resolution = resolve_query(graph, query)
            record = {
                "graph_id": graph.graph_id,
                "query": resolution.query_program,
                "resolution": resolution,
            }
            if resolution.verifier_status == "resolved":
                records.append(record)
            else:
                failures.append(
                    {
                        "graph_id": graph.graph_id,
                        "query_id": query.query_id,
                        "reason": resolution.candidate_trace.failure_reason,
                        "candidate_trace": resolution.candidate_trace,
                    }
                )
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "graphs.jsonl", graphs)
    write_jsonl(args.out / "queries.jsonl", records)
    write_jsonl(args.out / "failure_manifest.jsonl", failures)
    report = {"query_count": len(records), "failure_count": len(failures)}
    write_json(args.out / "query_report.json", report)
    return report


def _cmd_query_synthesize(args: argparse.Namespace) -> dict[str, Any]:
    graphs = _load_graphs(args.graph)
    release_families = _release_family_ids(args.family_manifest) if not args.include_review_only else None
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped_review_only_count = 0
    for graph in graphs:
        for query in synthesize_graph_hop_queries(graph, max_per_family=args.max_per_family):
            family_id = _query_family_id(query.query_id)
            if release_families is not None and family_id not in release_families:
                skipped_review_only_count += 1
                continue
            resolution = resolve_query(graph, query)
            record = {
                "graph_id": graph.graph_id,
                "query": resolution.query_program,
                "resolution": resolution,
            }
            if resolution.verifier_status == "resolved":
                records.append(record)
            else:
                failures.append(
                    {
                        "graph_id": graph.graph_id,
                        "query_id": query.query_id,
                        "reason": resolution.candidate_trace.failure_reason,
                        "candidate_trace": resolution.candidate_trace,
                    }
                )
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "graphs.jsonl", graphs)
    write_jsonl(args.out / "queries.jsonl", records)
    write_jsonl(args.out / "failure_manifest.jsonl", failures)
    report = {
        "query_count": len(records),
        "failure_count": len(failures),
        "skipped_review_only_count": skipped_review_only_count,
        "max_per_family": max(1, args.max_per_family),
        "release_families_only": release_families is not None,
        "query_record_format": "compact_graph_sidecar_v1",
    }
    write_json(args.out / "query_report.json", report)
    return report


def _release_family_ids(manifest_path: Path) -> set[str]:
    manifest = load_family_manifest(manifest_path)
    return {
        family_id
        for family_id, family in manifest["families"].items()
        if family["status"] in RELEASE_STATUSES
    }


def _query_family_id(query_id: str) -> str:
    return query_id.rsplit(":", 1)[-1]


def _cmd_dataset_materialize(args: argparse.Namespace) -> dict[str, Any]:
    query_records = read_jsonl(args.queries)
    graph_lookup = _materialize_graph_lookup(args)
    rows = []
    for record in query_records:
        graph = _graph_for_query_record(record, graph_lookup)
        query = query_from_dict(record["query"])
        resolution = resolve_query(graph, query)
        if resolution.verifier_status == "resolved":
            rows.append(materialize_row(graph, resolution))
    args.out.mkdir(parents=True, exist_ok=True)
    split_groups = assign_splits(rows)
    row_dicts = []
    for split, split_rows in split_groups.items():
        for row in split_rows:
            item = row.__dict__.copy()
            item["split"] = split
            row_dicts.append(item)
    write_jsonl(args.out / "rows.jsonl", row_dicts)
    for split, split_rows in split_groups.items():
        split_dicts = []
        for row in split_rows:
            item = row.__dict__.copy()
            item["split"] = split
            split_dicts.append(item)
        write_jsonl(args.out / "jsonl" / f"{split}.jsonl", split_dicts)
    manifest = split_manifest(rows)
    write_json(args.out / "split_manifest.json", manifest)
    query_failure_path = args.queries.parent / "failure_manifest.jsonl"
    if query_failure_path.exists():
        write_jsonl(args.out / "failure_manifest.jsonl", read_jsonl(query_failure_path))
    report = dataset_report(row_dicts)
    report["split_manifest"] = manifest
    report["leakage_audit"] = leakage_audit(row_dicts, manifest)
    report["split_audit"] = split_audit(row_dicts, manifest)
    write_json(args.out / "split_audit.json", report["split_audit"])
    write_json(args.out / "dataset_report.json", report)
    return report


def _materialize_graph_lookup(args: argparse.Namespace) -> dict[str, OntologyGraph]:
    graph_path = args.graphs
    if graph_path is None:
        sidecar = args.queries.parent / "graphs.jsonl"
        if sidecar.exists():
            graph_path = sidecar
    if graph_path is None:
        return {}
    return {graph.graph_id: graph for graph in _load_graphs(graph_path)}


def _graph_for_query_record(record: dict[str, Any], graph_lookup: dict[str, OntologyGraph]) -> OntologyGraph:
    embedded = record.get("graph")
    if embedded is not None:
        return graph_from_dict(embedded)
    graph_id = record.get("graph_id")
    if not isinstance(graph_id, str):
        raise ValueError("query record has neither embedded graph nor graph_id")
    graph = graph_lookup.get(graph_id)
    if graph is None:
        raise ValueError(f"missing graph sidecar entry for query graph_id {graph_id!r}")
    return graph


def _cmd_dataset_validate(args: argparse.Namespace) -> dict[str, Any]:
    return validate_dataset_dir(args.path, release=args.release)


def _cmd_dataset_audit(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.path / "rows.jsonl")
    manifest_path = args.path / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    report = leakage_audit(rows, manifest)
    write_json(args.path / "leakage_audit.json", report)
    return report


def _cmd_dataset_quarantine(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.path / "rows.jsonl")
    report = quarantine_report(rows)
    write_json(args.path / "quarantine_report.json", report)
    return report


def _cmd_dataset_export_release(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.path / "rows.jsonl")
    result = export_release_dataset(
        rows,
        out=args.out,
        source_dataset=args.path,
        allow_failing_release_gates=bool(args.allow_failing_release_gates),
        release_tier=args.release_tier,
        family_manifest=args.family_manifest,
        preview_evidence=args.preview_evidence,
        family_test_evidence=args.family_test_evidence,
    )
    return {
        "row_count": result["row_count"],
        "release_tier": result["release_tier"],
        "excluded_quarantine_count": result["excluded_quarantine_count"],
        "excluded_release_validation_count": result["excluded_release_validation_count"],
        "excluded_prompt_policy_count": result["excluded_prompt_policy_count"],
        "excluded_syntax_only_calibration_cap_count": result[
            "excluded_syntax_only_calibration_cap_count"
        ],
        "excluded_release_balance_cap_count": result["excluded_release_balance_cap_count"],
        "blocking_release_gates": result["blocking_release_gates"],
        "valid": result["valid"],
        "out": result["out"],
    }


def _cmd_dataset_export_public_private(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.path / "rows.jsonl")
    return write_public_private_artifacts(rows, args.path)


def _cmd_dataset_card(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.path / "rows.jsonl")
    report_path = args.path / "dataset_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else dataset_report(rows)
    validation_path = args.path / "validation_report.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else validate_dataset_dir(args.path)
    manifest_path = args.path / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    audit_path = args.path / "leakage_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else leakage_audit(rows, manifest)
    quarantine_path = args.path / "quarantine_report.json"
    if not quarantine_path.exists():
        write_json(quarantine_path, quarantine_report(rows))
    failure_path = args.path / "failure_manifest.jsonl"
    failures = failure_report(read_jsonl(failure_path)) if failure_path.exists() else failure_report([])
    write_json(args.path / "failure_report.json", failures)
    out = args.out or args.path / "DATASET_CARD.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        dataset_card_markdown(
            dataset_path=args.path,
            report=report,
            validation=validation,
            audit=audit,
            failures=failures,
        ),
        encoding="utf-8",
    )
    return {"dataset_card": str(out), "failure_report": str(args.path / "failure_report.json")}


def _cmd_dataset_release_report(args: argparse.Namespace) -> dict[str, Any]:
    return write_release_verifier_report(
        args.path,
        out=args.out,
        release_tier=args.release_tier,
        family_manifest=args.family_manifest,
        preview_evidence=args.preview_evidence,
        family_test_evidence=args.family_test_evidence,
    )


def _cmd_dataset_shortcut_report(args: argparse.Namespace) -> dict[str, Any]:
    rows_path = args.path / "rows.jsonl" if args.path.is_dir() else args.path
    rows = read_jsonl(rows_path)
    report = shortcut_resistance_report(rows)
    out_dir = args.out or (args.path if args.path.is_dir() else args.path.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "shortcut_resistance_report.json", report)
    (out_dir / "SHORTCUT_RESISTANCE_REPORT.md").write_text(
        shortcut_resistance_markdown(report),
        encoding="utf-8",
    )
    return {
        "row_count": report["row_count"],
        "prompt_family_count": report["prompt_family_count"],
        "geometry_hop_positive_share": report["geometry_hop_positive_share"],
        "syntax_only_calibration_share": report["syntax_only_calibration_share"],
        "out": str(out_dir),
    }


def _cmd_dataset_preview(args: argparse.Namespace) -> dict[str, Any]:
    rows_path = args.path / "rows.jsonl" if args.path.is_dir() else args.path
    rows = read_jsonl(rows_path)
    graphs = _load_graphs(args.graphs) if args.graphs else None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        dataset_preview_markdown(
            rows,
            graphs=graphs,
            sample_per_family=args.sample_per_family,
            families=args.families,
            node_types=args.node_types,
            seed=args.seed,
            max_prompt_chars=args.max_prompt_chars,
        ),
        encoding="utf-8",
    )
    evidence = dataset_preview_evidence_report(
        rows,
        preview_path=args.out,
        sample_per_family=args.sample_per_family,
        families=args.families,
        seed=args.seed,
    )
    evidence_path = args.out.with_suffix(".preview_evidence.json")
    write_json(evidence_path, evidence)
    if args.path.is_dir():
        write_json(args.path / DEFAULT_PREVIEW_EVIDENCE_FILENAME, evidence)
    return {
        "out": str(args.out),
        "preview_evidence": str(evidence_path),
        "row_count": len(rows),
        "graph_count": len(graphs) if graphs is not None else 0,
        "sample_per_family": args.sample_per_family,
        "families": args.families or [],
        "node_types": args.node_types or [],
        "seed": args.seed,
    }


def _cmd_dataset_synthesis_selfcheck(args: argparse.Namespace) -> dict[str, Any]:
    return write_synthesis_selfcheck(
        args.out,
        sample_per_family=args.sample_per_family,
        seed=args.seed,
    )


def _cmd_evaluation_baseline(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.rows)
    results = run_baselines(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {
        name: {key: value for key, value in result.items() if key != "predictions"}
        for name, result in results.items()
    }
    write_json(args.out / "baseline_metrics.json", metrics)
    for name, result in results.items():
        write_jsonl(args.out / f"{name}_predictions.jsonl", result["predictions"])
    return metrics


def _cmd_evaluation_grade(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.rows)
    responses = read_jsonl(args.responses)
    result = grade_responses(rows, responses)
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {key: value for key, value in result.items() if key != "graded"}
    write_json(args.out / "prediction_metrics.json", metrics)
    write_jsonl(args.out / "graded_responses.jsonl", result["graded"])
    return metrics


def _cmd_evaluation_grade_private(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_jsonl(args.public)
    private_rows = read_jsonl(args.private)
    responses = read_jsonl(args.responses)
    result = grade_public_private(public_rows, private_rows, responses)
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {key: value for key, value in result.items() if key != "graded"}
    write_json(args.out / "prediction_metrics.json", metrics)
    write_jsonl(args.out / "graded_responses.jsonl", result["graded"])
    return metrics


def _cmd_evaluation_closed_book(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_jsonl(args.public)
    private_rows = read_jsonl(args.private)
    requests = read_jsonl(args.requests)
    responses = read_jsonl(args.responses)
    result = run_closed_book_evaluation(
        public_rows,
        private_rows,
        requests,
        responses,
        model_id=args.model_id,
        setting=args.setting,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    report = {key: value for key, value in result.items() if key != "graded"}
    write_json(args.out / "closed_book_report.json", report)
    write_json(args.out / "prediction_metrics.json", result["metrics"])
    write_jsonl(args.out / "graded_responses.jsonl", result["graded"])
    return report


def _cmd_evaluation_export_requests(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.rows)
    if args.mode == "few-shot":
        examples = read_jsonl(args.examples) if args.examples else rows
        requests = few_shot_requests(rows, examples, shots=args.shots)
    else:
        requests = zero_shot_requests(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out, requests)
    report = {"request_count": len(requests), "mode": args.mode, "output": str(args.out)}
    write_json(args.out.with_suffix(".report.json"), report)
    return report


def _cmd_evaluation_export_oracle_responses(args: argparse.Namespace) -> dict[str, Any]:
    private_rows = read_jsonl(args.private)
    responses = oracle_responses(private_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out, responses)
    report = {
        "response_count": len(responses),
        "private_rows": str(args.private),
        "output": str(args.out),
    }
    write_json(args.out.with_suffix(".report.json"), report)
    return report


def _cmd_evaluation_tool_assisted_upper_bound(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_jsonl(args.public)
    private_rows = read_jsonl(args.private)
    result = run_tool_assisted_upper_bound(public_rows, private_rows)
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "tool_assisted_responses.jsonl", result["responses"])
    write_json(args.out / "prediction_metrics.json", result["metrics"])
    write_jsonl(args.out / "graded_responses.jsonl", result["graded"])
    report = {key: value for key, value in result.items() if key not in {"responses", "graded"}}
    write_json(args.out / "tool_assisted_report.json", report)
    return report


def _cmd_training_export_sft(args: argparse.Namespace) -> dict[str, Any]:
    profile = release_gate_profile(args.release_tier)
    input_rows = read_jsonl(args.rows)
    rows = input_rows if args.include_calibration else default_training_rows(input_rows)
    args.out.mkdir(parents=True, exist_ok=True)
    answer_rows = answer_sft_rows(rows)
    reasoning_rows = reasoning_sft_rows(rows)
    write_jsonl(args.out / "answer_sft.jsonl", answer_rows)
    write_jsonl(args.out / "reasoning_sft.jsonl", reasoning_rows)
    ablation_groups = ablation_sft_groups(rows)
    scaling_groups = scaling_sft_groups(rows, args.scaling_sizes)
    for name, group_rows in ablation_groups.items():
        write_jsonl(args.out / "ablations" / f"{name}.jsonl", group_rows)
    for name, group_rows in scaling_groups.items():
        write_jsonl(args.out / "scaling" / f"{name}.jsonl", group_rows)
    report = {
        "input_rows": len(input_rows),
        "training_rows": len(rows),
        "excluded_calibration_or_noncritical_rows": len(input_rows) - len(rows),
        "excluded_calibration_noncritical_or_quarantined_rows": len(input_rows) - len(rows),
        "include_calibration": bool(args.include_calibration),
        "release_tier": profile.name,
        "answer_sft_rows": len(answer_rows),
        "reasoning_sft_rows": len(reasoning_rows),
        "ablation_groups": {name: len(group_rows) for name, group_rows in ablation_groups.items()},
        "scaling_groups": {name: len(group_rows) for name, group_rows in scaling_groups.items()},
    }
    report["training_readiness"] = training_readiness_report(
        input_rows,
        rows,
        include_calibration=bool(args.include_calibration),
        dominance_threshold=profile.min_geometry_critical_training_share,
        max_syntax_only_share=profile.max_default_sft_syntax_only_share,
    )
    report["input_balance"] = release_balance_report(input_rows, release_tier=profile.name)
    report["training_balance"] = release_balance_report(rows, release_tier=profile.name)
    report["intended_family_coverage"] = intended_family_coverage_report(
        rows,
        manifest_path=args.family_manifest,
        enforce=profile.enforce_intended_family_coverage,
    )
    report["intended_family_share_feasibility"] = intended_family_share_feasibility_report(
        report["intended_family_coverage"],
        profile,
    )
    report["parameter_balance"] = parameter_balance_report(
        rows,
        family_manifest=args.family_manifest,
        max_parameter_value_share=profile.max_parameter_value_share,
        min_axis_direction_share=profile.min_axis_direction_parameter_share,
        enforce=profile.enforce_parameter_balance,
    )
    preview_evidence_payload = (
        json.loads(args.preview_evidence.read_text(encoding="utf-8"))
        if args.preview_evidence and args.preview_evidence.exists()
        else None
    )
    report["preview_evidence"] = preview_evidence_gate_report(
        rows,
        evidence=preview_evidence_payload,
        family_manifest=args.family_manifest,
        min_samples_per_family=profile.min_preview_samples_per_family,
        enforce=profile.enforce_preview_evidence,
    )
    report["family_test_evidence"] = family_test_evidence_gate_report(
        rows,
        evidence_path=args.family_test_evidence,
        family_manifest=args.family_manifest,
        enforce=profile.enforce_family_test_evidence,
    )
    report["training_stop_gates"] = _training_stop_gates(
        report["training_readiness"],
        report["training_balance"],
        report["intended_family_coverage"],
        report["intended_family_share_feasibility"],
        report["parameter_balance"],
        report["preview_evidence"],
        report["family_test_evidence"],
        profile_name=profile.name,
    )
    report["blocking_training_gates"] = _blocking_gates(report["training_stop_gates"])
    report["valid_for_training"] = not report["blocking_training_gates"]
    report["enforced_training_gates"] = not bool(args.include_calibration)
    write_json(args.out / "sft_report.json", report)
    if (
        report["blocking_training_gates"]
        and report["enforced_training_gates"]
        and not bool(args.allow_failing_training_gates)
    ):
        raise RuntimeError(f"training gates failed: {report['blocking_training_gates']}")
    return report


def _training_stop_gates(
    training_readiness: dict[str, Any],
    training_balance: dict[str, Any],
    intended_family_coverage: dict[str, Any],
    intended_family_share_feasibility: dict[str, Any],
    parameter_balance: dict[str, Any],
    preview_evidence: dict[str, Any],
    family_test_evidence: dict[str, Any],
    *,
    profile_name: str = DEFAULT_RELEASE_TIER,
) -> dict[str, Any]:
    profile = release_gate_profile(profile_name)
    return {
        "geometry_critical_dominance": training_readiness["passes_geometry_critical_dominance"],
        "default_sft_row_count": (
            True
            if profile.min_default_sft_rows is None
            else training_readiness["training_rows"] >= profile.min_default_sft_rows
        ),
        "default_sft_syntax_only_cap": training_readiness["passes_syntax_only_training_cap"],
        "prompt_family_balance": training_balance["passes_prompt_family_balance"],
        "prompt_template_balance": training_balance["passes_prompt_template_balance"],
        "answer_entropy": training_balance["passes_answer_entropy"],
        "geometry_hop_coverage": training_balance["passes_geometry_hop_coverage"],
        "main_browsecomp_hop_coverage": training_balance["passes_main_browsecomp_hop_coverage"],
        "syntax_only_calibration_cap": training_balance["passes_syntax_only_calibration_cap"],
        "value_bearing_measurement_coverage": training_balance["passes_value_bearing_measurement_coverage"],
        "cross_feature_value_bearing_coverage": training_balance["passes_cross_feature_value_bearing_coverage"],
        "candidate_breadth": training_balance["passes_candidate_breadth"],
        "intended_family_coverage": intended_family_coverage["valid"],
        "intended_family_share_feasibility": intended_family_share_feasibility["valid"],
        "parameter_balance": parameter_balance["valid"],
        "preview_evidence": preview_evidence["valid"],
        "family_test_evidence": family_test_evidence["valid"],
    }


def _blocking_gates(stop_gates: dict[str, Any]) -> list[str]:
    return [name for name, passed in stop_gates.items() if passed is False]


def _cmd_experiment_smoke(args: argparse.Namespace) -> dict[str, Any]:
    return run_smoke_experiment(
        sources_jsonl=args.sources_jsonl,
        out=args.out,
        limit=args.limit,
        scaling_sizes=args.scaling_sizes,
    )


def _cmd_experiment_package(args: argparse.Namespace) -> dict[str, Any]:
    write_json(args.run / "artifact_manifest.json", run_artifact_manifest(args.run))
    return package_run_artifacts(args.run, args.out)


def _cmd_experiment_paper_results(args: argparse.Namespace) -> dict[str, Any]:
    return write_paper_results(args.run, args.out)


def _load_graphs(path: Path) -> list[OntologyGraph]:
    graph_path = path / "graphs.jsonl" if path.is_dir() else path
    return [graph_from_dict(row) for row in read_jsonl(graph_path)]


if __name__ == "__main__":
    raise SystemExit(main())
