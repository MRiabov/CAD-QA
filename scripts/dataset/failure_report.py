"""Summarize trace failures and row coverage for a CAD-QA dataset export."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = build_failure_report(args.dataset_dir)
    output = args.output or args.dataset_dir / "failure_report.json"
    write_json(output, report)
    print(report)


def build_failure_report(dataset_dir: Path) -> dict[str, Any]:
    rows = _load_rows(dataset_dir)
    traces = _load_jsonl(dataset_dir / "traces.jsonl")
    failures = _manifest_failures(dataset_dir)
    if not failures:
        failures = [
            _trace_failure_row(trace)
            for trace in traces
            if trace.get("execution_status") != "ok" or trace.get("failure_reason")
        ]

    row_counts_by_source = Counter(str(row.get("source_id")) for row in rows)
    failure_items = [_summarize_failure(row, row_counts_by_source) for row in failures]
    categories = Counter(str(item["category"]) for item in failure_items)
    execution_statuses = Counter(str(item.get("execution_status")) for item in failure_items)
    operation_statuses = Counter(str(item.get("operation_graph_status")) for item in failure_items)

    return {
        "schema": "cadqa_failure_report_v1",
        "source_dataset_dir": str(dataset_dir),
        "trace_count": len(traces),
        "public_row_count": len(rows),
        "failure_count": len(failure_items),
        "status": "pass" if not failure_items else "has_failures",
        "failure_counts_by_category": dict(categories),
        "failure_counts_by_execution_status": dict(execution_statuses),
        "failure_counts_by_operation_graph_status": dict(operation_statuses),
        "row_counts_by_source_for_failed_traces": {
            str(item["source_id"]): item["public_rows_for_source"] for item in failure_items
        },
        "failures": failure_items,
    }


def _load_rows(dataset_dir: Path) -> list[dict[str, Any]]:
    jsonl_dir = dataset_dir / "jsonl"
    rows: list[dict[str, Any]] = []
    for path in sorted(jsonl_dir.glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path) if path.exists() else []


def _manifest_failures(dataset_dir: Path) -> list[dict[str, Any]]:
    return _load_jsonl(dataset_dir / "failure_manifest.jsonl")


def _trace_failure_row(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": trace.get("source_id"),
        "trace_id": trace.get("trace_id"),
        "failure_reason": trace.get("failure_reason"),
        "execution_status": trace.get("execution_status"),
        "operation_graph_status": trace.get("operation_graph_status"),
    }


def _summarize_failure(row: dict[str, Any], row_counts_by_source: Counter[str]) -> dict[str, Any]:
    reason = str(row.get("failure_reason") or "")
    source_id = str(row.get("source_id"))
    return {
        "source_id": row.get("source_id"),
        "trace_id": row.get("trace_id"),
        "category": _failure_category(reason, row),
        "failure_reason": row.get("failure_reason"),
        "execution_status": row.get("execution_status"),
        "operation_graph_status": row.get("operation_graph_status"),
        "public_rows_for_source": row_counts_by_source[source_id],
    }


def _failure_category(reason: str, row: dict[str, Any]) -> str:
    text = f"{reason} {row.get('execution_status')} {row.get('operation_graph_status')}".lower()
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "safety" in text or "unsafe" in text or "forbidden" in text:
        return "static_safety"
    if "import" in text or "module" in text:
        return "import_or_dependency"
    if "no result" in text or "missing result" in text:
        return "missing_result"
    if "operation" in text and "graph" in text:
        return "operation_graph"
    if "exception" in text or "trace_failed" in text or "execution" in text:
        return "execution_error"
    return "unknown"


if __name__ == "__main__":
    main()
