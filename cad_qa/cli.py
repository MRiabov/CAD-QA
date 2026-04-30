"""Graph-first CAD-QA command line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.public import write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release import export_release_dataset
from cad_qa.dataset.report import dataset_card_markdown, dataset_report, failure_report
from cad_qa.dataset.sft import (
    ablation_sft_groups,
    answer_sft_rows,
    reasoning_sft_rows,
    scaling_sft_groups,
)
from cad_qa.dataset.split import assign_splits, split_manifest
from cad_qa.dataset.materialize import materialize_row
from cad_qa.dataset.validate import validate_dataset_dir
from cad_qa.evaluation.baselines import run_baselines
from cad_qa.evaluation.grade import grade_public_private, grade_responses
from cad_qa.evaluation.requests import few_shot_requests, oracle_responses, zero_shot_requests
from cad_qa.experiment import package_run_artifacts, run_smoke_experiment, run_artifact_manifest, write_paper_results
from cad_qa.io import read_jsonl, write_json, write_jsonl
from cad_qa.ontology import build_graph
from cad_qa.ontology.nodes import OntologyGraph, graph_from_dict
from cad_qa.query.ir import query_from_dict
from cad_qa.query.resolver import resolve_query, smoke_queries
from cad_qa.source import load_sources_jsonl


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

    graph = subparsers.add_parser("graph")
    graph_sub = graph.add_subparsers(required=True)
    build = graph_sub.add_parser("build")
    build.add_argument("--sources-jsonl", type=Path, required=True)
    build.add_argument("--limit", type=int)
    build.add_argument("--out", type=Path, required=True)
    build.set_defaults(func=_cmd_graph_build)

    query = subparsers.add_parser("query")
    query_sub = query.add_subparsers(required=True)
    smoke = query_sub.add_parser("smoke")
    smoke.add_argument("--graph", type=Path, required=True)
    smoke.add_argument("--out", type=Path, required=True)
    smoke.set_defaults(func=_cmd_query_smoke)

    dataset = subparsers.add_parser("dataset")
    dataset_sub = dataset.add_subparsers(required=True)
    materialize = dataset_sub.add_parser("materialize")
    materialize.add_argument("--queries", type=Path, required=True)
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
    export_release.set_defaults(func=_cmd_dataset_export_release)
    export_public_private = dataset_sub.add_parser("export-public-private")
    export_public_private.add_argument("path", type=Path)
    export_public_private.set_defaults(func=_cmd_dataset_export_public_private)
    card = dataset_sub.add_parser("card")
    card.add_argument("path", type=Path)
    card.add_argument("--out", type=Path)
    card.set_defaults(func=_cmd_dataset_card)

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

    training = subparsers.add_parser("training")
    training_sub = training.add_subparsers(required=True)
    export_sft = training_sub.add_parser("export-sft")
    export_sft.add_argument("--rows", type=Path, required=True)
    export_sft.add_argument("--out", type=Path, required=True)
    export_sft.add_argument("--scaling-sizes", type=int, nargs="*", default=[8, 16, 32])
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
    return {
        "source_count": len(sources),
        "first_source_id": sources[0].source_id if sources else None,
        "paths": [source.source_path for source in sources[:5]],
    }


def _cmd_graph_build(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources_jsonl(args.sources_jsonl, limit=args.limit)
    graphs = [build_graph(source) for source in sources]
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


def _cmd_query_smoke(args: argparse.Namespace) -> dict[str, Any]:
    graphs = _load_graphs(args.graph)
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for graph in graphs:
        for query in smoke_queries(graph):
            resolution = resolve_query(graph, query)
            record = {
                "graph": graph,
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
    write_jsonl(args.out / "queries.jsonl", records)
    write_jsonl(args.out / "failure_manifest.jsonl", failures)
    report = {"query_count": len(records), "failure_count": len(failures)}
    write_json(args.out / "query_report.json", report)
    return report


def _cmd_dataset_materialize(args: argparse.Namespace) -> dict[str, Any]:
    query_records = read_jsonl(args.queries)
    rows = []
    for record in query_records:
        graph = graph_from_dict(record["graph"])
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
    write_json(args.out / "dataset_report.json", report)
    return report


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
    result = export_release_dataset(rows, out=args.out, source_dataset=args.path)
    return {
        "row_count": result["row_count"],
        "excluded_quarantine_count": result["excluded_quarantine_count"],
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


def _cmd_training_export_sft(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.rows)
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
        "answer_sft_rows": len(answer_rows),
        "reasoning_sft_rows": len(reasoning_rows),
        "ablation_groups": {name: len(group_rows) for name, group_rows in ablation_groups.items()},
        "scaling_groups": {name: len(group_rows) for name, group_rows in scaling_groups.items()},
    }
    write_json(args.out / "sft_report.json", report)
    return report


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
