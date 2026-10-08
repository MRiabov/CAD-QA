"""Closed-book LLM model evaluation reports."""

from __future__ import annotations

from collections import Counter
from typing import Any

from cad_qa.dataset.public import public_private_audit
from cad_qa.evaluation.grade import grade_public_private


HIDDEN_REQUEST_FIELDS = {
    "gold_answer",
    "query_program",
    "candidate_trace",
    "clue_map",
    "verifier_status",
}


def run_closed_book_evaluation(
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    *,
    model_id: str,
    setting: str = "zero-shot",
) -> dict[str, Any]:
    """Grade closed-book responses and audit benchmark-surface hygiene."""

    request_audit = closed_book_request_audit(public_rows, requests)
    key_audit = public_private_audit(public_rows, private_rows)
    grade = grade_public_private(public_rows, private_rows, responses)
    metrics = {key: value for key, value in grade.items() if key != "graded"}
    response_row_ids = {response.get("row_id") for response in responses}
    public_row_ids = {row["row_id"] for row in public_rows}
    return {
        "setting": setting,
        "model_id": model_id,
        "closed_book": True,
        "public_row_count": len(public_rows),
        "private_row_count": len(private_rows),
        "request_count": len(requests),
        "response_count": len(responses),
        "response_coverage": len(public_row_ids & response_row_ids) / len(public_row_ids) if public_row_ids else 0.0,
        "valid": request_audit["valid"] and key_audit["valid"],
        "request_audit": request_audit,
        "public_private_audit": key_audit,
        "metrics": metrics,
        "graded": grade["graded"],
    }


def closed_book_request_audit(
    public_rows: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> dict[str, Any]:
    public_by_id = {row["row_id"]: row for row in public_rows}
    public_ids = set(public_by_id)
    request_ids = [request.get("request_id") for request in requests]
    request_row_ids = [request.get("row_id") for request in requests]
    errors: list[dict[str, Any]] = []
    row_counts = Counter(request_row_ids)
    request_id_counts = Counter(request_ids)
    for request_id, count in sorted(request_id_counts.items(), key=lambda item: str(item[0])):
        if request_id is None:
            errors.append({"error": "missing_request_id", "count": count})
        elif count > 1:
            errors.append({"error": "duplicate_request_id", "request_id": request_id, "count": count})
    for row_id, count in sorted(row_counts.items(), key=lambda item: str(item[0])):
        if row_id is None:
            errors.append({"error": "missing_request_row_id", "count": count})
        elif count > 1:
            errors.append({"error": "duplicate_request_row_id", "row_id": row_id, "count": count})
    missing_requests = sorted(public_ids - {row_id for row_id in request_row_ids if row_id is not None})
    extra_requests = sorted({row_id for row_id in request_row_ids if row_id is not None} - public_ids)
    if missing_requests:
        errors.append({"error": "missing_requests", "row_ids": missing_requests})
    if extra_requests:
        errors.append({"error": "extra_requests", "row_ids": extra_requests})
    for request in requests:
        leaked = sorted(HIDDEN_REQUEST_FIELDS & _nested_keys(request))
        if leaked:
            errors.append({"error": "request_hidden_field_leak", "row_id": request.get("row_id"), "fields": leaked})
        row = public_by_id.get(request.get("row_id"))
        if row is not None and request.get("answer_format") != row.get("answer_format"):
            errors.append(
                {
                    "error": "request_answer_format_mismatch",
                    "row_id": request.get("row_id"),
                    "request_answer_format": request.get("answer_format"),
                    "public_answer_format": row.get("answer_format"),
                }
            )
    return {
        "valid": not errors,
        "public_row_count": len(public_rows),
        "request_count": len(requests),
        "errors": errors,
    }


def _nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_nested_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_nested_keys(item))
        return keys
    return set()
