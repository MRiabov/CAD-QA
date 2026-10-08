"""Graph-first CAD-QA command line interface."""

from __future__ import annotations

import argparse
from collections import Counter
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
from cad_qa.harbor import (
    DEFAULT_HARBOR_ENVIRONMENT,
    DEFAULT_HARBOR_MODEL,
    HARBOR_ENVIRONMENTS,
    export_harbor_atif,
    materialize_harbor_dataset,
    materialize_harbor_tasks,
)
from cad_qa.io import (
    existing_record_artifact_path,
    iter_records,
    read_records,
    record_artifact_path,
    write_json,
    write_jsonl,
    write_records,
)
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
    cadevolve_directory_scan_stats,
    cadevolve_source_table_rows,
    cadevolve_tar_source_rows,
    iter_cadevolve_directory_source_rows,
    load_sources_jsonl,
    source_audit,
    source_geometry_feature_tags,
    source_manifest,
    source_record_from_mapping,
    write_cadevolve_source_cache_parquet,
)
from cad_qa.trace import trace_report, trace_sources_bounded


RELEASE_SUPPORT_REQUIREMENTS = {
    "path_point_families": {
        "required_node_types": ("path_point",),
        "required_relation_types": ("point_on_path",),
        "required_measurement_names": ("coordinate_x", "distance_to_origin"),
    },
    "path_segment_families": {
        "required_node_types": ("path_segment",),
        "required_relation_types": ("segment_on_path",),
        "required_measurement_names": ("segment_length", "midpoint_distance_to_origin"),
    },
    "kernel_vertex_families": {
        "required_node_types": ("vertex",),
        "required_relation_types": ("has_kernel_stable_vertex_id",),
        "required_measurement_names": ("coordinate_x", "distance_to_origin"),
    },
    "void_region_families": {
        "required_node_types": ("void_region",),
        "required_relation_types": ("has_kernel_void_region_geometry",),
        "required_measurement_names": ("volume", "centroid_x"),
    },
    "face_spatial_relation_chain_families": {
        "required_node_types": ("face",),
        "required_relation_types": ("has_kernel_stable_face_id",),
        "any_relation_types": (
            "adjacent_to",
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
        ),
        "required_measurement_names": ("face_area",),
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except Exception as exc:
        print(f"cadqa: error: {exc}", file=sys.stderr)
        return 1
    if result is not None and not getattr(args, "quiet", False):
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
    source_from_cadevolve_tar.add_argument("--path-contains", action="append", dest="path_contains")
    source_from_cadevolve_tar.add_argument("--code-contains", action="append", dest="code_contains")
    source_from_cadevolve_tar.add_argument("--max-member-bytes", type=int, default=1_000_000)
    source_from_cadevolve_tar.add_argument(
        "--stratify-geometry-tags",
        action="store_true",
        help="Fill limited exports with examples of rare geometry-bearing source tags before archive-order fill.",
    )
    source_from_cadevolve_tar.add_argument(
        "--min-per-geometry-tag",
        type=int,
        default=0,
        help="Minimum selected examples per geometry tag when --stratify-geometry-tags is set. Defaults to 1.",
    )
    source_from_cadevolve_tar.add_argument(
        "--complete-stratified-scan",
        action="store_true",
        help="Scan the full archive for complete tag counts instead of stopping once requested strata are satisfied.",
    )
    source_from_cadevolve_tar.set_defaults(func=_cmd_sources_from_cadevolve_tar)
    source_cache_cadevolve_tar = sources_sub.add_parser("cache-cadevolve-tar")
    source_cache_cadevolve_tar.add_argument("--tar", type=Path, required=True)
    source_cache_cadevolve_tar.add_argument("--out", type=Path, required=True)
    source_cache_cadevolve_tar.add_argument("--path-prefix", action="append", dest="path_prefixes")
    source_cache_cadevolve_tar.add_argument("--path-contains", action="append", dest="path_contains")
    source_cache_cadevolve_tar.add_argument("--code-contains", action="append", dest="code_contains")
    source_cache_cadevolve_tar.add_argument("--max-member-bytes", type=int, default=1_000_000)
    source_cache_cadevolve_tar.add_argument(
        "--workers",
        type=int,
        help="Parallel workers for tar member normalization (default: min(64, cpu_count * 4)).",
    )
    source_cache_cadevolve_tar.set_defaults(func=_cmd_sources_cache_cadevolve_tar)
    source_cache_cadevolve_dir = sources_sub.add_parser("cache-cadevolve-dir")
    source_cache_cadevolve_dir.add_argument("--root", type=Path, required=True)
    source_cache_cadevolve_dir.add_argument("--out", type=Path, required=True)
    source_cache_cadevolve_dir.add_argument("--path-prefix", action="append", dest="path_prefixes")
    source_cache_cadevolve_dir.add_argument("--path-contains", action="append", dest="path_contains")
    source_cache_cadevolve_dir.add_argument("--code-contains", action="append", dest="code_contains")
    source_cache_cadevolve_dir.add_argument("--max-member-bytes", type=int, default=1_000_000)
    source_cache_cadevolve_dir.add_argument(
        "--workers",
        type=int,
        help="Parallel workers for directory scan and source normalization (default: min(64, cpu_count * 4)).",
    )
    source_cache_cadevolve_dir.set_defaults(func=_cmd_sources_cache_cadevolve_dir)
    source_from_cadevolve_cache = sources_sub.add_parser("from-cadevolve-cache")
    source_from_cadevolve_cache.add_argument("--cache", type=Path, required=True)
    source_from_cadevolve_cache.add_argument("--out", type=Path, required=True)
    source_from_cadevolve_cache.add_argument("--limit", type=int)
    source_from_cadevolve_cache.add_argument(
        "--exclude-sources",
        action="append",
        type=Path,
        help="Source artifact containing source_id values to exclude from the selected cache slice.",
    )
    source_from_cadevolve_cache.add_argument("--path-prefix", action="append", dest="path_prefixes")
    source_from_cadevolve_cache.add_argument("--path-contains", action="append", dest="path_contains")
    source_from_cadevolve_cache.add_argument("--code-contains", action="append", dest="code_contains")
    source_from_cadevolve_cache.add_argument(
        "--stratify-geometry-tags",
        action="store_true",
        help="Fill limited exports with examples of rare geometry-bearing source tags before table-order fill.",
    )
    source_from_cadevolve_cache.add_argument(
        "--min-per-geometry-tag",
        type=int,
        default=0,
        help="Minimum selected examples per geometry tag when --stratify-geometry-tags is set. Defaults to 1.",
    )
    source_from_cadevolve_cache.set_defaults(func=_cmd_sources_from_cadevolve_cache)

    graph = subparsers.add_parser("graph")
    graph_sub = graph.add_subparsers(required=True)
    build = graph_sub.add_parser("build")
    build.add_argument("--sources-jsonl", type=Path, required=True)
    build.add_argument("--limit", type=int)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--traces-jsonl", type=Path)
    build.add_argument(
        "--shard-size",
        type=int,
        default=0,
        help="Write graph artifacts in parquet shards of this many graphs instead of one in-memory file.",
    )
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
    materialize.add_argument("--graphs", type=Path, help="Optional graph directory or graph artifact file for compact query records.")
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
    release_report.add_argument(
        "--quiet",
        action="store_true",
        help="Write report artifacts without printing the full JSON report to stdout.",
    )
    release_report.set_defaults(func=_cmd_dataset_release_report)
    shortcut_report = dataset_sub.add_parser("shortcut-report")
    shortcut_report.add_argument("path", type=Path, help="Dataset directory or dataset file.")
    shortcut_report.add_argument("--out", type=Path, help="Output directory. Defaults to the dataset directory.")
    shortcut_report.set_defaults(func=_cmd_dataset_shortcut_report)
    preview = dataset_sub.add_parser("preview")
    preview.add_argument("path", type=Path, help="Dataset directory or dataset file.")
    preview.add_argument("--graphs", type=Path, help="Optional graph directory or graph artifact file for node samples.")
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

    harbor = subparsers.add_parser("harbor")
    harbor_sub = harbor.add_subparsers(required=True)
    harbor_materialize = harbor_sub.add_parser("materialize")
    harbor_materialize.add_argument("--public", type=Path, required=True)
    harbor_materialize.add_argument("--private", type=Path, required=True)
    harbor_materialize.add_argument("--out", type=Path, required=True)
    _add_harbor_filters(harbor_materialize)
    harbor_materialize.set_defaults(func=_cmd_harbor_materialize)
    harbor_dataset = harbor_sub.add_parser("materialize-dataset")
    harbor_dataset.add_argument("dataset_dir", type=Path)
    harbor_dataset.add_argument("--out", type=Path, required=True)
    _add_harbor_filters(harbor_dataset)
    harbor_dataset.set_defaults(func=_cmd_harbor_materialize_dataset)
    harbor_sft = harbor_sub.add_parser("export-sft")
    harbor_sft.add_argument("--rows", type=Path, required=True)
    harbor_sft.add_argument("--out", type=Path, required=True)
    harbor_sft.add_argument("--scaling-sizes", type=int, nargs="*", default=[8, 16, 32])
    harbor_sft.add_argument("--release-tier", choices=RELEASE_TIERS, default=DEFAULT_RELEASE_TIER)
    harbor_sft.add_argument("--family-manifest", type=Path, default=DEFAULT_FAMILY_MANIFEST)
    harbor_sft.add_argument("--preview-evidence", type=Path)
    harbor_sft.add_argument("--family-test-evidence", type=Path, default=DEFAULT_FAMILY_TEST_EVIDENCE)
    harbor_sft.add_argument("--include-calibration", action="store_true")
    harbor_sft.add_argument("--allow-failing-training-gates", action="store_true")
    harbor_sft.set_defaults(func=_cmd_harbor_export_sft)
    harbor_atif = harbor_sub.add_parser("export-atif")
    harbor_atif.add_argument("--responses", type=Path, required=True)
    harbor_atif.add_argument("--public", type=Path, required=True)
    harbor_atif.add_argument("--private", type=Path, required=True)
    harbor_atif.add_argument("--out", type=Path, required=True)
    harbor_atif.set_defaults(func=_cmd_harbor_export_atif)

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


def _add_harbor_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--split", action="append", dest="split")
    parser.add_argument("--difficulty", action="append", dest="difficulty")
    parser.add_argument("--relation-family", action="append", dest="relation_family")
    parser.add_argument("--measurement-scope", action="append", dest="measurement_scope")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--model", default=None, help="Harbor agent model name for the generated job config.")
    parser.add_argument(
        "--environment",
        choices=HARBOR_ENVIRONMENTS,
        default=DEFAULT_HARBOR_ENVIRONMENT,
        help="Harbor execution environment for the generated job config.",
    )
    parser.add_argument(
        "--daytona",
        action="store_const",
        const="daytona",
        dest="environment",
        help="Shortcut for --environment daytona.",
    )
    parser.add_argument(
        "--n-concurrent-trials",
        type=int,
        default=1,
        help="Harbor trial concurrency for the generated job config.",
    )


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
        path_contains=args.path_contains,
        code_contains=args.code_contains,
        max_member_bytes=args.max_member_bytes,
        stratify_by_tags=bool(args.stratify_geometry_tags),
        min_per_tag=args.min_per_geometry_tag,
        complete_stratified_scan=bool(args.complete_stratified_scan),
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


def _cmd_sources_cache_cadevolve_tar(args: argparse.Namespace) -> dict[str, Any]:
    _require_parquet_path(args.out, "--out")
    rows, report = cadevolve_tar_source_rows(
        args.tar,
        path_prefixes=args.path_prefixes,
        path_contains=args.path_contains,
        code_contains=args.code_contains,
        max_member_bytes=args.max_member_bytes,
        workers=args.workers,
    )
    write_cadevolve_source_cache_parquet(args.out, rows)
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


def _cmd_sources_cache_cadevolve_dir(args: argparse.Namespace) -> dict[str, Any]:
    _require_parquet_path(args.out, "--out")
    report = cadevolve_directory_scan_stats(
        args.root,
        path_prefixes=args.path_prefixes,
        path_contains=args.path_contains,
        code_contains=args.code_contains,
        max_member_bytes=args.max_member_bytes,
    )
    rows = iter_cadevolve_directory_source_rows(
        args.root,
        stats=report,
        path_prefixes=args.path_prefixes,
        path_contains=args.path_contains,
        code_contains=args.code_contains,
        max_member_bytes=args.max_member_bytes,
        workers=args.workers,
    )
    row_count = write_cadevolve_source_cache_parquet(args.out, rows)
    report["included_count"] = row_count
    write_json(args.out.with_suffix(".report.json"), report)
    return {
        "out": str(args.out),
        "source_count": row_count,
        "file_count": report["file_count"],
        "python_file_count": report["python_file_count"],
        "skipped_non_cadquery_count": report["skipped_non_cadquery_count"],
        "report": str(args.out.with_suffix(".report.json")),
    }


def _cmd_sources_from_cadevolve_cache(args: argparse.Namespace) -> dict[str, Any]:
    _require_parquet_path(args.cache, "--cache")
    _require_parquet_path(args.out, "--out")
    rows, report = cadevolve_source_table_rows(
        args.cache,
        limit=args.limit,
        path_prefixes=args.path_prefixes,
        path_contains=args.path_contains,
        code_contains=args.code_contains,
        exclude_source_ids=_source_ids_from_record_paths(args.exclude_sources or []),
        stratify_by_tags=bool(args.stratify_geometry_tags),
        min_per_tag=args.min_per_geometry_tag,
    )
    write_cadevolve_source_cache_parquet(args.out, rows)
    manifest = source_manifest([source_record_from_mapping(row) for row in rows])
    report = {**report, "source_manifest": manifest}
    write_json(args.out.with_suffix(".manifest.json"), manifest)
    write_json(args.out.with_suffix(".report.json"), report)
    return {
        "out": str(args.out),
        "source_count": len(rows),
        "table_row_count": report["table_row_count"],
        "candidate_count": report["candidate_count"],
        "manifest": str(args.out.with_suffix(".manifest.json")),
        "report": str(args.out.with_suffix(".report.json")),
    }


def _source_ids_from_record_paths(paths: list[Path]) -> set[str]:
    source_ids: set[str] = set()
    for path in paths:
        for row in read_records(path):
            source_id = row.get("source_id")
            if source_id:
                source_ids.add(str(source_id))
    return source_ids


def _require_parquet_path(path: Path, label: str) -> None:
    if path.suffix != ".parquet":
        raise ValueError(f"{label} must be a .parquet path")


def _cmd_graph_build(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    traces_by_source = _trace_records_by_source(args.traces_jsonl)
    args.out.mkdir(parents=True, exist_ok=True)
    report_builder = _GraphBuildReport()
    shard_size = max(0, int(args.shard_size or 0))
    if shard_size:
        _write_graph_shards(
            args.out,
            (
                build_graph(source, trace=traces_by_source.get(source.source_id))
                for source in sources
            ),
            shard_size=shard_size,
            report_builder=report_builder,
        )
    else:
        graphs = [build_graph(source, trace=traces_by_source.get(source.source_id)) for source in sources]
        write_records(record_artifact_path(args.out, "graphs"), graphs)
        for graph in graphs:
            report_builder.add_graph(graph)
    report = {
        "graph_count": report_builder.graph_count,
        "node_count": report_builder.node_count,
        "relation_count": report_builder.relation_count,
        "measurement_count": report_builder.measurement_count,
        "diagnostic_count": report_builder.diagnostic_count,
        "node_type_counts": dict(sorted(report_builder.node_type_counts.items())),
        "relation_type_counts": dict(sorted(report_builder.relation_type_counts.items())),
        "measurement_scope_counts": dict(sorted(report_builder.measurement_scope_counts.items())),
        "measurement_name_counts": dict(sorted(report_builder.measurement_name_counts.items())),
        "source_geometry_feature_tag_counts": dict(
            sorted(
                Counter(
                    tag
                    for source in sources
                    for tag in (
                        source.metadata.get("source_feature_tags")
                        if source.metadata and isinstance(source.metadata.get("source_feature_tags"), list)
                        else source_geometry_feature_tags(source.source_code)
                    )
                ).items()
            )
        ),
        "release_support_coverage": report_builder.release_support_coverage(),
    }
    if shard_size:
        report["graph_artifact_sharded"] = True
        report["graph_shard_size"] = shard_size
    report["missing_release_support"] = [
        name
        for name, coverage in report["release_support_coverage"].items()
        if coverage["graph_count"] == 0
    ]
    write_json(args.out / "graph_report.json", report)
    return report


class _GraphBuildReport:
    def __init__(self) -> None:
        self.graph_count = 0
        self.node_count = 0
        self.relation_count = 0
        self.measurement_count = 0
        self.diagnostic_count = 0
        self.node_type_counts: Counter[str] = Counter()
        self.relation_type_counts: Counter[str] = Counter()
        self.measurement_scope_counts: Counter[str] = Counter()
        self.measurement_name_counts: Counter[str] = Counter()
        self.release_support_counts: Counter[str] = Counter()
        self.release_support_examples: dict[str, list[str]] = {name: [] for name in RELEASE_SUPPORT_REQUIREMENTS}

    def add_graph(self, graph: OntologyGraph) -> None:
        self.graph_count += 1
        self.node_count += len(graph.nodes)
        self.relation_count += len(graph.relations)
        self.measurement_count += len(graph.measurements)
        self.diagnostic_count += len(graph.diagnostics)
        self.node_type_counts.update(node.type for node in graph.nodes)
        self.relation_type_counts.update(relation.type for relation in graph.relations)
        self.measurement_scope_counts.update(measurement.scope for measurement in graph.measurements)
        self.measurement_name_counts.update(measurement.name for measurement in graph.measurements)
        for name, requirements in RELEASE_SUPPORT_REQUIREMENTS.items():
            if _graph_satisfies_release_support(graph, requirements):
                self.release_support_counts[name] += 1
                examples = self.release_support_examples[name]
                if len(examples) < 10:
                    examples.append(graph.graph_id)

    def release_support_coverage(self) -> dict[str, dict[str, Any]]:
        coverage: dict[str, dict[str, Any]] = {}
        for name, requirements in RELEASE_SUPPORT_REQUIREMENTS.items():
            graph_count = self.release_support_counts[name]
            coverage[name] = {
                "graph_count": graph_count,
                "graph_share": (graph_count / self.graph_count) if self.graph_count else 0.0,
                "example_graph_ids": self.release_support_examples[name],
                "requirements": requirements,
            }
        return coverage


def _write_graph_shards(
    out_dir: Path,
    graphs: Any,
    *,
    shard_size: int,
    report_builder: _GraphBuildReport,
) -> None:
    shard_dir = out_dir / "graphs"
    shard_dir.mkdir(parents=True, exist_ok=True)
    for stale in shard_dir.glob("part-*.parquet"):
        stale.unlink()
    batch: list[OntologyGraph] = []
    shard_index = 0
    for graph in graphs:
        report_builder.add_graph(graph)
        batch.append(graph)
        if len(batch) >= shard_size:
            write_records(shard_dir / f"part-{shard_index:05d}.parquet", batch)
            batch = []
            shard_index += 1
    if batch:
        write_records(shard_dir / f"part-{shard_index:05d}.parquet", batch)


def _release_support_coverage(graphs: list[OntologyGraph]) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    total = len(graphs)
    for name, requirements in RELEASE_SUPPORT_REQUIREMENTS.items():
        graph_ids = [
            graph.graph_id
            for graph in graphs
            if _graph_satisfies_release_support(graph, requirements)
        ]
        coverage[name] = {
            "graph_count": len(graph_ids),
            "graph_share": (len(graph_ids) / total) if total else 0.0,
            "example_graph_ids": graph_ids[:10],
            "requirements": requirements,
        }
    return coverage


def _graph_satisfies_release_support(graph: OntologyGraph, requirements: dict[str, Any]) -> bool:
    node_types = {node.type for node in graph.nodes}
    relation_types = {relation.type for relation in graph.relations}
    measurement_names = {measurement.name for measurement in graph.measurements}
    if not set(requirements.get("required_node_types", ())).issubset(node_types):
        return False
    if not set(requirements.get("required_relation_types", ())).issubset(relation_types):
        return False
    if not set(requirements.get("required_measurement_names", ())).issubset(measurement_names):
        return False
    any_relation_types = set(requirements.get("any_relation_types", ()))
    return not any_relation_types or bool(any_relation_types & relation_types)


def _trace_records_by_source(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    return {
        str(record["source_id"]): record
        for record in read_records(path)
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
    write_records(record_artifact_path(args.out, "traces"), traces)
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
    write_records(record_artifact_path(args.out, "graphs"), graphs)
    write_records(record_artifact_path(args.out, "queries"), records)
    write_records(record_artifact_path(args.out, "failure_manifest"), failures)
    report = {"query_count": len(records), "failure_count": len(failures)}
    write_json(args.out / "query_report.json", report)
    return report


def _cmd_query_synthesize(args: argparse.Namespace) -> dict[str, Any]:
    graphs = _load_graphs(args.graph)
    release_families = _release_family_ids(args.family_manifest) if not args.include_review_only else None
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    skipped_review_only_count = 0
    for graph in graphs:
        for query in synthesize_graph_hop_queries(graph, max_per_family=args.max_per_family):
            family_id = _query_family_id(query)
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
                family_counts[family_id] += 1
            else:
                failures.append(
                    {
                        "graph_id": graph.graph_id,
                        "family_id": family_id,
                        "query_id": query.query_id,
                        "reason": resolution.candidate_trace.failure_reason,
                        "candidate_trace": resolution.candidate_trace,
                    }
                )
    args.out.mkdir(parents=True, exist_ok=True)
    write_records(record_artifact_path(args.out, "graphs"), graphs)
    write_records(record_artifact_path(args.out, "queries"), records)
    write_records(record_artifact_path(args.out, "failure_manifest"), failures)
    report = {
        "query_count": len(records),
        "failure_count": len(failures),
        "skipped_review_only_count": skipped_review_only_count,
        "max_per_family": max(1, args.max_per_family),
        "release_families_only": release_families is not None,
        "query_record_format": "compact_graph_sidecar_parquet_v1",
        "family_counts": dict(sorted(family_counts.items())),
    }
    if release_families is not None:
        report["zero_release_families"] = [
            family_id
            for family_id in sorted(release_families)
            if family_counts.get(family_id, 0) == 0
        ]
    write_json(args.out / "query_report.json", report)
    return report


def _release_family_ids(manifest_path: Path) -> set[str]:
    manifest = load_family_manifest(manifest_path)
    return {
        family_id
        for family_id, family in manifest["families"].items()
        if family["status"] in RELEASE_STATUSES
    }


def _query_family_id(query: Any) -> str:
    if isinstance(query, str):
        return query.rsplit(":", 1)[-1]
    canonical = getattr(query, "canonical_prompt_family", None)
    if isinstance(canonical, str) and canonical:
        return canonical
    sampled = getattr(query, "sampled_parameters", None)
    if isinstance(sampled, dict):
        values = sampled.get("canonical_prompt_family")
        if isinstance(values, list) and values:
            return str(values[0])
        if isinstance(values, str) and values:
            return values
    query_id = getattr(query, "query_id", "")
    return str(query_id).rsplit(":", 1)[-1]


def _cmd_dataset_materialize(args: argparse.Namespace) -> dict[str, Any]:
    query_records = read_records(args.queries)
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
    write_records(record_artifact_path(args.out, "rows"), row_dicts)
    for split, split_rows in split_groups.items():
        split_dicts = []
        for row in split_rows:
            item = row.__dict__.copy()
            item["split"] = split
            split_dicts.append(item)
        write_records(record_artifact_path(args.out / "parquet", split), split_dicts)
    manifest = split_manifest(rows)
    write_json(args.out / "split_manifest.json", manifest)
    query_failure_path = existing_record_artifact_path(args.queries.parent, "failure_manifest")
    if query_failure_path.exists():
        write_records(record_artifact_path(args.out, "failure_manifest"), read_records(query_failure_path))
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
        sidecar = existing_record_artifact_path(args.queries.parent, "graphs")
        if sidecar.exists():
            graph_path = sidecar
        elif _graph_shard_paths(args.queries.parent):
            graph_path = args.queries.parent
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


def _load_dataset_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_dir():
        return read_records(path)
    rows_path = existing_record_artifact_path(path, "rows")
    if rows_path.exists():
        return read_records(rows_path)
    shard_paths = _dataset_row_shard_paths(path)
    if shard_paths:
        rows: list[dict[str, Any]] = []
        for shard_path in shard_paths:
            rows.extend(iter_records(shard_path))
        return rows
    return read_records(rows_path)


def _dataset_row_shard_paths(path: Path) -> list[Path]:
    return [
        *sorted((path / "row_shards").glob("part-*.parquet")),
        *sorted((path / "row_graph_shards").glob("part-*.parquet")),
    ]


def _cmd_dataset_validate(args: argparse.Namespace) -> dict[str, Any]:
    return validate_dataset_dir(args.path, release=args.release)


def _cmd_dataset_audit(args: argparse.Namespace) -> dict[str, Any]:
    rows = _load_dataset_rows(args.path)
    manifest_path = args.path / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    report = leakage_audit(rows, manifest)
    write_json(args.path / "leakage_audit.json", report)
    return report


def _cmd_dataset_quarantine(args: argparse.Namespace) -> dict[str, Any]:
    rows = _load_dataset_rows(args.path)
    report = quarantine_report(rows)
    write_json(args.path / "quarantine_report.json", report)
    return report


def _cmd_dataset_export_release(args: argparse.Namespace) -> dict[str, Any]:
    rows = _load_dataset_rows(args.path)
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
    rows = _load_dataset_rows(args.path)
    return write_public_private_artifacts(rows, args.path)


def _cmd_dataset_card(args: argparse.Namespace) -> dict[str, Any]:
    rows = _load_dataset_rows(args.path)
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
    failure_path = existing_record_artifact_path(args.path, "failure_manifest")
    failures = failure_report(read_records(failure_path)) if failure_path.exists() else failure_report([])
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
    rows = _load_dataset_rows(args.path)
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
    rows = _load_dataset_rows(args.path)
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
    rows = read_records(args.rows)
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
    rows = read_records(args.rows)
    responses = read_records(args.responses)
    result = grade_responses(rows, responses)
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {key: value for key, value in result.items() if key != "graded"}
    write_json(args.out / "prediction_metrics.json", metrics)
    write_jsonl(args.out / "graded_responses.jsonl", result["graded"])
    return metrics


def _cmd_evaluation_grade_private(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
    responses = read_records(args.responses)
    result = grade_public_private(public_rows, private_rows, responses)
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {key: value for key, value in result.items() if key != "graded"}
    write_json(args.out / "prediction_metrics.json", metrics)
    write_jsonl(args.out / "graded_responses.jsonl", result["graded"])
    return metrics


def _cmd_evaluation_closed_book(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
    requests = read_records(args.requests)
    responses = read_records(args.responses)
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
    rows = read_records(args.rows)
    if args.mode == "few-shot":
        examples = read_records(args.examples) if args.examples else rows
        requests = few_shot_requests(rows, examples, shots=args.shots)
    else:
        requests = zero_shot_requests(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_records(args.out, requests)
    report = {"request_count": len(requests), "mode": args.mode, "output": str(args.out)}
    write_json(args.out.with_suffix(".report.json"), report)
    return report


def _cmd_evaluation_export_oracle_responses(args: argparse.Namespace) -> dict[str, Any]:
    private_rows = read_records(args.private)
    responses = oracle_responses(private_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_records(args.out, responses)
    report = {
        "response_count": len(responses),
        "private_rows": str(args.private),
        "output": str(args.out),
    }
    write_json(args.out.with_suffix(".report.json"), report)
    return report


def _cmd_evaluation_tool_assisted_upper_bound(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
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
    input_rows = read_records(args.rows)
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


def _cmd_harbor_materialize(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
    return materialize_harbor_tasks(
        public_rows,
        private_rows,
        args.out,
        split=args.split,
        difficulty=args.difficulty,
        relation_family=args.relation_family,
        measurement_scope=args.measurement_scope,
        max_rows=args.max_rows,
        fresh=bool(args.fresh),
        model_name=args.model or DEFAULT_HARBOR_MODEL,
        environment=args.environment,
        n_concurrent_trials=args.n_concurrent_trials,
    )


def _cmd_harbor_materialize_dataset(args: argparse.Namespace) -> dict[str, Any]:
    return materialize_harbor_dataset(
        args.dataset_dir,
        args.out,
        split=args.split,
        difficulty=args.difficulty,
        relation_family=args.relation_family,
        measurement_scope=args.measurement_scope,
        max_rows=args.max_rows,
        fresh=bool(args.fresh),
        model_name=args.model or DEFAULT_HARBOR_MODEL,
        environment=args.environment,
        n_concurrent_trials=args.n_concurrent_trials,
    )


def _cmd_harbor_export_sft(args: argparse.Namespace) -> dict[str, Any]:
    return _cmd_training_export_sft(args)


def _cmd_harbor_export_atif(args: argparse.Namespace) -> dict[str, Any]:
    responses = read_records(args.responses)
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
    return export_harbor_atif(responses, public_rows, private_rows, args.out)


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
    return [graph_from_dict(row) for graph_path in _graph_record_paths(path) for row in read_records(graph_path)]


def _graph_record_paths(path: Path) -> list[Path]:
    if not path.is_dir():
        return [path]
    graph_path = existing_record_artifact_path(path, "graphs")
    if graph_path.exists():
        return [graph_path]
    shard_paths = _graph_shard_paths(path)
    if shard_paths:
        return shard_paths
    return [graph_path]


def _graph_shard_paths(path: Path) -> list[Path]:
    return sorted((path / "graphs").glob("part-*.parquet"))


if __name__ == "__main__":
    raise SystemExit(main())
