"""Evaluate CAD-QA experiment canary stop gates from generated reports."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_json, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-stats", type=Path, required=True)
    parser.add_argument("--failure-report", type=Path)
    parser.add_argument("--sft-smoke-report", type=Path)
    parser.add_argument("--experiment-comparison", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--max-trace-failure-rate", type=float, default=0.5)
    args = parser.parse_args(argv)

    report = evaluate_stop_gates(
        dataset_stats_path=args.dataset_stats,
        failure_report_path=args.failure_report,
        sft_smoke_report_path=args.sft_smoke_report,
        experiment_comparison_path=args.experiment_comparison,
        min_rows=args.min_rows,
        max_trace_failure_rate=args.max_trace_failure_rate,
    )
    write_json(args.output, report)
    print(report)
    if report["status"] != "pass":
        raise SystemExit(1)


def evaluate_stop_gates(
    *,
    dataset_stats_path: Path,
    failure_report_path: Path | None = None,
    sft_smoke_report_path: Path | None = None,
    experiment_comparison_path: Path | None = None,
    min_rows: int = 1,
    max_trace_failure_rate: float = 0.5,
) -> dict[str, Any]:
    gates = [
        _dataset_gate(dataset_stats_path, min_rows=min_rows),
    ]
    if failure_report_path is not None:
        gates.append(
            _failure_gate(
                failure_report_path, max_trace_failure_rate=max_trace_failure_rate
            )
        )
    if sft_smoke_report_path is not None:
        gates.append(
            _status_gate("sft_smoke", sft_smoke_report_path, passing_statuses={"pass"})
        )
    if experiment_comparison_path is not None:
        gates.append(
            _status_gate(
                "experiment_comparison",
                experiment_comparison_path,
                passing_statuses={"pass"},
            )
        )
    return {
        "schema": "cadqa_stop_gate_report_v1",
        "status": "pass" if all(gate["status"] == "pass" for gate in gates) else "fail",
        "gates": gates,
    }


def _dataset_gate(path: Path, *, min_rows: int) -> dict[str, Any]:
    payload = read_json(path)
    row_count = int(payload.get("row_count", 0))
    passed = payload.get("status") == "pass" and row_count >= min_rows
    return {
        "name": "dataset_validation",
        "status": "pass" if passed else "fail",
        "path": str(path),
        "observed_status": payload.get("status"),
        "row_count": row_count,
        "min_rows": min_rows,
    }


def _failure_gate(path: Path, *, max_trace_failure_rate: float) -> dict[str, Any]:
    payload = read_json(path)
    trace_count = int(payload.get("trace_count", 0))
    failure_count = int(payload.get("failure_count", 0))
    failure_rate = failure_count / trace_count if trace_count else 0.0
    passed = failure_rate <= max_trace_failure_rate
    return {
        "name": "trace_failure_rate",
        "status": "pass" if passed else "fail",
        "path": str(path),
        "trace_count": trace_count,
        "failure_count": failure_count,
        "failure_rate": failure_rate,
        "max_trace_failure_rate": max_trace_failure_rate,
    }


def _status_gate(
    name: str, path: Path, *, passing_statuses: set[str]
) -> dict[str, Any]:
    payload = read_json(path)
    observed = str(payload.get("status"))
    return {
        "name": name,
        "status": "pass" if observed in passing_statuses else "fail",
        "path": str(path),
        "observed_status": observed,
        "passing_statuses": sorted(passing_statuses),
    }


if __name__ == "__main__":
    main()
