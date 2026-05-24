"""Small graph-first experiment orchestration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.materialize import materialize_row
from cad_qa.dataset.preview import dataset_preview_markdown
from cad_qa.dataset.public import private_rows, public_rows, write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release import export_release_dataset
from cad_qa.dataset.release_report import release_balance_report, write_release_verifier_report
from cad_qa.dataset.report import dataset_card_markdown, dataset_report, failure_report
from cad_qa.dataset.sft import (
    ablation_sft_groups,
    answer_sft_rows,
    default_training_rows,
    reasoning_sft_rows,
    scaling_sft_groups,
    training_readiness_report,
)
from cad_qa.dataset.split import assign_splits, split_audit, split_manifest
from cad_qa.dataset.validate import validate_rows
from cad_qa.evaluation.baselines import run_baselines
from cad_qa.evaluation.grade import grade_public_private
from cad_qa.evaluation.requests import few_shot_requests, oracle_responses, zero_shot_requests
from cad_qa.evaluation.tool_assisted import run_tool_assisted_upper_bound
from cad_qa.io import read_jsonl, write_json, write_jsonl
from cad_qa.ontology import build_graph
from cad_qa.query.resolver import resolve_query, smoke_queries
from cad_qa.source import load_sources_jsonl


def run_smoke_experiment(
    *,
    sources_jsonl: Path,
    out: Path,
    limit: int = 10,
    scaling_sizes: list[int] | None = None,
) -> dict[str, Any]:
    scaling_sizes = scaling_sizes or [8, 16, 32]
    graph_dir = out / "graph"
    query_dir = out / "query"
    dataset_dir = out / "dataset"
    release_dataset_dir = out / "release_dataset"
    baseline_dir = out / "baseline"
    release_baseline_dir = out / "release_baseline"
    request_dir = out / "requests"
    release_request_dir = out / "release_requests"
    grade_dir = out / "grade"
    release_grade_dir = out / "release_grade"
    tool_dir = out / "tool_assisted"
    release_tool_dir = out / "release_tool_assisted"
    sft_dir = out / "sft"
    release_sft_dir = out / "release_sft"

    sources = load_sources_jsonl(sources_jsonl, limit=limit)
    graphs = [build_graph(source) for source in sources]
    write_jsonl(graph_dir / "graphs.jsonl", graphs)
    graph_report = {
        "graph_count": len(graphs),
        "node_count": sum(len(graph.nodes) for graph in graphs),
        "relation_count": sum(len(graph.relations) for graph in graphs),
        "measurement_count": sum(len(graph.measurements) for graph in graphs),
        "diagnostic_count": sum(len(graph.diagnostics) for graph in graphs),
    }
    write_json(graph_dir / "graph_report.json", graph_report)

    query_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    rows = []
    for graph in graphs:
        for query in smoke_queries(graph):
            resolution = resolve_query(graph, query)
            if resolution.verifier_status == "resolved":
                query_records.append({"graph": graph, "query": resolution.query_program, "resolution": resolution})
                rows.append(materialize_row(graph, resolution))
            else:
                failures.append(
                    {
                        "graph_id": graph.graph_id,
                        "query_id": query.query_id,
                        "reason": resolution.candidate_trace.failure_reason,
                        "candidate_trace": resolution.candidate_trace,
                    }
                )
    write_jsonl(query_dir / "queries.jsonl", query_records)
    write_jsonl(query_dir / "failure_manifest.jsonl", failures)
    query_report = {"query_count": len(query_records), "failure_count": len(failures)}
    write_json(query_dir / "query_report.json", query_report)

    split_groups = assign_splits(rows)
    row_dicts: list[dict[str, Any]] = []
    for split, split_rows in split_groups.items():
        split_dicts = []
        for row in split_rows:
            item = row.__dict__.copy()
            item["split"] = split
            split_dicts.append(item)
            row_dicts.append(item)
        write_jsonl(dataset_dir / "jsonl" / f"{split}.jsonl", split_dicts)
    write_jsonl(dataset_dir / "rows.jsonl", row_dicts)
    public_private = write_public_private_artifacts(row_dicts, dataset_dir)
    manifest = split_manifest(rows)
    write_json(dataset_dir / "split_manifest.json", manifest)
    write_jsonl(dataset_dir / "failure_manifest.jsonl", failures)
    report = dataset_report(row_dicts)
    report["split_manifest"] = manifest
    report["leakage_audit"] = leakage_audit(row_dicts, manifest)
    report["split_audit"] = split_audit(row_dicts, manifest)
    write_json(dataset_dir / "dataset_report.json", report)
    validation = validate_rows(row_dicts)
    write_json(dataset_dir / "validation_report.json", validation)
    release_validation = validate_rows(row_dicts, release=True)
    write_json(dataset_dir / "release_validation_report.json", release_validation)
    audit = leakage_audit(row_dicts, manifest)
    write_json(dataset_dir / "leakage_audit.json", audit)
    split_quality = split_audit(row_dicts, manifest)
    write_json(dataset_dir / "split_audit.json", split_quality)
    quarantine = quarantine_report(row_dicts)
    write_json(dataset_dir / "quarantine_report.json", quarantine)
    failures_by_reason = failure_report(failures)
    write_json(dataset_dir / "failure_report.json", failures_by_reason)
    preview_path = dataset_dir / "GENERATED_PREVIEW.md"
    preview_path.write_text(
        dataset_preview_markdown(
            row_dicts,
            graphs=graphs,
            sample_per_family=1,
            seed=0,
            max_prompt_chars=5000,
        ),
        encoding="utf-8",
    )
    (dataset_dir / "DATASET_CARD.md").write_text(
        dataset_card_markdown(
            dataset_path=dataset_dir,
            report=report,
            validation=validation,
            audit=audit,
            failures=failures_by_reason,
        ),
        encoding="utf-8",
    )
    release_dataset = export_release_dataset(
        row_dicts,
        out=release_dataset_dir,
        source_dataset=dataset_dir,
        allow_failing_release_gates=True,
    )
    release_verifier = write_release_verifier_report(dataset_dir)
    release_dataset_verifier = write_release_verifier_report(release_dataset_dir)

    baselines = run_baselines(row_dicts)
    baseline_metrics = {
        name: {key: value for key, value in result.items() if key != "predictions"}
        for name, result in baselines.items()
    }
    write_json(baseline_dir / "baseline_metrics.json", baseline_metrics)
    for name, result in baselines.items():
        write_jsonl(baseline_dir / f"{name}_predictions.jsonl", result["predictions"])

    release_rows = read_jsonl(release_dataset_dir / "rows.jsonl")
    release_baselines = run_baselines(release_rows)
    release_baseline_metrics = {
        name: {key: value for key, value in result.items() if key != "predictions"}
        for name, result in release_baselines.items()
    }
    write_json(release_baseline_dir / "baseline_metrics.json", release_baseline_metrics)
    for name, result in release_baselines.items():
        write_jsonl(release_baseline_dir / f"{name}_predictions.jsonl", result["predictions"])

    request_report = _write_request_exports(row_dicts, request_dir)
    release_request_report = _write_request_exports(release_rows, release_request_dir)
    grade_report = _write_private_oracle_grade(row_dicts, grade_dir)
    release_grade_report = _write_private_oracle_grade(release_rows, release_grade_dir)
    tool_report = _write_tool_assisted_upper_bound(row_dicts, tool_dir)
    release_tool_report = _write_tool_assisted_upper_bound(release_rows, release_tool_dir)

    sft_report = _write_sft_exports(row_dicts, sft_dir, scaling_sizes)
    release_sft_report = _write_sft_exports(release_rows, release_sft_dir, scaling_sizes)

    experiment_report = {
        "graph": graph_report,
        "query": query_report,
        "dataset": report,
        "release_dataset": {
            "row_count": release_dataset["row_count"],
            "excluded_quarantine_count": release_dataset["excluded_quarantine_count"],
            "excluded_release_validation_count": release_dataset["excluded_release_validation_count"],
            "excluded_prompt_policy_count": release_dataset["excluded_prompt_policy_count"],
            "excluded_syntax_only_calibration_cap_count": release_dataset[
                "excluded_syntax_only_calibration_cap_count"
            ],
            "blocking_release_gates": release_dataset["blocking_release_gates"],
            "valid": release_dataset["valid"],
            "dataset": release_dataset["dataset"],
            "validation": release_dataset["validation"],
            "leakage_audit": release_dataset["leakage_audit"],
            "quarantine": release_dataset["quarantine"],
            "public_private": release_dataset["public_private"],
            "verifier_report": release_dataset_verifier,
        },
        "validation": validation,
        "release_validation": release_validation,
        "leakage_audit": audit,
        "quarantine": quarantine,
        "public_private": public_private,
        "release_verifier": release_verifier,
        "preview": {"path": str(preview_path), "sample_per_family": 1, "seed": 0},
        "baseline": baseline_metrics,
        "release_baseline": release_baseline_metrics,
        "requests": request_report,
        "release_requests": release_request_report,
        "grade": grade_report,
        "release_grade": release_grade_report,
        "tool_assisted": tool_report,
        "release_tool_assisted": release_tool_report,
        "sft": sft_report,
        "release_sft": release_sft_report,
    }
    write_json(out / "experiment_report.json", experiment_report)
    summary = experiment_summary(experiment_report)
    write_json(out / "run_summary.json", summary)
    (out / "RUN_SUMMARY.md").write_text(experiment_summary_markdown(summary), encoding="utf-8")
    (out / "PAPER_RESULTS.md").write_text(paper_results_markdown(experiment_report), encoding="utf-8")
    write_json(out / "artifact_manifest.json", run_artifact_manifest(out))
    return experiment_report


def experiment_summary(report: dict[str, Any]) -> dict[str, Any]:
    dataset = report["dataset"]
    release_dataset = report["release_dataset"]
    return {
        "graph_count": report["graph"]["graph_count"],
        "node_count": report["graph"]["node_count"],
        "relation_count": report["graph"]["relation_count"],
        "measurement_count": report["graph"]["measurement_count"],
        "query_count": report["query"]["query_count"],
        "query_failure_count": report["query"]["failure_count"],
        "smoke_row_count": dataset["row_count"],
        "release_row_count": release_dataset["row_count"],
        "excluded_quarantine_count": release_dataset["excluded_quarantine_count"],
        "excluded_release_validation_count": release_dataset.get("excluded_release_validation_count", 0),
        "excluded_prompt_policy_count": release_dataset.get("excluded_prompt_policy_count", 0),
        "excluded_syntax_only_calibration_cap_count": release_dataset.get(
            "excluded_syntax_only_calibration_cap_count",
            0,
        ),
        "release_blocking_gates": release_dataset.get("blocking_release_gates", []),
        "smoke_validation_valid": report["validation"]["valid"],
        "smoke_release_validation_valid": report["release_validation"]["valid"],
        "release_validation_valid": release_dataset["valid"],
        "leakage_audit_valid": report["leakage_audit"]["valid"],
        "release_leakage_audit_valid": release_dataset["leakage_audit"]["valid"],
        "quarantine_reasons": report["quarantine"]["reasons"],
        "smoke_hop_counts": dataset["hop_counts"],
        "release_hop_counts": release_dataset["dataset"]["hop_counts"],
        "smoke_difficulty_buckets": dataset["difficulty_buckets"],
        "release_difficulty_buckets": release_dataset["dataset"]["difficulty_buckets"],
        "smoke_first_candidate_accuracy": report["baseline"]["first_candidate"]["accuracy"],
        "release_first_candidate_accuracy": report["release_baseline"]["first_candidate"]["accuracy"],
        "smoke_private_oracle_accuracy": report["grade"]["metrics"]["accuracy"],
        "release_private_oracle_accuracy": report["release_grade"]["metrics"]["accuracy"],
        "smoke_tool_assisted_accuracy": report["tool_assisted"]["metrics"]["accuracy"],
        "release_tool_assisted_accuracy": report["release_tool_assisted"]["metrics"]["accuracy"],
        "smoke_zero_shot_requests": report["requests"]["zero_shot_request_count"],
        "release_zero_shot_requests": report["release_requests"]["zero_shot_request_count"],
        "smoke_few_shot_requests": report["requests"]["few_shot_request_count"],
        "release_few_shot_requests": report["release_requests"]["few_shot_request_count"],
        "smoke_answer_sft_rows": report["sft"]["answer_sft_rows"],
        "release_answer_sft_rows": report["release_sft"]["answer_sft_rows"],
        "public_row_count": report["public_private"]["public_row_count"],
        "release_public_row_count": release_dataset["public_private"]["public_row_count"],
    }


def experiment_summary_markdown(summary: dict[str, Any]) -> str:
    checks = {
        "smoke validation": summary["smoke_validation_valid"],
        "release dataset validation": summary["release_validation_valid"],
        "smoke leakage audit": summary["leakage_audit_valid"],
        "release leakage audit": summary["release_leakage_audit_valid"],
    }
    lines = [
        "# CAD-QA Smoke Run Summary",
        "",
        "## Counts",
        "",
        f"- Graphs: {summary['graph_count']}",
        f"- Nodes: {summary['node_count']}",
        f"- Relations: {summary['relation_count']}",
        f"- Measurements: {summary['measurement_count']}",
        f"- Resolved queries: {summary['query_count']}",
        f"- Query failures: {summary['query_failure_count']}",
        f"- Smoke rows: {summary['smoke_row_count']}",
        f"- Release rows: {summary['release_row_count']}",
        f"- Quarantined rows excluded from release: {summary['excluded_quarantine_count']}",
        f"- Release-validation rows excluded from release: {summary['excluded_release_validation_count']}",
        f"- Prompt-policy rows excluded from release: {summary['excluded_prompt_policy_count']}",
        "- Syntax-only calibration rows excluded by cap: "
        f"{summary['excluded_syntax_only_calibration_cap_count']}",
        f"- Release blocking gates: {summary['release_blocking_gates']}",
        "",
        "## Release Readiness",
        "",
        *[f"- {name}: {'pass' if valid else 'fail'}" for name, valid in checks.items()],
        f"- Quarantine reasons: {summary['quarantine_reasons']}",
        "",
        "## Slices",
        "",
        f"- Smoke hop counts: {summary['smoke_hop_counts']}",
        f"- Release hop counts: {summary['release_hop_counts']}",
        f"- Smoke difficulty buckets: {summary['smoke_difficulty_buckets']}",
        f"- Release difficulty buckets: {summary['release_difficulty_buckets']}",
        "",
        "## Artifacts",
        "",
        f"- Smoke zero-shot requests: {summary['smoke_zero_shot_requests']}",
        f"- Release zero-shot requests: {summary['release_zero_shot_requests']}",
        f"- Smoke few-shot requests: {summary['smoke_few_shot_requests']}",
        f"- Release few-shot requests: {summary['release_few_shot_requests']}",
        f"- Smoke answer SFT rows: {summary['smoke_answer_sft_rows']}",
        f"- Release answer SFT rows: {summary['release_answer_sft_rows']}",
        f"- Smoke public rows: {summary['public_row_count']}",
        f"- Release public rows: {summary['release_public_row_count']}",
        "",
        "## Baselines",
        "",
        f"- Smoke first-candidate accuracy: {summary['smoke_first_candidate_accuracy']:.3f}",
        f"- Release first-candidate accuracy: {summary['release_first_candidate_accuracy']:.3f}",
        f"- Smoke private-key oracle accuracy: {summary['smoke_private_oracle_accuracy']:.3f}",
        f"- Release private-key oracle accuracy: {summary['release_private_oracle_accuracy']:.3f}",
        f"- Tool-assisted upper-bound accuracy (smoke): {summary['smoke_tool_assisted_accuracy']:.3f}",
        f"- Tool-assisted upper-bound accuracy (release): {summary['release_tool_assisted_accuracy']:.3f}",
        "",
    ]
    return "\n".join(lines)


def write_paper_results(run_dir: Path, out: Path | None = None) -> dict[str, Any]:
    report_path = run_dir / "experiment_report.json"
    if not report_path.exists():
        raise FileNotFoundError(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    output = out or run_dir / "PAPER_RESULTS.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(paper_results_markdown(report), encoding="utf-8")
    return {"paper_results": str(output)}


def paper_results_markdown(report: dict[str, Any]) -> str:
    release = report["release_dataset"]["dataset"]
    release_grade = report["release_grade"]["metrics"]
    summary = experiment_summary(report)
    lines = [
        "# CAD-QA Paper Results Snapshot",
        "",
        "This generated snapshot is derived from `experiment_report.json`. Treat it as smoke/release-candidate evidence, not final release-scale model results.",
        "",
        "## Headline Counts",
        "",
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Source programs", str(release.get("split_manifest", {}).get("source_count", "unknown"))],
                ["Smoke rows", str(summary["smoke_row_count"])],
                ["Release rows", str(summary["release_row_count"])],
                ["Quarantined smoke rows excluded from release", str(summary["excluded_quarantine_count"])],
                [
                    "Release-validation rows excluded from release",
                    str(summary["excluded_release_validation_count"]),
                ],
                ["Prompt-policy rows excluded from release", str(summary["excluded_prompt_policy_count"])],
                [
                    "Syntax-only calibration rows excluded by cap",
                    str(summary["excluded_syntax_only_calibration_cap_count"]),
                ],
                ["Release blocking gates", str(summary["release_blocking_gates"])],
                ["Release public rows", str(summary["release_public_row_count"])],
                ["Release validation", "pass" if summary["release_validation_valid"] else "fail"],
                ["Release leakage audit", "pass" if summary["release_leakage_audit_valid"] else "fail"],
            ],
        ),
        "",
        "## Release Composition",
        "",
        "### Hop Slices",
        "",
        _counter_table(release.get("hop_counts", {}), "Hop Count"),
        "",
        "### Difficulty",
        "",
        _counter_table(release.get("difficulty_buckets", {}), "Difficulty"),
        "",
        "### Relation Families",
        "",
        _counter_table(release.get("relation_families", {}), "Relation Family"),
        "",
        "### Measurement Scopes",
        "",
        _counter_table(release.get("measurement_scopes", {}), "Measurement Scope"),
        "",
        "## Baselines And Key Checks",
        "",
        _markdown_table(
            ["Metric", "Smoke", "Release"],
            [
                [
                    "Oracle accuracy",
                    _format_float(report["baseline"]["oracle"]["accuracy"]),
                    _format_float(report["release_baseline"]["oracle"]["accuracy"]),
                ],
                [
                    "First-candidate accuracy",
                    _format_float(summary["smoke_first_candidate_accuracy"]),
                    _format_float(summary["release_first_candidate_accuracy"]),
                ],
                [
                    "Private-key oracle accuracy",
                    _format_float(summary["smoke_private_oracle_accuracy"]),
                    _format_float(summary["release_private_oracle_accuracy"]),
                ],
                [
                    "Tool-assisted upper-bound accuracy",
                    _format_float(summary["smoke_tool_assisted_accuracy"]),
                    _format_float(summary["release_tool_assisted_accuracy"]),
                ],
                [
                    "Invalid output rate",
                    _format_float(report["grade"]["metrics"]["invalid_output_rate"]),
                    _format_float(release_grade["invalid_output_rate"]),
                ],
                [
                    "Missing response rate",
                    _format_float(report["grade"]["metrics"]["missing_response_rate"]),
                    _format_float(release_grade["missing_response_rate"]),
                ],
                [
                    "Duplicate responses",
                    str(report["grade"]["metrics"]["duplicate_response_count"]),
                    str(release_grade["duplicate_response_count"]),
                ],
                [
                    "Extra responses",
                    str(report["grade"]["metrics"]["extra_response_count"]),
                    str(release_grade["extra_response_count"]),
                ],
            ],
        ),
        "",
        "## Release Accuracy Slices",
        "",
        "These are oracle key-check slices, included to validate grading and table shape.",
        "",
        "### By Hop",
        "",
        _metric_table(release_grade.get("by_hop", {}), "Hop Count"),
        "",
        "### By Relation Family",
        "",
        _metric_table(release_grade.get("by_relation_family", {}), "Relation Family"),
        "",
        "### By Measurement Scope",
        "",
        _metric_table(release_grade.get("by_measurement_scope", {}), "Measurement Scope"),
        "",
        "## Quarantine Reasons",
        "",
        _counter_table(report["quarantine"].get("reasons", {}), "Reason"),
        "",
    ]
    return "\n".join(lines)


def _counter_table(counter: dict[str, Any], label: str) -> str:
    if not counter:
        return "_None._"
    return _markdown_table([label, "Count"], [[key, str(value)] for key, value in sorted(counter.items())])


def _metric_table(metrics: dict[str, dict[str, Any]], label: str) -> str:
    if not metrics:
        return "_None._"
    rows = [
        [key, str(value.get("total", 0)), str(value.get("correct", 0)), _format_float(value.get("accuracy", 0.0))]
        for key, value in sorted(metrics.items())
    ]
    return _markdown_table([label, "Total", "Correct", "Accuracy"], rows)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _format_float(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _write_request_exports(rows: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    zero_shot = zero_shot_requests(rows)
    write_jsonl(out / "zero_shot_requests.jsonl", zero_shot)
    train_rows = [row for row in rows if row.get("split") == "train"]
    test_rows = [row for row in rows if row.get("split") == "test"]
    example_rows = train_rows or rows
    eval_rows = test_rows or rows
    few_shot = few_shot_requests(eval_rows, example_rows, shots=3)
    write_jsonl(out / "few_shot_test_requests.jsonl", few_shot)
    report = {
        "zero_shot_request_count": len(zero_shot),
        "few_shot_request_count": len(few_shot),
        "few_shot_eval_split": "test" if test_rows else "all",
        "few_shot_example_split": "train" if train_rows else "all",
        "few_shot_shots": few_shot[0]["metadata"]["shots"] if few_shot else 0,
    }
    write_json(out / "request_report.json", report)
    return report


def _write_private_oracle_grade(rows: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    public = public_rows(rows)
    private = private_rows(rows)
    responses = oracle_responses(private)
    result = grade_public_private(public, private, responses)
    metrics = {key: value for key, value in result.items() if key != "graded"}
    write_jsonl(out / "oracle_responses.jsonl", responses)
    write_json(out / "prediction_metrics.json", metrics)
    write_jsonl(out / "graded_responses.jsonl", result["graded"])
    return {
        "oracle_response_count": len(responses),
        "metrics": metrics,
    }


def _write_tool_assisted_upper_bound(rows: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    public = public_rows(rows)
    private = private_rows(rows)
    result = run_tool_assisted_upper_bound(public, private)
    write_jsonl(out / "tool_assisted_responses.jsonl", result["responses"])
    write_json(out / "prediction_metrics.json", result["metrics"])
    write_jsonl(out / "graded_responses.jsonl", result["graded"])
    report = {key: value for key, value in result.items() if key not in {"responses", "graded"}}
    write_json(out / "tool_assisted_report.json", report)
    return report


def _write_sft_exports(rows: list[dict[str, Any]], out: Path, scaling_sizes: list[int]) -> dict[str, Any]:
    training_rows = default_training_rows(rows)
    answer_rows = answer_sft_rows(training_rows)
    reasoning_rows = reasoning_sft_rows(training_rows)
    write_jsonl(out / "answer_sft.jsonl", answer_rows)
    write_jsonl(out / "reasoning_sft.jsonl", reasoning_rows)
    ablations = ablation_sft_groups(training_rows)
    scaling = scaling_sft_groups(training_rows, scaling_sizes)
    for name, group_rows in ablations.items():
        write_jsonl(out / "ablations" / f"{name}.jsonl", group_rows)
    for name, group_rows in scaling.items():
        write_jsonl(out / "scaling" / f"{name}.jsonl", group_rows)
    report = {
        "input_rows": len(rows),
        "training_rows": len(training_rows),
        "excluded_calibration_or_noncritical_rows": len(rows) - len(training_rows),
        "excluded_calibration_noncritical_or_quarantined_rows": len(rows) - len(training_rows),
        "include_calibration": False,
        "answer_sft_rows": len(answer_rows),
        "reasoning_sft_rows": len(reasoning_rows),
        "ablation_groups": {name: len(group_rows) for name, group_rows in ablations.items()},
        "scaling_groups": {name: len(group_rows) for name, group_rows in scaling.items()},
    }
    report["training_readiness"] = training_readiness_report(rows, training_rows)
    report["input_balance"] = release_balance_report(rows)
    report["training_balance"] = release_balance_report(training_rows)
    report["training_stop_gates"] = {
        "geometry_critical_dominance": report["training_readiness"]["passes_geometry_critical_dominance"],
        "prompt_family_balance": report["training_balance"]["passes_prompt_family_balance"],
        "prompt_template_balance": report["training_balance"]["passes_prompt_template_balance"],
        "answer_entropy": report["training_balance"]["passes_answer_entropy"],
        "geometry_hop_coverage": report["training_balance"]["passes_geometry_hop_coverage"],
        "syntax_only_calibration_cap": report["training_balance"]["passes_syntax_only_calibration_cap"],
    }
    report["blocking_training_gates"] = [
        name
        for name, passed in report["training_stop_gates"].items()
        if passed is False
    ]
    report["valid_for_training"] = not report["blocking_training_gates"]
    report["enforced_training_gates"] = False
    write_json(out / "sft_report.json", report)
    return report


def run_artifact_manifest(run_dir: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        if path.name.endswith(".tar.gz"):
            continue
        payload = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(run_dir).as_posix(),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return {
        "run_dir": str(run_dir),
        "file_count": len(files),
        "total_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }


def package_run_artifacts(run_dir: Path, package_path: Path | None = None) -> dict[str, Any]:
    if not run_dir.exists():
        raise FileNotFoundError(run_dir)
    package_path = package_path or run_dir.with_suffix(".tar.gz")
    manifest = run_artifact_manifest(run_dir)
    write_json(run_dir / "artifact_manifest.json", manifest)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(package_path, "w:gz") as archive:
        for item in sorted(path for path in run_dir.rglob("*") if path.is_file()):
            if item.resolve() == package_path.resolve():
                continue
            archive.add(item, arcname=f"{run_dir.name}/{item.relative_to(run_dir).as_posix()}")
    payload = package_path.read_bytes()
    return {
        "package": str(package_path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "manifest_file_count": manifest["file_count"],
        "manifest_total_bytes": manifest["total_bytes"],
    }
