"""Release dataset export helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.family_test_evidence import DEFAULT_FAMILY_TEST_EVIDENCE
from cad_qa.dataset.preview import DEFAULT_PREVIEW_EVIDENCE_FILENAME
from cad_qa.dataset.public import write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release_report import (
    DEFAULT_RELEASE_TIER,
    _is_cross_feature_value_bearing_row,
    _is_value_bearing_measurement_row,
    release_gate_profile,
    write_release_verifier_report,
)
from cad_qa.dataset.report import dataset_card_markdown, dataset_report, failure_report
from cad_qa.dataset.sft import is_syntax_only_calibration_row
from cad_qa.dataset.split import rows_with_assigned_splits, split_audit, split_manifest
from cad_qa.dataset.validate import validate_dataset_dir, validate_rows
from cad_qa.io import write_json, write_jsonl
from cad_qa.prompts.render import prompt_template_id_from_mapping
from cad_qa.query.family_manifest import DEFAULT_FAMILY_MANIFEST, RELEASE_STATUSES, load_family_manifest


def export_release_dataset(
    rows: list[dict[str, Any]],
    *,
    out: Path,
    source_dataset: Path | None = None,
    allow_failing_release_gates: bool = False,
    release_tier: str = DEFAULT_RELEASE_TIER,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
    preview_evidence: Path | None = None,
    family_test_evidence: Path | None = DEFAULT_FAMILY_TEST_EVIDENCE,
) -> dict[str, Any]:
    profile = release_gate_profile(release_tier)
    release_valid_rows, validation_exclusions = _filter_release_valid_rows(rows)
    release_family_rows, non_release_family_exclusions = _filter_release_family_rows(
        release_valid_rows,
        family_manifest,
        enforce=profile.enforce_intended_family_coverage,
    )
    deduped_rows, duplicate_exclusions = _dedupe_release_prompts(release_family_rows)
    release_rows, calibration_cap_exclusions = _cap_syntax_only_calibration_rows(
        deduped_rows,
        profile.max_syntax_only_calibration_share,
    )
    release_rows, balance_cap_exclusions = _cap_release_balance_rows(release_rows, profile)
    if not release_rows:
        raise ValueError("no release-ready rows found")
    out.mkdir(parents=True, exist_ok=True)
    manifest = split_manifest(release_rows)
    release_rows = rows_with_assigned_splits(release_rows, manifest)
    release_rows = [_with_prompt_template_id(row) for row in release_rows]
    write_jsonl(out / "rows.jsonl", release_rows)
    public_private = write_public_private_artifacts(release_rows, out)
    split_rows: dict[str, list[dict[str, Any]]] = {}
    for row in release_rows:
        split_rows.setdefault(row.get("split", "unsplit"), []).append(row)
    for split, items in sorted(split_rows.items()):
        write_jsonl(out / "jsonl" / f"{split}.jsonl", items)

    write_json(out / "split_manifest.json", manifest)
    report = dataset_report(release_rows)
    report["split_manifest"] = manifest
    if source_dataset is not None:
        report["source_dataset"] = str(source_dataset)
    excluded_quarantine_count = sum(
        1
        for row in rows
        if row.get("release_ready") is False or row.get("quarantine_reasons")
    )
    excluded_prompt_policy_count = sum(
        1
        for exclusion in validation_exclusions
        if any(error.get("error") == "geometry_first_prompt_policy" for error in exclusion["errors"])
    )
    report["excluded_quarantine_count"] = excluded_quarantine_count
    report["excluded_release_validation_count"] = len(validation_exclusions)
    report["excluded_non_release_family_count"] = len(non_release_family_exclusions)
    report["excluded_prompt_policy_count"] = excluded_prompt_policy_count
    report["excluded_duplicate_prompt_count"] = len(duplicate_exclusions)
    report["excluded_syntax_only_calibration_cap_count"] = len(calibration_cap_exclusions)
    report["excluded_release_balance_cap_count"] = len(balance_cap_exclusions)
    write_json(out / "dataset_report.json", report)
    write_json(
        out / "release_exclusions.json",
        {
            "excluded_quarantine_count": excluded_quarantine_count,
            "excluded_release_validation_count": len(validation_exclusions),
            "excluded_non_release_family_count": len(non_release_family_exclusions),
            "excluded_prompt_policy_count": excluded_prompt_policy_count,
            "excluded_duplicate_prompt_count": len(duplicate_exclusions),
            "excluded_syntax_only_calibration_cap_count": len(calibration_cap_exclusions),
            "excluded_release_balance_cap_count": len(balance_cap_exclusions),
            "release_validation_exclusions": validation_exclusions,
            "non_release_family_exclusions": non_release_family_exclusions,
            "duplicate_prompt_exclusions": duplicate_exclusions,
            "syntax_only_calibration_cap_exclusions": calibration_cap_exclusions,
            "release_balance_cap_exclusions": balance_cap_exclusions,
        },
    )

    validation = validate_dataset_dir(out, release=True)
    audit = leakage_audit(release_rows, manifest)
    write_json(out / "leakage_audit.json", audit)
    split_quality = split_audit(release_rows, manifest)
    write_json(out / "split_audit.json", split_quality)
    quarantine = quarantine_report(release_rows)
    write_json(out / "quarantine_report.json", quarantine)
    failures = failure_report([])
    write_json(out / "failure_report.json", failures)
    (out / "DATASET_CARD.md").write_text(
        dataset_card_markdown(
            dataset_path=out,
            report=report,
            validation=validation,
            audit=audit,
            failures=failures,
        ),
        encoding="utf-8",
    )
    verifier_report = write_release_verifier_report(
        out,
        release_tier=profile.name,
        family_manifest=family_manifest,
        preview_evidence=preview_evidence or out / DEFAULT_PREVIEW_EVIDENCE_FILENAME,
        family_test_evidence=family_test_evidence,
    )
    valid = validation["valid"] and audit["valid"] and split_quality["valid"] and verifier_report["valid_for_release"]
    result = {
        "row_count": len(release_rows),
        "excluded_quarantine_count": excluded_quarantine_count,
        "excluded_release_validation_count": len(validation_exclusions),
        "excluded_non_release_family_count": len(non_release_family_exclusions),
        "excluded_prompt_policy_count": excluded_prompt_policy_count,
        "excluded_duplicate_prompt_count": len(duplicate_exclusions),
        "excluded_syntax_only_calibration_cap_count": len(calibration_cap_exclusions),
        "excluded_release_balance_cap_count": len(balance_cap_exclusions),
        "valid": valid,
        "release_tier": profile.name,
        "blocking_release_gates": verifier_report["blocking_gates"],
        "out": str(out),
        "dataset": report,
        "validation": validation,
        "leakage_audit": audit,
        "split_audit": split_quality,
        "quarantine": quarantine,
        "public_private": public_private,
        "verifier_report": verifier_report,
    }
    if not valid and not allow_failing_release_gates:
        raise RuntimeError(f"release gates failed: {verifier_report['blocking_gates']}")
    return result


def _filter_release_valid_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for row in rows:
        validation = validate_rows([row], release=True)
        if validation["valid"]:
            kept.append(row)
            continue
        exclusions.append(
            {
                "row_id": row.get("row_id"),
                "source_id": row.get("source_id"),
                "prompt_family": _prompt_family(row),
                "errors": [
                    {key: value for key, value in error.items() if key not in {"index"}}
                    for error in validation["errors"]
                ],
            }
        )
    return kept, exclusions


def _filter_release_family_rows(
    rows: list[dict[str, Any]],
    family_manifest: Path | None,
    *,
    enforce: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not enforce:
        return rows, []
    manifest = load_family_manifest(family_manifest)
    if not manifest["exists"]:
        return rows, []
    families = manifest["families"]
    release_families = {
        family_id
        for family_id, spec in families.items()
        if spec.get("status") in RELEASE_STATUSES
    }
    kept: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for row in rows:
        family = _prompt_family(row)
        spec = families.get(family)
        if spec is None or family in release_families:
            kept.append(row)
            continue
        exclusions.append(
            {
                "row_id": row.get("row_id"),
                "source_id": row.get("source_id"),
                "prompt_family": family,
                "family_status": spec.get("status"),
                "reason": "non_release_family",
            }
        )
    return kept, exclusions


def _dedupe_release_prompts(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[str, str | None] = {}
    kept: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for row in rows:
        prompt_hash = hashlib.sha256(str(row.get("prompt", "")).encode("utf-8")).hexdigest()
        kept_row_id = seen.get(prompt_hash)
        if kept_row_id is not None:
            exclusions.append(
                {
                    "prompt_hash": prompt_hash,
                    "kept_row_id": kept_row_id,
                    "dropped_row_id": row.get("row_id"),
                }
            )
            continue
        seen[prompt_hash] = row.get("row_id")
        kept.append(row)
    return kept, exclusions


def _cap_syntax_only_calibration_rows(
    rows: list[dict[str, Any]],
    max_share: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    calibration_rows = [row for row in rows if is_syntax_only_calibration_row(row)]
    main_rows = [row for row in rows if not is_syntax_only_calibration_row(row)]
    if not calibration_rows or not main_rows:
        return rows, []
    allowed_count = _allowed_calibration_count(len(main_rows), max_share)
    kept_calibration = sorted(calibration_rows, key=lambda row: str(row.get("row_id")))[:allowed_count]
    excluded_calibration = sorted(calibration_rows, key=lambda row: str(row.get("row_id")))[allowed_count:]
    kept_ids = {id(row) for row in kept_calibration}
    kept = [row for row in rows if not is_syntax_only_calibration_row(row) or id(row) in kept_ids]
    exclusions = [
        {
            "row_id": row.get("row_id"),
            "source_id": row.get("source_id"),
            "prompt_family": _prompt_family(row),
            "reason": "syntax_only_calibration_cap",
            "maximum_syntax_only_calibration_share": max_share,
        }
        for row in excluded_calibration
    ]
    return kept, exclusions


def _allowed_calibration_count(main_count: int, max_share: float) -> int:
    if max_share <= 0:
        return 0
    return int((max_share * main_count) // (1 - max_share))


def _cap_release_balance_rows(
    rows: list[dict[str, Any]],
    profile: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically cap overrepresented release slices when alternatives exist."""

    if len(rows) < profile.min_applicable_rows:
        return rows, []
    kept = list(rows)
    exclusions: list[dict[str, Any]] = []
    for _ in range(len(rows)):
        before = len(kept)
        kept, dropped = _cap_boolean_share_rows(
            kept,
            predicate=_is_cross_feature_value_bearing_row,
            max_share=profile.max_cross_feature_value_bearing_share,
            reason="cross_feature_value_bearing_cap",
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_boolean_share_rows(
            kept,
            predicate=_is_value_bearing_measurement_row,
            max_share=profile.max_value_bearing_measurement_share,
            reason="value_bearing_measurement_cap",
            prefer_keep=_cross_feature_keep_priority,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_group_share_rows(
            kept,
            group_key=_prompt_family,
            max_share=profile.max_prompt_family_share,
            reason="prompt_family_share_cap",
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_group_share_rows(
            kept,
            group_key=_prompt_template,
            max_share=profile.max_prompt_template_share,
            reason="prompt_template_share_cap",
        )
        exclusions.extend(dropped)
        if len(kept) == before:
            break
    return kept, exclusions


def _cap_boolean_share_rows(
    rows: list[dict[str, Any]],
    *,
    predicate: Any,
    max_share: float | None,
    reason: str,
    prefer_keep: Any | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_share is None:
        return rows, []
    matched = [row for row in rows if predicate(row)]
    other_count = len(rows) - len(matched)
    allowed_count = _allowed_share_count(other_count, max_share)
    if len(matched) <= allowed_count:
        return rows, []
    key = prefer_keep or _stable_row_key
    kept_matched = sorted(matched, key=key)[:allowed_count]
    kept_ids = {id(row) for row in kept_matched}
    dropped = [row for row in matched if id(row) not in kept_ids]
    exclusions = [
        _balance_exclusion(row, reason=reason, maximum_share=max_share)
        for row in sorted(dropped, key=_stable_row_key)
    ]
    return [row for row in rows if not predicate(row) or id(row) in kept_ids], exclusions


def _cap_group_share_rows(
    rows: list[dict[str, Any]],
    *,
    group_key: Any,
    max_share: float,
    reason: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_share <= 0:
        return rows, []
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(group_key(row), []).append(row)
    if len(groups) < _minimum_group_count_for_share(max_share):
        return rows, []
    kept = list(rows)
    exclusions: list[dict[str, Any]] = []
    for group, group_rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        current_group_rows = [row for row in kept if group_key(row) == group]
        other_count = len(kept) - len(current_group_rows)
        allowed_count = _allowed_share_count(other_count, max_share)
        if len(current_group_rows) <= allowed_count:
            continue
        kept_group_rows = sorted(current_group_rows, key=_stable_row_key)[:allowed_count]
        kept_group_ids = {id(row) for row in kept_group_rows}
        dropped = [row for row in current_group_rows if id(row) not in kept_group_ids]
        exclusions.extend(
            _balance_exclusion(row, reason=reason, maximum_share=max_share, group=group)
            for row in sorted(dropped, key=_stable_row_key)
        )
        kept = [row for row in kept if group_key(row) != group or id(row) in kept_group_ids]
    return kept, exclusions


def _allowed_share_count(other_count: int, max_share: float) -> int:
    if max_share <= 0:
        return 0
    if max_share >= 1:
        return 10**12
    return int((max_share * other_count) // (1 - max_share))


def _minimum_group_count_for_share(max_share: float) -> int:
    if max_share <= 0:
        return 1
    return int((1 / max_share) + 0.999999)


def _cross_feature_keep_priority(row: dict[str, Any]) -> tuple[int, str]:
    return (0 if _is_cross_feature_value_bearing_row(row) else 1, _stable_row_key(row))


def _stable_row_key(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("prompt") or row.get("query_program", {}).get("query_id") or "")


def _balance_exclusion(
    row: dict[str, Any],
    *,
    reason: str,
    maximum_share: float,
    group: str | None = None,
) -> dict[str, Any]:
    exclusion = {
        "row_id": row.get("row_id"),
        "source_id": row.get("source_id"),
        "prompt_family": _prompt_family(row),
        "prompt_template": _prompt_template(row),
        "reason": reason,
        "maximum_share": maximum_share,
    }
    if group is not None:
        exclusion["group"] = group
    return exclusion


def _with_prompt_template_id(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("prompt_template_id"):
        return row
    query = row.get("query_program")
    if not isinstance(query, dict):
        return row
    return {**row, "prompt_template_id": prompt_template_id_from_mapping(query)}


def _prompt_family(row: dict[str, Any]) -> str:
    query_id = row.get("query_program", {}).get("query_id")
    if isinstance(query_id, str) and ":" in query_id:
        return query_id.rsplit(":", 1)[-1]
    row_id = row.get("row_id")
    if isinstance(row_id, str) and ":" in row_id:
        return row_id.rsplit(":", 1)[-1]
    return "unknown"


def _prompt_template(row: dict[str, Any]) -> str:
    template_id = row.get("prompt_template_id")
    if template_id:
        return str(template_id)
    query = row.get("query_program")
    if isinstance(query, dict):
        return prompt_template_id_from_mapping(query)
    return str(row.get("prompt_version", "unknown"))
