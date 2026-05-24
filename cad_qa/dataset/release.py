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
    release_gate_profile,
    write_release_verifier_report,
)
from cad_qa.dataset.report import dataset_card_markdown, dataset_report, failure_report
from cad_qa.dataset.sft import is_syntax_only_calibration_row
from cad_qa.dataset.split import rows_with_assigned_splits, split_audit, split_manifest
from cad_qa.dataset.validate import validate_dataset_dir, validate_rows
from cad_qa.io import write_json, write_jsonl
from cad_qa.prompts.render import prompt_template_id_from_mapping
from cad_qa.query.family_manifest import DEFAULT_FAMILY_MANIFEST


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
    deduped_rows, duplicate_exclusions = _dedupe_release_prompts(release_valid_rows)
    release_rows, calibration_cap_exclusions = _cap_syntax_only_calibration_rows(
        deduped_rows,
        profile.max_syntax_only_calibration_share,
    )
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
    report["excluded_prompt_policy_count"] = excluded_prompt_policy_count
    report["excluded_duplicate_prompt_count"] = len(duplicate_exclusions)
    report["excluded_syntax_only_calibration_cap_count"] = len(calibration_cap_exclusions)
    write_json(out / "dataset_report.json", report)
    write_json(
        out / "release_exclusions.json",
        {
            "excluded_quarantine_count": excluded_quarantine_count,
            "excluded_release_validation_count": len(validation_exclusions),
            "excluded_prompt_policy_count": excluded_prompt_policy_count,
            "excluded_duplicate_prompt_count": len(duplicate_exclusions),
            "excluded_syntax_only_calibration_cap_count": len(calibration_cap_exclusions),
            "release_validation_exclusions": validation_exclusions,
            "duplicate_prompt_exclusions": duplicate_exclusions,
            "syntax_only_calibration_cap_exclusions": calibration_cap_exclusions,
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
        "excluded_prompt_policy_count": excluded_prompt_policy_count,
        "excluded_duplicate_prompt_count": len(duplicate_exclusions),
        "excluded_syntax_only_calibration_cap_count": len(calibration_cap_exclusions),
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
