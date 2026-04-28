"""Command line interface for CAD-QA."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
import sys

from cad_qa.baselines import baseline_predictions, evaluate_predictions, run_baselines
from cad_qa.config import DatasetConfig, load_config
from cad_qa.export import export_dataset, export_smoke_dataset
from cad_qa.fixtures import smoke_traces
from cad_qa.jsonio import read_jsonl, write_json, write_jsonl
from cad_qa.materialize import materialize_rows, rows_to_dicts
from cad_qa.schema import SourceRecord
from cad_qa.source import find_adjacent_source_dir, load_source_archive, load_source_dir
from cad_qa.trace import trace_source_records_bounded
from cad_qa.validation import validate_dataset_dir, validate_record_file


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
    parser = argparse.ArgumentParser(prog="cadqa", description="CAD-QA dataset tools")
    subparsers = parser.add_subparsers(required=True)

    smoke = subparsers.add_parser("smoke", help="generate deterministic synthetic smoke dataset")
    smoke.add_argument("--config", type=Path)
    smoke.add_argument("--output-dir", type=Path, required=True)
    smoke.set_defaults(func=_cmd_smoke)

    generate = subparsers.add_parser("generate", help="generate dataset from CADEvolve sources")
    generate.add_argument("--config", type=Path)
    generate.add_argument("--source-dir", type=Path)
    generate.add_argument("--source-archive", type=Path)
    generate.add_argument("--auto-source-dir", action="store_true")
    generate.add_argument("--output-dir", type=Path, required=True)
    generate.add_argument("--limit", type=int)
    generate.add_argument("--offset", type=int, default=0)
    generate.add_argument("--workers", type=int)
    generate.add_argument("--trace-timeout-seconds", type=float)
    generate.add_argument("--cache-dir", type=Path)
    generate.set_defaults(func=_cmd_generate)

    trace = subparsers.add_parser("trace", help="write source and trace records from CADEvolve sources")
    trace.add_argument("--config", type=Path)
    trace.add_argument("--source-dir", type=Path)
    trace.add_argument("--source-archive", type=Path)
    trace.add_argument("--auto-source-dir", action="store_true")
    trace.add_argument("--output-dir", type=Path, required=True)
    trace.add_argument("--limit", type=int)
    trace.add_argument("--offset", type=int, default=0)
    trace.add_argument("--workers", type=int)
    trace.add_argument("--trace-timeout-seconds", type=float)
    trace.add_argument("--cache-dir", type=Path)
    trace.set_defaults(func=_cmd_trace)

    materialize = subparsers.add_parser("materialize-smoke", help="write public rows for smoke traces only")
    materialize.add_argument("--config", type=Path)
    materialize.add_argument("--output", type=Path, required=True)
    materialize.set_defaults(func=_cmd_materialize_smoke)

    validate = subparsers.add_parser("validate", help="validate a dataset dir or JSONL record file")
    validate.add_argument("path", type=Path)
    validate.add_argument("--kind", choices=["dataset", "source", "trace", "row"], default="dataset")
    validate.set_defaults(func=_cmd_validate)

    baseline = subparsers.add_parser("baseline", help="run simple baselines on a row JSONL file")
    baseline.add_argument("rows", type=Path)
    baseline.add_argument("--seed", type=int, default=1234)
    baseline.add_argument("--output-dir", type=Path)
    baseline.set_defaults(func=_cmd_baseline)

    return parser


def _cmd_smoke(args: argparse.Namespace) -> dict[str, object]:
    config = load_config(args.config)
    return export_smoke_dataset(output_dir=args.output_dir, config=config)


def _cmd_generate(args: argparse.Namespace) -> dict[str, object]:
    config = _config_from_args(args)
    sources = _load_sources_from_args(args, config)
    traces = trace_source_records_bounded(sources, config=config, worker_count=args.workers, cache_dir=args.cache_dir)
    pairs = list(zip(sources, traces, strict=True))
    return export_dataset(pairs, output_dir=args.output_dir, config=config)


def _cmd_trace(args: argparse.Namespace) -> dict[str, object]:
    config = _config_from_args(args)
    sources = _load_sources_from_args(args, config)
    traces = trace_source_records_bounded(sources, config=config, worker_count=args.workers, cache_dir=args.cache_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "sources.jsonl", sources)
    write_jsonl(args.output_dir / "traces.jsonl", traces)
    report = {
        "source_count": len(sources),
        "trace_count": len(traces),
        "execution_status_counts": _counts(trace.execution_status for trace in traces),
        "failure_reason_counts": _counts(trace.failure_reason for trace in traces if trace.failure_reason),
    }
    write_json(args.output_dir / "trace_report.json", report)
    return report


def _load_sources_from_args(args: argparse.Namespace, config: DatasetConfig) -> list[SourceRecord]:
    source_dir = args.source_dir
    if args.auto_source_dir and source_dir is None:
        source_dir = find_adjacent_source_dir(Path.cwd())
    if source_dir is not None:
        return load_source_dir(source_dir, config=config, limit=args.limit, offset=args.offset)
    if args.source_archive is not None:
        return load_source_archive(args.source_archive, config=config, limit=args.limit, offset=args.offset)
    raise ValueError("provide --source-dir, --source-archive, or --auto-source-dir")


def _config_from_args(args: argparse.Namespace) -> DatasetConfig:
    config = load_config(args.config)
    timeout = getattr(args, "trace_timeout_seconds", None)
    if timeout is not None:
        config = replace(config, trace_timeout_seconds=timeout)
    return config


def _cmd_materialize_smoke(args: argparse.Namespace) -> dict[str, object]:
    config = load_config(args.config)
    rows = [
        row
        for source, trace in smoke_traces(config)
        for row in materialize_rows(source, trace, config=config)
    ]
    count = write_jsonl(args.output, rows_to_dicts(rows))
    return {"row_count": count, "output": str(args.output)}


def _cmd_validate(args: argparse.Namespace) -> dict[str, object]:
    if args.kind == "dataset":
        return validate_dataset_dir(args.path)
    return validate_record_file(args.path, args.kind)


def _cmd_baseline(args: argparse.Namespace) -> dict[str, object]:
    rows = read_jsonl(args.rows)
    metrics = run_baselines(rows, seed=args.seed)
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.output_dir / "baseline_metrics.json", metrics)
        for name in metrics:
            predictions = baseline_predictions(rows, name=name, seed=args.seed)
            write_json(args.output_dir / f"{name}_predictions.json", predictions)
            write_json(args.output_dir / f"{name}_graded.json", evaluate_predictions(rows, predictions))
    return metrics


def _counts(values: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:  # type: ignore[union-attr]
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


if __name__ == "__main__":
    raise SystemExit(main())
