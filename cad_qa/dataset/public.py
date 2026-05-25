"""Public/private row views for benchmark release artifacts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.io import record_artifact_path, write_json, write_records


PUBLIC_FIELDS = {
    "row_id",
    "source_id",
    "source_code",
    "prompt",
    "answer_format",
    "relation_families",
    "measurement_scopes",
    "logical_hop_count",
    "static_hop_count",
    "geometry_hop_count",
    "difficulty_bucket",
    "prompt_version",
    "prompt_template_id",
    "evidence_tier",
    "release_ready",
    "quarantine_reasons",
    "split",
}

PRIVATE_FIELDS = {
    "row_id",
    "source_id",
    "answer_format",
    "gold_answer",
    "query_program",
    "candidate_trace",
    "clue_map",
    "verifier_status",
    "split",
}


def public_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_select_fields(row, PUBLIC_FIELDS) for row in rows]


def private_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_select_fields(row, PRIVATE_FIELDS) for row in rows]


def write_public_private_artifacts(rows: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    public = public_rows(rows)
    private = private_rows(rows)
    write_records(record_artifact_path(out, "public"), public)
    write_records(record_artifact_path(out, "private"), private)
    public_split_counts: dict[str, int] = {}
    for row in public:
        public_split_counts[row.get("split", "unsplit")] = public_split_counts.get(row.get("split", "unsplit"), 0) + 1
    report = {
        "public_row_count": len(public),
        "private_row_count": len(private),
        "public_fields": sorted(PUBLIC_FIELDS),
        "private_fields": sorted(PRIVATE_FIELDS),
        "public_split_counts": dict(sorted(public_split_counts.items())),
        "audit": public_private_audit(public, private),
    }
    write_json(out / "public_private_report.json", report)
    return report


def public_private_audit(public: list[dict[str, Any]], private: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    public_ids = [row.get("row_id") for row in public]
    private_ids = [row.get("row_id") for row in private]
    public_counts = Counter(public_ids)
    private_counts = Counter(private_ids)
    for row_id, count in sorted(public_counts.items()):
        if row_id is None:
            errors.append({"error": "public_missing_row_id", "count": count})
        elif count > 1:
            errors.append({"error": "duplicate_public_row_id", "row_id": row_id, "count": count})
    for row_id, count in sorted(private_counts.items()):
        if row_id is None:
            errors.append({"error": "private_missing_row_id", "count": count})
        elif count > 1:
            errors.append({"error": "duplicate_private_row_id", "row_id": row_id, "count": count})
    public_id_set = {row_id for row_id in public_ids if row_id is not None}
    private_id_set = {row_id for row_id in private_ids if row_id is not None}
    missing_private = sorted(public_id_set - private_id_set)
    missing_public = sorted(private_id_set - public_id_set)
    if missing_private:
        errors.append({"error": "missing_private_rows", "row_ids": missing_private})
    if missing_public:
        errors.append({"error": "missing_public_rows", "row_ids": missing_public})

    hidden_public_fields = PRIVATE_FIELDS - {"row_id", "source_id", "answer_format", "split"}
    for row in public:
        leaked = sorted(hidden_public_fields & set(row))
        if leaked:
            errors.append({"error": "public_hidden_field_leak", "row_id": row.get("row_id"), "fields": leaked})
    required_private_fields = {"row_id", "source_id", "answer_format", "gold_answer", "query_program", "candidate_trace"}
    for row in private:
        missing = sorted(required_private_fields - set(row))
        if missing:
            errors.append({"error": "private_missing_required_fields", "row_id": row.get("row_id"), "fields": missing})

    return {
        "valid": not errors,
        "public_row_count": len(public),
        "private_row_count": len(private),
        "errors": errors,
    }


def _select_fields(row: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    return {field: row[field] for field in sorted(fields) if field in row}
