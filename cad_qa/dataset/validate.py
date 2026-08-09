"""Dataset row validation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re
from typing import Any

from cad_qa.io import existing_record_artifact_path, read_records, write_json
from cad_qa.prompts.wording_gates import (
    banned_terms,
    clue_breadth_violations,
    clue_map_traceability_errors,
    geometry_first_prompt_policy_issues,
)
from cad_qa.query.answers import DEFAULT_MAX_CANDIDATE_LABELS

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
        if row.get("answer_format") == "json":
            # workplane_state json family was pruned (degenerate base="cq" golds);
            # rows in this format are unsupported and must never be re-emitted.
            errors.append({"index": index, "row_id": row.get("row_id"),
                           "error": "unsupported_json_format"})
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
        for issue in public_candidate_label_issues(row):
            item = {"index": index, "row_id": row.get("row_id"), **issue}
            errors.append(item)
        for issue in public_coordinate_answer_issues(row):
            item = {"index": index, "row_id": row.get("row_id"), **issue}
            errors.append(item)
        for issue in public_source_variable_answer_issues(row):
            item = {"index": index, "row_id": row.get("row_id"), **issue}
            errors.append(item)
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


def public_candidate_label_issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return public candidate-list contract issues for real CAD-QA prompt rows."""

    prompt = str(row.get("prompt") or "")
    is_cadqa_prompt = "Given the CadQuery script" in prompt
    if not is_cadqa_prompt or row.get("answer_format") != "candidate_label":
        return []
    issues: list[dict[str, Any]] = []
    candidate_labels = ((row.get("query_program") or {}).get("answer_spec") or {}).get("candidate_labels") or {}
    if len(candidate_labels) > DEFAULT_MAX_CANDIDATE_LABELS:
        issues.append(
            {
                "error": "too_many_public_candidate_labels",
                "candidate_label_count": len(candidate_labels),
                "max_candidate_labels": DEFAULT_MAX_CANDIDATE_LABELS,
            }
        )
    gold_label = _normalized_gold_label(row.get("gold_answer"))
    rendered_label_texts = _rendered_candidate_label_texts(prompt)
    if not rendered_label_texts:
        issues.append({"error": "missing_rendered_candidate_labels"})
    elif gold_label and gold_label not in rendered_label_texts:
        issues.append(
            {
                "error": "gold_candidate_label_not_rendered",
                "gold_label": gold_label,
                "rendered_labels": sorted(rendered_label_texts),
            }
        )
    duplicate_gold = _duplicated_gold_candidate_description_issue(row)
    if duplicate_gold is not None:
        issues.append(duplicate_gold)
    return issues


def public_coordinate_answer_issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return public coordinate-answer contract issues for CAD-QA prompt rows."""

    prompt = str(row.get("prompt") or "")
    if "Given the CadQuery script" not in prompt or row.get("answer_format") != "coordinate":
        return []
    issues: list[dict[str, Any]] = []
    if "coordinate tuple" not in prompt:
        issues.append({"error": "missing_coordinate_tuple_return_instruction"})
    coordinate = _normalized_coordinate_answer(row.get("gold_answer"))
    if coordinate is None:
        issues.append(
            {
                "error": "invalid_coordinate_gold_answer",
                "gold_answer": row.get("gold_answer"),
            }
        )
    return issues


def public_source_variable_answer_issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return public source-variable answer contract issues for CAD-QA prompt rows."""

    prompt = str(row.get("prompt") or "")
    if (
        "Given the CadQuery script" not in prompt
        or row.get("answer_format") != "text"
        or "source variable name" not in prompt
    ):
        return []
    answer = _normalized_gold_label(row.get("gold_answer"))
    if not answer:
        return [{"error": "invalid_source_variable_gold_answer", "gold_answer": row.get("gold_answer")}]
    assignment_count = _source_assignment_counts(str(row.get("source_code") or "")).get(answer, 0)
    if assignment_count == 0:
        return [{"error": "source_variable_gold_answer_not_assigned", "gold_answer": answer}]
    if assignment_count > 1:
        return [
            {
                "error": "source_variable_gold_answer_reassigned",
                "gold_answer": answer,
                "assignment_count": assignment_count,
            }
        ]
    return []


def _duplicated_gold_candidate_description_issue(row: dict[str, Any]) -> dict[str, Any] | None:
    gold_label = _normalized_gold_label(row.get("gold_answer"))
    if not gold_label:
        return None
    label_texts = _rendered_candidate_label_texts(str(row.get("prompt") or ""))
    if gold_label not in label_texts:
        return None
    duplicate_labels = sorted(
        label for label, text in label_texts.items()
        if text == label_texts[gold_label]
    )
    if len(duplicate_labels) <= 1:
        return None
    return {
        "error": "duplicated_gold_candidate_description",
        "gold_label": gold_label,
        "duplicate_labels": duplicate_labels,
        "candidate_description": label_texts[gold_label],
    }


def _normalized_gold_label(gold_answer: Any) -> str | None:
    if not isinstance(gold_answer, str):
        return None
    try:
        decoded = json.loads(gold_answer)
    except json.JSONDecodeError:
        decoded = gold_answer
    return decoded if isinstance(decoded, str) else None


def _normalized_coordinate_answer(gold_answer: Any) -> list[float] | None:
    value = gold_answer
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        return [float(component) for component in value]
    except (TypeError, ValueError):
        return None


def _source_assignment_counts(source_code: str) -> Counter[str]:
    assignment_counts: Counter[str] = Counter()
    pattern = re.compile(r"^\s*([A-Za-z_]\w*)\s*=")
    for line in source_code.splitlines():
        match = pattern.match(line)
        if match:
            assignment_counts[match.group(1)] += 1
    return assignment_counts


def _rendered_candidate_label_texts(prompt: str) -> dict[str, str]:
    label_texts = {}
    pattern = re.compile(r"^- ([A-Z]+): (.*)$")
    for line in prompt.splitlines():
        match = pattern.match(line.strip())
        if match:
            label_texts[match.group(1)] = match.group(2).strip()
    return label_texts


def validate_dataset_dir(path: Path, *, release: bool = False) -> dict[str, Any]:
    row_path = existing_record_artifact_path(path, "rows")
    rows = read_records(row_path)
    report = validate_rows(rows, release=release)
    output_name = "release_validation_report.json" if release else "validation_report.json"
    write_json(path / output_name, report)
    return report
