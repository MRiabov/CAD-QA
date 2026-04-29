"""Create a deterministic stratified sample for human CAD-QA label audit."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_text
from cad_qa.jsonio import read_jsonl, write_json, write_jsonl


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rows-per-bucket", type=int, default=2)
    parser.add_argument("--max-rows", type=int, default=200)
    parser.add_argument("--failure-rows", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sample, report = build_audit_sample(
        args.dataset_dir,
        rows_per_bucket=args.rows_per_bucket,
        max_rows=args.max_rows,
        failure_rows=args.failure_rows,
        seed=args.seed,
    )
    write_jsonl(args.output_dir / "manual_audit_sample.jsonl", sample)
    write_json(args.output_dir / "manual_audit_report.json", report)
    print(report)


def build_audit_sample(
    dataset_dir: Path,
    *,
    rows_per_bucket: int = 2,
    max_rows: int = 200,
    failure_rows: int = 50,
    seed: int = 1234,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _load_rows(dataset_dir)
    failures = _load_failures(dataset_dir)

    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[(str(row.get("split")), str(row.get("task_type")))].append(row)

    selected: list[dict[str, Any]] = []
    for (split, task_type), bucket_rows in sorted(buckets.items()):
        ordered = sorted(bucket_rows, key=lambda row: _stable_order_key(seed, row))
        for row in ordered[:rows_per_bucket]:
            selected.append(_audit_row(row, split=split, task_type=task_type))

    selected = sorted(selected, key=lambda item: str(item["audit_id"]))[:max_rows]
    failure_sample = [
        _failure_row(failure)
        for failure in sorted(failures, key=lambda row: _stable_order_key(seed, row))[
            :failure_rows
        ]
    ]
    sample = selected + failure_sample
    report = {
        "schema": "cadqa_manual_audit_report_v1",
        "source_dataset_dir": str(dataset_dir),
        "seed": seed,
        "rows_per_bucket": rows_per_bucket,
        "max_rows": max_rows,
        "failure_rows": failure_rows,
        "input_row_count": len(rows),
        "input_failure_count": len(failures),
        "sample_row_count": len(sample),
        "label_sample_count": len(selected),
        "failure_sample_count": len(failure_sample),
        "input_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
        "input_counts_by_task_type": dict(
            Counter(str(row.get("task_type")) for row in rows)
        ),
        "sample_counts_by_kind": dict(
            Counter(str(row.get("audit_kind")) for row in sample)
        ),
        "sample_counts_by_split": dict(
            Counter(str(row.get("split")) for row in selected)
        ),
        "sample_counts_by_task_type": dict(
            Counter(str(row.get("task_type")) for row in selected)
        ),
        "sampled_buckets": [
            {"split": split, "task_type": task} for split, task in sorted(buckets)
        ],
    }
    return sample, report


def _load_rows(dataset_dir: Path) -> list[dict[str, Any]]:
    jsonl_dir = dataset_dir / "jsonl"
    rows: list[dict[str, Any]] = []
    for path in sorted(jsonl_dir.glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def _load_failures(dataset_dir: Path) -> list[dict[str, Any]]:
    path = dataset_dir / "failure_manifest.jsonl"
    return read_jsonl(path) if path.exists() else []


def _audit_row(row: dict[str, Any], *, split: str, task_type: str) -> dict[str, Any]:
    return {
        "audit_id": f"label:{row.get('id')}",
        "audit_kind": "label",
        "row_id": row.get("id"),
        "split": split,
        "task_type": task_type,
        "source_id": row.get("source_id"),
        "trace_id": row.get("trace_id"),
        "target_feature_id": row.get("target_feature_id"),
        "prompt": row.get("prompt"),
        "answer_type": row.get("answer_type"),
        "answer": row.get("answer"),
        "choices": row.get("choices"),
        "unit": row.get("unit"),
        "numeric_tolerance": row.get("numeric_tolerance"),
        "requires": row.get("requires", []),
        "difficulty_tags": row.get("difficulty_tags", []),
        "labels": row.get("labels", {}),
        "diagnostics": row.get("diagnostics", {}),
        "provenance": row.get("provenance", {}),
        "audit_fields": {
            "prompt_correct": None,
            "answer_correct": None,
            "requires_correct": None,
            "notes": "",
        },
    }


def _failure_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": f"failure:{row.get('trace_id') or row.get('source_id')}",
        "audit_kind": "trace_failure",
        "source_id": row.get("source_id"),
        "trace_id": row.get("trace_id"),
        "execution_status": row.get("execution_status"),
        "operation_graph_status": row.get("operation_graph_status"),
        "failure_reason": row.get("failure_reason"),
        "audit_fields": {
            "expected_or_actionable": None,
            "notes": "",
        },
    }


def _stable_order_key(seed: int, row: dict[str, Any]) -> str:
    return sha256_text(
        f"{seed}:{row.get('id')}:{row.get('source_id')}:{row.get('trace_id')}"
    )


if __name__ == "__main__":
    main()
