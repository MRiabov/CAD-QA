"""Cross-package ``cadqa`` command line interface.

The dataset-generation commands are registered by :mod:`dataset.cli`; this
module adds the evaluation and experiment commands and provides the ``cadqa``
entry point that combines both.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from dataset import cli as dataset_cli
from dataset.io import read_records, write_json, write_jsonl, write_records
from train_and_eval.experiment import (
    package_run_artifacts,
    run_artifact_manifest,
    run_smoke_experiment,
    write_paper_results,
)
from train_and_eval.grading.baselines import run_baselines
from train_and_eval.grading.no_cadquery_access import run_no_cadquery_access_evaluation
from train_and_eval.grading.grade import grade_public_private, grade_responses
from train_and_eval.grading.requests import few_shot_requests, oracle_responses, zero_shot_requests
from train_and_eval.grading.tool_assisted import run_tool_assisted_upper_bound
from train_and_eval.harbor import export_harbor_atif


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
    harbor_sub = dataset_cli.register_commands(subparsers)
    register_commands(subparsers, harbor_sub=harbor_sub)
    return parser


def register_commands(subparsers: Any, *, harbor_sub: Any | None = None) -> None:
    _register_evaluation(subparsers)
    _register_experiment(subparsers)
    if harbor_sub is not None:
        _register_harbor_runner(harbor_sub)


def _register_evaluation(subparsers: Any) -> None:
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
    no_cadquery_access = evaluation_sub.add_parser("no-cadquery-access")
    no_cadquery_access.add_argument("--public", type=Path, required=True)
    no_cadquery_access.add_argument("--private", type=Path, required=True)
    no_cadquery_access.add_argument("--requests", type=Path, required=True)
    no_cadquery_access.add_argument("--responses", type=Path, required=True)
    no_cadquery_access.add_argument("--out", type=Path, required=True)
    no_cadquery_access.add_argument("--model-id", required=True)
    no_cadquery_access.add_argument("--setting", default="zero-shot")
    no_cadquery_access.set_defaults(func=_cmd_evaluation_no_cadquery_access)
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


def _register_experiment(subparsers: Any) -> None:
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


def _register_harbor_runner(harbor_sub: Any) -> None:
    harbor_atif = harbor_sub.add_parser("export-atif")
    harbor_atif.add_argument("--responses", type=Path, required=True)
    harbor_atif.add_argument("--public", type=Path, required=True)
    harbor_atif.add_argument("--private", type=Path, required=True)
    harbor_atif.add_argument("--out", type=Path, required=True)
    harbor_atif.set_defaults(func=_cmd_harbor_export_atif)


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


def _cmd_evaluation_no_cadquery_access(args: argparse.Namespace) -> dict[str, Any]:
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
    requests = read_records(args.requests)
    responses = read_records(args.responses)
    result = run_no_cadquery_access_evaluation(
        public_rows,
        private_rows,
        requests,
        responses,
        model_id=args.model_id,
        setting=args.setting,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    report = {key: value for key, value in result.items() if key != "graded"}
    write_json(args.out / "no_cadquery_access_report.json", report)
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


def _cmd_harbor_export_atif(args: argparse.Namespace) -> dict[str, Any]:
    responses = read_records(args.responses)
    public_rows = read_records(args.public)
    private_rows = read_records(args.private)
    return export_harbor_atif(responses, public_rows, private_rows, args.out)


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


if __name__ == "__main__":
    raise SystemExit(main())
