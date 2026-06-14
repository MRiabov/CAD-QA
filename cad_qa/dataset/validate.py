"""Dataset row validation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.io import existing_record_artifact_path, read_records, write_json
from cad_qa.prompts.wording_gates import (
    banned_terms,
    clue_breadth_violations,
    clue_map_traceability_errors,
    geometry_first_prompt_policy_issues,
)

REQUIRED_ROW_FIELDS = {
    "row_id",
    "source_id",
    "source_code",
    "prompt",
    "answer_format",
    "gold_answer",
    "query_program",
    "candidate_trace",
    "relation_families",
    "measurement_scopes",
    "logical_hop_count",
    "static_hop_count",
    "geometry_hop_count",
    "difficulty_bucket",
    "verifier_status",
    "evidence_tier",
    "release_ready",
    "quarantine_reasons",
}


def validate_rows(rows: list[dict[str, Any]], *, release: bool = False) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    row_id_counts = Counter(row.get("row_id") for row in rows)
    for index, row in enumerate(rows):
        missing = sorted(REQUIRED_ROW_FIELDS - set(row))
        if missing:
            errors.append({"index": index, "row_id": row.get("row_id"), "missing": missing})
        row_id = row.get("row_id")
        if row_id is None:
            errors.append({"index": index, "row_id": row_id, "error": "missing_row_id"})
        elif row_id_counts[row_id] > 1:
            errors.append({"index": index, "row_id": row_id, "error": "duplicate_row_id"})
        if row.get("verifier_status") != "resolved":
            errors.append({"index": index, "row_id": row.get("row_id"), "error": "unresolved_row"})
        if not row.get("candidate_trace", {}).get("final_candidates"):
            errors.append({"index": index, "row_id": row.get("row_id"), "error": "empty_candidate_trace"})
        if len(row.get("clue_map", [])) == 0:
            errors.append({"index": index, "row_id": row.get("row_id"), "error": "missing_clue_map"})
        for clue_error in clue_map_traceability_errors(row):
            errors.append({"index": index, "row_id": row.get("row_id"), **clue_error})
        for violation in clue_breadth_violations(row):
            errors.append({"index": index, "row_id": row.get("row_id"), "error": "clue_too_narrow", **violation})
        terms = banned_terms(str(row.get("prompt", "")))
        if terms:
            errors.append({"index": index, "row_id": row.get("row_id"), "error": "banned_prompt_terms", "terms": terms})
        for issue in public_answer_identity_leak_issues(row):
            item = {"index": index, "row_id": row.get("row_id"), **issue}
            if release:
                errors.append(item)
            else:
                warnings.append({**item, "warning": issue["error"]})
        for issue in geometry_first_prompt_policy_issues(row):
            item = {
                "index": index,
                "row_id": row.get("row_id"),
                "prompt_policy_issue": issue["issue"],
                **issue,
            }
            if release and issue["severity"] == "error":
                errors.append({**item, "error": "geometry_first_prompt_policy"})
            else:
                warnings.append({**item, "warning": "geometry_first_prompt_policy"})
        if row.get("release_ready") is False:
            item = {
                "index": index,
                "row_id": row.get("row_id"),
                "warning": "quarantined_row",
                "reasons": row.get("quarantine_reasons", []),
            }
            if release:
                errors.append({**item, "error": "not_release_ready"})
            else:
                warnings.append(item)
    return {"valid": not errors, "row_count": len(rows), "errors": errors, "warnings": warnings}


def public_answer_identity_leak_issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return public-answer contract issues for real CAD-QA prompt rows."""

    prompt = str(row.get("prompt") or "")
    is_cadqa_prompt = "Given the CadQuery script" in prompt or "Return exactly one entity_id." in prompt
    is_benchmark_row = row.get("difficulty_bucket") == "cad_browsecomp" or int(row.get("logical_hop_count") or 0) >= 3
    if not is_cadqa_prompt or not is_benchmark_row:
        return []
    issues: list[dict[str, Any]] = []
    if row.get("answer_format") == "entity_id" or "Return exactly one entity_id." in prompt:
        issues.append(
            {
                "error": "public_internal_id_answer_contract",
                "answer_format": row.get("answer_format"),
            }
        )
    gold_answer = row.get("gold_answer")
    if isinstance(gold_answer, str) and ":" in gold_answer:
        issues.append(
            {
                "error": "public_internal_id_gold_answer",
                "answer_format": row.get("answer_format"),
            }
        )
    return issues


def validate_dataset_dir(path: Path, *, release: bool = False) -> dict[str, Any]:
    row_path = existing_record_artifact_path(path, "rows")
    rows = read_records(row_path)
    report = validate_rows(rows, release=release)
    output_name = "release_validation_report.json" if release else "validation_report.json"
    write_json(path / output_name, report)
    return report
