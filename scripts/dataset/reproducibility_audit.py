"""Compare two CAD-QA dataset exports for deterministic reproducibility."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_json
from cad_qa.jsonio import read_json, read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left_dataset_dir", type=Path)
    parser.add_argument("right_dataset_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = compare_dataset_exports(args.left_dataset_dir, args.right_dataset_dir)
    output = args.output or Path("reproducibility_audit.json")
    write_json(output, report)
    print(report)
    if report["status"] != "pass":
        raise SystemExit(1)


def compare_dataset_exports(left_dir: Path, right_dir: Path) -> dict[str, Any]:
    left_rows = _load_rows_by_id(left_dir)
    right_rows = _load_rows_by_id(right_dir)
    left_sources = _load_records_by_key(left_dir / "sources.jsonl", "source_id")
    right_sources = _load_records_by_key(right_dir / "sources.jsonl", "source_id")
    left_traces = _load_records_by_key(left_dir / "traces.jsonl", "trace_id")
    right_traces = _load_records_by_key(right_dir / "traces.jsonl", "trace_id")

    row_diff = _diff_record_maps(left_rows, right_rows)
    source_diff = _diff_record_maps(left_sources, right_sources)
    trace_diff = _diff_record_maps(left_traces, right_traces)
    metadata_diff = _metadata_diff(left_dir, right_dir)
    split_diff = _split_membership_diff(left_rows, right_rows)
    failures = [row_diff, source_diff, trace_diff, metadata_diff, split_diff]
    status = "pass" if all(not item["changed"] for item in failures) else "fail"
    return {
        "schema": "cadqa_reproducibility_audit_v1",
        "status": status,
        "left_dataset_dir": str(left_dir),
        "right_dataset_dir": str(right_dir),
        "left_counts": _dataset_counts(left_rows),
        "right_counts": _dataset_counts(right_rows),
        "row_diff": row_diff,
        "source_diff": source_diff,
        "trace_diff": trace_diff,
        "metadata_diff": metadata_diff,
        "split_membership_diff": split_diff,
    }


def _load_rows_by_id(dataset_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted((dataset_dir / "jsonl").glob("*.jsonl")):
        for row in read_jsonl(path):
            rows[str(row.get("id"))] = row
    return rows


def _load_records_by_key(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {str(row.get(key)): row for row in read_jsonl(path)}


def _diff_record_maps(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> dict[str, Any]:
    left_ids = set(left)
    right_ids = set(right)
    common = left_ids & right_ids
    changed = sorted(item_id for item_id in common if sha256_json(left[item_id]) != sha256_json(right[item_id]))
    return {
        "changed": bool(left_ids ^ right_ids or changed),
        "left_count": len(left),
        "right_count": len(right),
        "missing_from_right": sorted(left_ids - right_ids)[:100],
        "missing_from_left": sorted(right_ids - left_ids)[:100],
        "content_mismatches": changed[:100],
        "truncated": len(left_ids ^ right_ids) > 100 or len(changed) > 100,
    }


def _metadata_diff(left_dir: Path, right_dir: Path) -> dict[str, Any]:
    comparable_keys = {
        "schema",
        "dataset_name",
        "dataset_version",
        "row_count",
        "source_count",
        "trace_count",
        "row_counts_by_split",
        "row_counts_by_task_type",
        "source_manifest_hash",
        "generation_config_hash",
        "label_policy",
        "leakage_audit",
    }
    left = _read_json_if_exists(left_dir / "metadata.json")
    right = _read_json_if_exists(right_dir / "metadata.json")
    mismatches = [
        key
        for key in sorted(comparable_keys)
        if left.get(key) != right.get(key)
    ]
    return {
        "changed": bool(mismatches),
        "compared_keys": sorted(comparable_keys),
        "mismatched_keys": mismatches,
        "left_metadata_exists": bool(left),
        "right_metadata_exists": bool(right),
    }


def _split_membership_diff(
    left_rows: dict[str, dict[str, Any]],
    right_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    common = set(left_rows) & set(right_rows)
    mismatches = sorted(
        row_id
        for row_id in common
        if left_rows[row_id].get("split") != right_rows[row_id].get("split")
    )
    return {
        "changed": bool(mismatches),
        "split_mismatches": mismatches[:100],
        "truncated": len(mismatches) > 100,
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = read_json(path)
    return value if isinstance(value, dict) else {}


def _dataset_counts(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "row_count": len(rows),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows.values())),
        "row_counts_by_task_type": dict(Counter(str(row.get("task_type")) for row in rows.values())),
    }


if __name__ == "__main__":
    main()
