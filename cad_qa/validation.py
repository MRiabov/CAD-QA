"""Dataset validation utilities."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_jsonl
from cad_qa.schema import (
    validate_public_row,
    validate_source_record,
    validate_trace_record,
)
from cad_qa.splits import leakage_audit


def validate_dataset_dir(dataset_dir: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    jsonl_dir = dataset_dir / "jsonl"
    if not jsonl_dir.exists():
        errors.append({"path": str(jsonl_dir), "error": "missing jsonl directory"})
    else:
        for path in sorted(jsonl_dir.glob("*.jsonl")):
            file_rows = read_jsonl(path)
            for index, row in enumerate(file_rows, start=1):
                row_errors = validate_public_row(row)
                if row_errors:
                    errors.append(
                        {"path": str(path), "line": index, "errors": row_errors}
                    )
            rows.extend(file_rows)
    errors.extend(_duplicate_id_errors(rows))
    audit = leakage_audit(rows)
    if audit["status"] != "pass":
        errors.append(
            {
                "path": str(dataset_dir / "split_manifest.json"),
                "errors": audit["violations"],
            }
        )
    return {
        "status": "pass" if not errors else "fail",
        "row_count": len(rows),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
        "row_counts_by_task_type": dict(
            Counter(str(row.get("task_type")) for row in rows)
        ),
        "row_counts_by_requires": dict(
            Counter(tag for row in rows for tag in _list_field(row, "requires"))
        ),
        "row_counts_by_difficulty_tag": dict(
            Counter(tag for row in rows for tag in _list_field(row, "difficulty_tags"))
        ),
        "errors": errors,
        "leakage_audit": audit,
    }


def validate_record_file(path: Path, kind: str) -> dict[str, Any]:
    rows = read_jsonl(path)
    validators = {
        "source": validate_source_record,
        "trace": validate_trace_record,
        "row": validate_public_row,
    }
    validator = validators[kind]
    errors = []
    for index, row in enumerate(rows, start=1):
        row_errors = validator(row)
        if row_errors:
            errors.append({"line": index, "errors": row_errors})
    return {
        "status": "pass" if not errors else "fail",
        "count": len(rows),
        "errors": errors,
    }


def _duplicate_id_errors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_id[str(row.get("id"))].append(str(row.get("split")))
    return [
        {"row_id": row_id, "error": "duplicate row id", "splits": splits}
        for row_id, splits in sorted(by_id.items())
        if row_id and len(splits) > 1
    ]


def _list_field(row: dict[str, Any], key: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
