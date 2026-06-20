"""Release dataset export helpers."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.family_test_evidence import DEFAULT_FAMILY_TEST_EVIDENCE
from cad_qa.dataset.preview import (
    DEFAULT_PREVIEW_EVIDENCE_FILENAME,
    dataset_preview_evidence_report,
    dataset_preview_markdown,
)
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
from cad_qa.io import record_artifact_path, write_json, write_records
from cad_qa.prompts.render import prompt_template_id_from_mapping
from cad_qa.query.family_manifest import DEFAULT_FAMILY_MANIFEST, RELEASE_STATUSES, load_family_manifest

PARAMETER_DIVERSITY_DIMENSIONS = (
    "aggregation_axis",
    "aggregation_metric",
    "aggregation_rank",
    "clause_axis",
    "clause_metric",
    "clause_relation",
    "clause_target_type",
    "comparison_operator",
    "effect_delta_metric",
    "equal_measurement_metric",
    "extremum_direction",
    "final_selector",
    "measurement_value_bucket",
    "narrowing_mode",
    "rank_direction",
    "reference_point_metric",
    "reference_type",
    "selected_entity_type",
    "target_point_metric",
    "target_type",
    "tie_break_axis",
    "tie_break_direction",
    "tie_break_metric",
    "tie_break_selector",
)


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
    release_rows = [_with_prompt_template_id(row) for row in release_rows]
    balance_capacity = _release_balance_capacity_report(release_rows, profile)
    protected_prompt_families = (
        {_prompt_family(row) for row in release_rows}
        if profile.enforce_intended_family_coverage
        else None
    )
    release_rows, balance_cap_exclusions = _cap_release_balance_rows(
        release_rows,
        profile,
        protected_prompt_families=protected_prompt_families,
    )
    if not release_rows:
        raise ValueError("no release-ready rows found")
    out.mkdir(parents=True, exist_ok=True)
    manifest = split_manifest(release_rows)
    release_rows = rows_with_assigned_splits(release_rows, manifest)
    write_records(record_artifact_path(out, "rows"), release_rows)
    public_private = write_public_private_artifacts(release_rows, out)
    split_rows: dict[str, list[dict[str, Any]]] = {}
    for row in release_rows:
        split_rows.setdefault(row.get("split", "unsplit"), []).append(row)
    for split, items in sorted(split_rows.items()):
        write_records(record_artifact_path(out / "parquet", split), items)

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
    report["pre_balance_capacity"] = balance_capacity
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
            "pre_balance_capacity": balance_capacity,
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
    generated_preview_evidence = _write_release_preview_artifacts(release_rows, out, profile)
    verifier_report = write_release_verifier_report(
        out,
        release_tier=profile.name,
        family_manifest=family_manifest,
        preview_evidence=preview_evidence or generated_preview_evidence,
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
        "pre_balance_capacity": balance_capacity,
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


def _write_release_preview_artifacts(rows: list[dict[str, Any]], out: Path, profile: Any) -> Path:
    sample_per_family = profile.min_preview_samples_per_family or 1
    preview_path = out / "PREVIEW.md"
    preview_path.write_text(
        dataset_preview_markdown(
            rows,
            sample_per_family=sample_per_family,
            seed=0,
        ),
        encoding="utf-8",
    )
    evidence = dataset_preview_evidence_report(
        rows,
        preview_path=preview_path,
        sample_per_family=sample_per_family,
        seed=0,
    )
    evidence_path = out / DEFAULT_PREVIEW_EVIDENCE_FILENAME
    write_json(evidence_path, evidence)
    write_json(preview_path.with_suffix(".preview_evidence.json"), evidence)
    return evidence_path


def _release_balance_capacity_report(rows: list[dict[str, Any]], profile: Any) -> dict[str, Any]:
    """Report whether input rows can satisfy family-share gates before capping."""

    family_counts = Counter(_prompt_family(row) for row in rows)
    family_floor_only_max_rows = None
    if family_counts and profile.min_prompt_family_share > 0:
        family_floor_only_max_rows = min(
            int(count / profile.min_prompt_family_share + 1e-12)
            for count in family_counts.values()
        )
    min_rows_per_family_for_release = None
    families_below_min_release_floor: list[dict[str, Any]] = []
    if profile.min_release_rows is not None:
        min_rows_per_family_for_release = math.ceil(
            profile.min_release_rows * profile.min_prompt_family_share - 1e-12
        )
        families_below_min_release_floor = [
            {"prompt_family": family, "count": count, "minimum_required_count": min_rows_per_family_for_release}
            for family, count in sorted(family_counts.items())
            if count < min_rows_per_family_for_release
        ]
    return {
        "input_row_count": len(rows),
        "prompt_family_count": len(family_counts),
        "prompt_family_counts": dict(sorted(family_counts.items())),
        "minimum_prompt_family_share": profile.min_prompt_family_share,
        "maximum_prompt_family_share": profile.max_prompt_family_share,
        "minimum_release_rows": profile.min_release_rows,
        "minimum_rows_per_family_for_minimum_release_rows": min_rows_per_family_for_release,
        "family_floor_only_max_rows": family_floor_only_max_rows,
        "families_below_minimum_release_floor": families_below_min_release_floor,
        "passes_family_floor_for_minimum_release_rows": not families_below_min_release_floor,
    }


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
    *,
    protected_prompt_families: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically cap overrepresented release slices when alternatives exist."""

    if len(rows) < profile.min_applicable_rows:
        return rows, []
    release_floor = (
        profile.min_release_rows
        if profile.min_release_rows is not None and len(rows) >= profile.min_release_rows
        else None
    )
    kept = list(rows)
    exclusions: list[dict[str, Any]] = []
    for _ in range(len(rows)):
        before = len(kept)
        min_cad_model_count = _minimum_cad_model_count_for_target(
            profile,
            release_floor or len(kept),
        )
        kept, dropped = _cap_boolean_share_rows(
            kept,
            predicate=_is_cross_feature_value_bearing_row,
            max_share=profile.max_cross_feature_value_bearing_share,
            min_prompt_family_share=profile.min_prompt_family_share,
            reason="cross_feature_value_bearing_cap",
            prefer_keep=_high_hop_keep_priority(kept),
            protected_prompt_families=protected_prompt_families,
            min_total_rows=release_floor,
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_boolean_share_rows(
            kept,
            predicate=_is_value_bearing_measurement_row,
            max_share=profile.max_value_bearing_measurement_share,
            min_prompt_family_share=profile.min_prompt_family_share,
            reason="value_bearing_measurement_cap",
            prefer_keep=_cross_feature_keep_priority(kept),
            protected_prompt_families=protected_prompt_families,
            min_total_rows=release_floor,
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_boolean_min_share_rows(
            kept,
            predicate=_is_main_browsecomp_hop_row,
            min_share=profile.min_logical_hop_ge_3_share,
            min_prompt_family_share=profile.min_prompt_family_share,
            reason="main_browsecomp_hop_cap",
            protected_prompt_families=protected_prompt_families,
            min_total_rows=release_floor,
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_group_share_rows(
            kept,
            group_key=_prompt_family,
            max_share=profile.max_prompt_family_share,
            reason="prompt_family_share_cap",
            min_total_rows=release_floor,
            prefer_keep=_parameter_diversity_keep_priority(kept),
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_group_share_rows(
            kept,
            group_key=_prompt_template,
            max_share=profile.max_prompt_template_share,
            reason="prompt_template_share_cap",
            min_total_rows=release_floor,
            prefer_keep=_answer_diversity_keep_priority(kept),
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_group_min_share_rows(
            kept,
            group_key=_prompt_family,
            min_share=profile.min_prompt_family_share,
            reason="prompt_family_min_share_cap",
            min_total_rows=release_floor,
            protected_boolean_minimums=[
                (_is_cross_feature_value_bearing_row, profile.min_cross_feature_value_bearing_share),
                (_is_value_bearing_measurement_row, profile.min_value_bearing_measurement_share),
            ],
            protected_boolean_maximums=[
                (_is_cross_feature_value_bearing_row, profile.max_cross_feature_value_bearing_share),
                (_is_value_bearing_measurement_row, profile.max_value_bearing_measurement_share),
            ],
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_boolean_min_share_rows(
            kept,
            predicate=_is_cross_feature_value_bearing_row,
            min_share=profile.min_cross_feature_value_bearing_share,
            min_prompt_family_share=profile.min_prompt_family_share,
            reason="cross_feature_value_bearing_min_share_cap",
            protected_prompt_families=protected_prompt_families,
            min_total_rows=release_floor,
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        kept, dropped = _cap_boolean_min_share_rows(
            kept,
            predicate=_is_value_bearing_measurement_row,
            min_share=profile.min_value_bearing_measurement_share,
            min_prompt_family_share=profile.min_prompt_family_share,
            reason="value_bearing_measurement_min_share_cap",
            protected_prompt_families=protected_prompt_families,
            min_total_rows=release_floor,
            min_cad_model_count=min_cad_model_count,
        )
        exclusions.extend(dropped)
        if profile.enforce_parameter_balance:
            kept, dropped = _cap_sampled_parameter_share_rows(
                kept,
                profile,
                min_total_rows=release_floor,
                min_cad_model_count=min_cad_model_count,
            )
            exclusions.extend(dropped)
        if len(kept) == before:
            break
    kept, dropped = _improve_answer_diversity_rows(rows, kept, profile)
    exclusions.extend(dropped)
    return kept, exclusions


def _cap_boolean_share_rows(
    rows: list[dict[str, Any]],
    *,
    predicate: Any,
    max_share: float | None,
    min_prompt_family_share: float | None = None,
    reason: str,
    prefer_keep: Any | None = None,
    protected_prompt_families: set[str] | None = None,
    min_total_rows: int | None = None,
    min_cad_model_count: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_share is None:
        return rows, []
    matched = [row for row in rows if predicate(row)]
    other_count = len(rows) - len(matched)
    allowed_count = _allowed_share_count(other_count, max_share)
    if min_total_rows is not None and other_count + allowed_count < min_total_rows:
        allowed_count = min(len(matched), max(allowed_count, min_total_rows - other_count))
    if len(matched) <= allowed_count:
        return rows, []
    key = prefer_keep or _stable_row_key
    kept_matched = _keep_rows_preserving_prompt_families(
        rows,
        matched,
        allowed_count,
        key=key,
        min_family_share=min_prompt_family_share,
        target_total=other_count + allowed_count,
        protected_prompt_families=protected_prompt_families,
        min_cad_model_count=min_cad_model_count,
    )
    kept_ids = {id(row) for row in kept_matched}
    dropped = [row for row in matched if id(row) not in kept_ids]
    exclusions = [
        _balance_exclusion(row, reason=reason, maximum_share=max_share)
        for row in sorted(dropped, key=_stable_row_key)
    ]
    return [row for row in rows if not predicate(row) or id(row) in kept_ids], exclusions


def _cap_boolean_min_share_rows(
    rows: list[dict[str, Any]],
    *,
    predicate: Any,
    min_share: float | None,
    min_prompt_family_share: float | None = None,
    reason: str,
    protected_prompt_families: set[str] | None = None,
    min_total_rows: int | None = None,
    min_cad_model_count: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if min_share is None or min_share <= 0:
        return rows, []
    matched = [row for row in rows if predicate(row)]
    unmatched = [row for row in rows if not predicate(row)]
    if not matched or len(matched) / len(rows) >= min_share:
        return rows, []
    allowed_unmatched_count = int((len(matched) * (1 - min_share)) / min_share + 1e-12)
    if min_total_rows is not None and len(matched) + allowed_unmatched_count < min_total_rows:
        return rows, []
    if len(unmatched) <= allowed_unmatched_count:
        return rows, []
    kept_unmatched = _keep_rows_preserving_prompt_families(
        rows,
        unmatched,
        allowed_unmatched_count,
        key=_stable_row_key,
        min_family_share=min_prompt_family_share,
        target_total=len(matched) + allowed_unmatched_count,
        protected_prompt_families=protected_prompt_families,
        min_cad_model_count=min_cad_model_count,
    )
    kept_unmatched_ids = {id(row) for row in kept_unmatched}
    dropped = [row for row in unmatched if id(row) not in kept_unmatched_ids]
    exclusions = [
        _balance_exclusion(row, reason=reason, minimum_share=min_share)
        for row in sorted(dropped, key=_stable_row_key)
    ]
    return [row for row in rows if predicate(row) or id(row) in kept_unmatched_ids], exclusions


def _cap_group_share_rows(
    rows: list[dict[str, Any]],
    *,
    group_key: Any,
    max_share: float,
    reason: str,
    min_total_rows: int | None = None,
    prefer_keep: Any | None = None,
    min_cad_model_count: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_share <= 0:
        return rows, []
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(group_key(row), []).append(row)
    if len(groups) < _minimum_group_count_for_share(max_share):
        return rows, []
    kept_ids = {id(row) for row in rows}
    exclusions: list[dict[str, Any]] = []
    for group, group_rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        current_group_rows = [row for row in group_rows if id(row) in kept_ids]
        if not current_group_rows:
            continue
        other_count = len(kept_ids) - len(current_group_rows)
        allowed_count = max(1, _allowed_share_count(other_count, max_share))
        if min_total_rows is not None and other_count + allowed_count < min_total_rows:
            allowed_count = min(
                len(current_group_rows),
                max(allowed_count, min_total_rows - other_count),
            )
        if len(current_group_rows) <= allowed_count:
            continue
        keep_key = prefer_keep or _stable_row_key
        kept_group_rows = _keep_rows_preserving_cad_model_identities(
            rows,
            current_group_rows,
            allowed_count,
            key=keep_key,
            min_cad_model_count=min_cad_model_count,
        )
        kept_group_ids = {id(row) for row in kept_group_rows}
        dropped = [row for row in current_group_rows if id(row) not in kept_group_ids]
        dropped_ids = {id(row) for row in dropped}
        exclusions.extend(
            _balance_exclusion(row, reason=reason, maximum_share=max_share, group=group)
            for row in sorted(dropped, key=_stable_row_key)
        )
        kept_ids.difference_update(dropped_ids)
    return [row for row in rows if id(row) in kept_ids], exclusions


def _cap_group_min_share_rows(
    rows: list[dict[str, Any]],
    *,
    group_key: Any,
    min_share: float,
    reason: str,
    protected_boolean_minimums: list[tuple[Any, float | None]] | None = None,
    protected_boolean_maximums: list[tuple[Any, float | None]] | None = None,
    min_total_rows: int | None = None,
    min_cad_model_count: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if min_share <= 0 or not rows:
        return rows, []
    kept = list(rows)
    exclusions: list[dict[str, Any]] = []
    for _ in range(len(rows)):
        groups = _rows_by_group(kept, group_key)
        underrepresented = {
            group: group_rows
            for group, group_rows in groups.items()
            if len(group_rows) / len(kept) < min_share
        }
        if not underrepresented:
            break
        target_total = min(int(len(group_rows) / min_share + 1e-12) for group_rows in underrepresented.values())
        if min_total_rows is not None and target_total < min_total_rows:
            break
        minimum_group_rows_after = max(1, math.ceil(min_share * target_total - 1e-12))
        drop_count = len(kept) - target_total
        if drop_count <= 0:
            break
        protected_minimums = _protected_boolean_minimum_counts(
            kept,
            target_total=target_total,
            protected_boolean_minimums=protected_boolean_minimums,
        )
        protected_maximums = _protected_boolean_maximum_counts(
            kept,
            target_total=target_total,
            protected_boolean_maximums=protected_boolean_maximums,
        )
        protected_drops = [0 for _predicate, _minimum, _current in protected_minimums]
        source_counts = _cad_model_identity_counts(kept)
        protected_groups = set(underrepresented)
        dropped: list[dict[str, Any]] = []
        dropped_by_group: Counter[str] = Counter()
        for group, group_rows in sorted(
            groups.items(),
            key=lambda item: (
                -sum(_protected_boolean_maximum_drop_score(row, protected_maximums) for row in item[1]),
                -len(item[1]),
                item[0],
            ),
        ):
            if group in protected_groups:
                continue
            group_drop_count = dropped_by_group[group]
            for row in sorted(
                group_rows,
                key=lambda row: (
                    _protected_boolean_maximum_drop_score(row, protected_maximums),
                    _stable_row_key(row),
                ),
                reverse=True,
            ):
                if len(dropped) >= drop_count:
                    break
                if len(group_rows) - group_drop_count <= minimum_group_rows_after:
                    break
                if _would_drop_last_cad_model_identity(row, source_counts, min_cad_model_count=min_cad_model_count):
                    continue
                if _would_violate_protected_boolean_minimum(row, protected_minimums, protected_drops):
                    continue
                dropped.append(row)
                group_drop_count += 1
                dropped_by_group[group] = group_drop_count
                _record_protected_boolean_drop(row, protected_minimums, protected_drops)
                _record_cad_model_identity_drop(row, source_counts)
            if len(dropped) >= drop_count:
                break
        if not dropped:
            break
        dropped_ids = {id(row) for row in dropped}
        exclusions.extend(
            _balance_exclusion(row, reason=reason, minimum_share=min_share, group=group_key(row))
            for row in sorted(dropped, key=_stable_row_key)
        )
        kept = [row for row in kept if id(row) not in dropped_ids]
    return kept, exclusions


def _cap_sampled_parameter_share_rows(
    rows: list[dict[str, Any]],
    profile: Any,
    *,
    min_total_rows: int | None = None,
    min_cad_model_count: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    max_share = profile.max_parameter_value_share
    if max_share is None or max_share <= 0 or len(rows) < profile.min_applicable_rows:
        return rows, []
    kept = list(rows)
    drops = _sampled_parameter_cap_drop_batch(
        kept,
        max_share=max_share,
        min_family_share=profile.min_prompt_family_share,
        min_total_rows=min_total_rows,
        min_cad_model_count=min_cad_model_count,
    )
    if not drops:
        return rows, []
    dropped_ids = {id(drop["row"]) for drop in drops}
    kept = [row for row in kept if id(row) not in dropped_ids]
    exclusions = [
        _balance_exclusion(
            drop["row"],
            reason="sampled_parameter_share_cap",
            maximum_share=max_share,
            group=f"{drop['prompt_family']}:{drop['dimension']}:{drop['value']}",
        )
        for drop in sorted(drops, key=lambda item: _stable_row_key(item["row"]))
    ]
    return kept, exclusions


def _sampled_parameter_cap_drop_batch(
    rows: list[dict[str, Any]],
    *,
    max_share: float,
    min_family_share: float,
    min_total_rows: int | None,
    min_cad_model_count: int | None,
) -> list[dict[str, Any]]:
    family_rows = _rows_by_group(rows, _prompt_family)
    family_minimum_rows = 1
    if min_total_rows is not None and min_family_share > 0:
        family_minimum_rows = max(1, math.ceil(min_total_rows * min_family_share - 1e-12))
    total_drop_budget = len(rows) - min_total_rows if min_total_rows is not None else len(rows)
    if total_drop_budget <= 0:
        return []
    priority = _parameter_diversity_keep_priority(rows)
    selected_ids: set[int] = set()
    drops: list[dict[str, Any]] = []
    family_drop_counts: Counter[str] = Counter()
    source_counts = _cad_model_identity_counts(rows)
    for family, current_family_rows in sorted(family_rows.items()):
        if len(current_family_rows) <= family_minimum_rows:
            continue
        family_drop_budget = len(current_family_rows) - family_minimum_rows
        for dimension in PARAMETER_DIVERSITY_DIMENSIONS:
            remaining_family_rows = [row for row in current_family_rows if id(row) not in selected_ids]
            value_groups = _sampled_parameter_value_groups(remaining_family_rows, dimension)
            if len(value_groups) < _minimum_group_count_for_share(max_share):
                continue
            for value, value_rows in sorted(value_groups.items(), key=lambda item: (-len(item[1]), item[0])):
                remaining_family_rows = [row for row in current_family_rows if id(row) not in selected_ids]
                remaining_value_ids = {id(row) for row in value_rows}
                value_rows = [row for row in remaining_family_rows if id(row) in remaining_value_ids]
                other_count = len(remaining_family_rows) - len(value_rows)
                allowed_count = max(1, _allowed_share_count(other_count, max_share))
                if len(value_rows) <= allowed_count:
                    continue
                remaining_family_budget = family_drop_budget - family_drop_counts[family]
                remaining_total_budget = total_drop_budget - len(drops)
                if remaining_family_budget <= 0 or remaining_total_budget <= 0:
                    continue
                drop_count = min(len(value_rows) - allowed_count, remaining_family_budget, remaining_total_budget)
                candidates = sorted(value_rows, key=priority, reverse=True)
                for row in candidates:
                    if drop_count <= 0:
                        break
                    if _would_drop_last_cad_model_identity(row, source_counts, min_cad_model_count=min_cad_model_count):
                        continue
                    selected_ids.add(id(row))
                    family_drop_counts[family] += 1
                    drop_count -= 1
                    _record_cad_model_identity_drop(row, source_counts)
                    drops.append(
                        {
                            "row": row,
                            "prompt_family": family,
                            "dimension": dimension,
                            "value": value,
                        }
                    )
    return drops


def _sampled_parameter_value_groups(
    rows: list[dict[str, Any]],
    dimension: str,
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for value in _sampled_parameter_values(row, dimension):
            groups.setdefault(value, []).append(row)
    return groups


def _sampled_parameter_values(row: dict[str, Any], dimension: str) -> tuple[str, ...]:
    query = row.get("query_program")
    if not isinstance(query, dict):
        return ()
    sampled = query.get("sampled_parameters")
    if not isinstance(sampled, dict):
        return ()
    raw = sampled.get(dimension)
    if raw is None:
        return ()
    values = raw if isinstance(raw, list) else [raw]
    return tuple(str(value) for value in values if value is not None)


def _improve_answer_diversity_rows(
    all_rows: list[dict[str, Any]],
    kept_rows: list[dict[str, Any]],
    profile: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_unique = profile.min_unique_answer_count
    if target_unique is None or target_unique <= 0:
        return kept_rows, []
    answer_counts = Counter(_answer_identity_key(row) for row in kept_rows)
    if len(answer_counts) >= target_unique:
        return kept_rows, []
    available_unique = {_answer_identity_key(row) for row in all_rows}
    if len(available_unique) < target_unique:
        return kept_rows, []

    kept_ids = {id(row) for row in kept_rows}
    replacements_by_family: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(all_rows, key=_stable_row_key):
        if id(row) in kept_ids:
            continue
        answer_key = _answer_identity_key(row)
        if answer_key in answer_counts:
            continue
        replacements_by_family.setdefault(_prompt_family(row), []).append(row)

    kept = list(kept_rows)
    removed: list[dict[str, Any]] = []
    replacement_indices: Counter[str] = Counter()
    for row in sorted(
        kept,
        key=lambda item: (answer_counts[_answer_identity_key(item)], _stable_row_key(item)),
        reverse=True,
    ):
        if len(answer_counts) >= target_unique:
            break
        row_answer_key = _answer_identity_key(row)
        if answer_counts[row_answer_key] <= 1:
            continue
        family = _prompt_family(row)
        replacement = _next_answer_diversity_replacement(
            replacements_by_family.get(family, []),
            replacement_indices[family],
            answer_counts,
            row,
        )
        if replacement is None:
            continue
        replacement_indices[family] += 1
        original_position = next(position for position, kept_row in enumerate(kept) if id(kept_row) == id(row))
        kept[original_position] = replacement
        removed.append(row)
        answer_counts[row_answer_key] -= 1
        if answer_counts[row_answer_key] <= 0:
            del answer_counts[row_answer_key]
        answer_counts[_answer_identity_key(replacement)] += 1

    exclusions = [
        _balance_exclusion(row, reason="answer_diversity_replacement")
        for row in sorted(removed, key=_stable_row_key)
    ]
    return kept, exclusions


def _next_answer_diversity_replacement(
    candidates: list[dict[str, Any]],
    start_index: int,
    answer_counts: Counter[str],
    replaced_row: dict[str, Any],
) -> dict[str, Any] | None:
    replaced_shape = _answer_diversity_balance_shape(replaced_row)
    fallback: dict[str, Any] | None = None
    for candidate in candidates[start_index:]:
        if _answer_identity_key(candidate) in answer_counts:
            continue
        if fallback is None:
            fallback = candidate
        if _answer_diversity_balance_shape(candidate) == replaced_shape:
            return candidate
    return fallback


def _answer_diversity_balance_shape(row: dict[str, Any]) -> tuple[bool, bool, bool]:
    return (
        _is_value_bearing_measurement_row(row),
        _is_cross_feature_value_bearing_row(row),
        _is_main_browsecomp_hop_row(row),
    )


def _protected_boolean_minimum_counts(
    rows: list[dict[str, Any]],
    *,
    target_total: int,
    protected_boolean_minimums: list[tuple[Any, float | None]] | None,
) -> list[tuple[Any, int, int]]:
    protected: list[tuple[Any, int, int]] = []
    if not protected_boolean_minimums:
        return protected
    for predicate, min_share in protected_boolean_minimums:
        if min_share is None or min_share <= 0:
            continue
        minimum_count = math.ceil(min_share * target_total - 1e-12)
        current_count = sum(1 for row in rows if predicate(row))
        if current_count > minimum_count:
            protected.append((predicate, minimum_count, current_count))
    return protected


def _protected_boolean_maximum_counts(
    rows: list[dict[str, Any]],
    *,
    target_total: int,
    protected_boolean_maximums: list[tuple[Any, float | None]] | None,
) -> list[tuple[Any, int, int]]:
    protected: list[tuple[Any, int, int]] = []
    if not protected_boolean_maximums:
        return protected
    for predicate, max_share in protected_boolean_maximums:
        if max_share is None or max_share <= 0:
            continue
        maximum_count = math.floor(max_share * target_total + 1e-12)
        current_count = sum(1 for row in rows if predicate(row))
        if current_count > maximum_count:
            protected.append((predicate, maximum_count, current_count))
    return protected


def _protected_boolean_maximum_drop_score(
    row: dict[str, Any],
    protected_maximums: list[tuple[Any, int, int]],
) -> int:
    return sum(1 for predicate, _maximum_count, _current_count in protected_maximums if predicate(row))


def _would_violate_protected_boolean_minimum(
    row: dict[str, Any],
    protected_minimums: list[tuple[Any, int, int]],
    protected_drops: list[int],
) -> bool:
    for index, (predicate, minimum_count, current_count) in enumerate(protected_minimums):
        if predicate(row) and current_count - protected_drops[index] <= minimum_count:
            return True
    return False


def _record_protected_boolean_drop(
    row: dict[str, Any],
    protected_minimums: list[tuple[Any, int, int]],
    protected_drops: list[int],
) -> None:
    for index, (predicate, _minimum_count, _current_count) in enumerate(protected_minimums):
        if predicate(row):
            protected_drops[index] += 1


def _rows_by_group(rows: list[dict[str, Any]], group_key: Any) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(group_key(row), []).append(row)
    return groups


def _keep_rows_preserving_prompt_families(
    all_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    keep_count: int,
    *,
    key: Any,
    min_family_share: float | None = None,
    target_total: int | None = None,
    protected_prompt_families: set[str] | None = None,
    min_cad_model_count: int | None = None,
) -> list[dict[str, Any]]:
    if keep_count <= 0:
        return []
    candidates = sorted(candidate_rows, key=key)
    if len(candidates) <= keep_count:
        return candidates
    kept: list[dict[str, Any]] = []
    required_by_family = _minimum_candidate_rows_by_prompt_family(
        all_rows,
        candidates,
        min_family_share=min_family_share,
        target_total=target_total,
        protected_prompt_families=protected_prompt_families,
    )
    for family, required_count in sorted(required_by_family.items()):
        family_rows = [row for row in candidates if _prompt_family(row) == family]
        kept.extend(family_rows[:required_count])
    kept_ids = {id(row) for row in kept}
    for source_rows in _required_cad_model_identity_rows(
        all_rows,
        candidates,
        key=key,
        min_cad_model_count=min_cad_model_count,
    ).values():
        if any(id(row) in kept_ids for row in source_rows):
            continue
        kept.append(source_rows[0])
        kept_ids.add(id(source_rows[0]))
    if len(kept) > keep_count:
        protected = protected_prompt_families or set()
        protected_kept = [row for row in kept if _prompt_family(row) in protected]
        if protected_kept:
            protected_ids = {id(row) for row in protected_kept}
            remaining = [row for row in kept if id(row) not in protected_ids]
            return sorted(
                protected_kept + sorted(remaining, key=key)[: max(0, keep_count - len(protected_kept))],
                key=key,
            )
        return sorted(kept, key=key)[:keep_count]
    for row in candidates:
        if len(kept) >= keep_count:
            break
        if id(row) not in kept_ids:
            kept.append(row)
            kept_ids.add(id(row))
    return sorted(kept, key=key)


def _keep_rows_preserving_cad_model_identities(
    all_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    keep_count: int,
    *,
    key: Any,
    min_cad_model_count: int | None = None,
) -> list[dict[str, Any]]:
    candidates = sorted(candidate_rows, key=key)
    if len(candidates) <= keep_count:
        return candidates
    kept: list[dict[str, Any]] = []
    kept_ids: set[int] = set()
    for source_rows in _required_cad_model_identity_rows(
        all_rows,
        candidates,
        key=key,
        min_cad_model_count=min_cad_model_count,
    ).values():
        row = source_rows[0]
        kept.append(row)
        kept_ids.add(id(row))
    if len(kept) > keep_count:
        return sorted(kept, key=key)[:keep_count]
    for row in candidates:
        if len(kept) >= keep_count:
            break
        if id(row) not in kept_ids:
            kept.append(row)
            kept_ids.add(id(row))
    return sorted(kept, key=key)


def _minimum_candidate_rows_by_prompt_family(
    all_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    min_family_share: float | None,
    target_total: int | None,
    protected_prompt_families: set[str] | None = None,
) -> dict[str, int]:
    candidates_by_family = _rows_by_group(candidate_rows, _prompt_family)
    candidate_ids = {id(row) for row in candidate_rows}
    noncandidate_counts = Counter(
        _prompt_family(row)
        for row in all_rows
        if id(row) not in candidate_ids
    )
    minimum_rows = 1
    if min_family_share and target_total:
        minimum_rows = max(1, math.ceil(min_family_share * target_total - 1e-12))
    required: dict[str, int] = {}
    for family, family_candidates in candidates_by_family.items():
        family_minimum_rows = minimum_rows
        if family in (protected_prompt_families or set()) and noncandidate_counts.get(family, 0) == 0:
            family_minimum_rows = max(1, family_minimum_rows)
        needed = family_minimum_rows - noncandidate_counts.get(family, 0)
        if needed > 0:
            required[family] = min(needed, len(family_candidates))
    return required


def _required_cad_model_identity_rows(
    all_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    key: Any,
    min_cad_model_count: int | None,
) -> dict[str, list[dict[str, Any]]]:
    if min_cad_model_count is None or len(_cad_model_identity_counts(all_rows)) > min_cad_model_count:
        return {}
    candidate_ids = {id(row) for row in candidate_rows}
    noncandidate_identities = {
        identity
        for row in all_rows
        if id(row) not in candidate_ids
        if (identity := _cad_model_identity_key(row))
    }
    candidates_by_identity: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(candidate_rows, key=key):
        identity = _cad_model_identity_key(row)
        if identity and identity not in noncandidate_identities:
            candidates_by_identity.setdefault(identity, []).append(row)
    return candidates_by_identity


def _allowed_share_count(other_count: int, max_share: float) -> int:
    if max_share <= 0:
        return 0
    if max_share >= 1:
        return 10**12
    return int((max_share * other_count) / (1 - max_share) + 1e-12)


def _minimum_group_count_for_share(max_share: float) -> int:
    if max_share <= 0:
        return 1
    return int((1 / max_share) + 0.999999)


def _minimum_cad_model_count_for_target(profile: Any, target_total: int) -> int | None:
    min_share = getattr(profile, "min_distinct_cad_model_share", None)
    if min_share is None:
        return None
    return math.ceil(target_total * min_share - 1e-12)


def _cross_feature_keep_priority(rows: list[dict[str, Any]]) -> Any:
    source_counts = _cad_model_identity_counts(rows)

    def key(row: dict[str, Any]) -> tuple[int, int, int, str]:
        return (
            0 if _is_cross_feature_value_bearing_row(row) else 1,
            0 if _is_main_browsecomp_hop_row(row) else 1,
            _cad_model_identity_count(row, source_counts),
            _stable_row_key(row),
        )

    return key


def _high_hop_keep_priority(rows: list[dict[str, Any]]) -> Any:
    source_counts = _cad_model_identity_counts(rows)

    def key(row: dict[str, Any]) -> tuple[int, int, str]:
        return (
            0 if _is_main_browsecomp_hop_row(row) else 1,
            _cad_model_identity_count(row, source_counts),
            _stable_row_key(row),
        )

    return key


def _answer_diversity_keep_priority(rows: list[dict[str, Any]]) -> Any:
    answer_counts = Counter(_answer_identity_key(row) for row in rows)
    source_counts = _cad_model_identity_counts(rows)

    def key(row: dict[str, Any]) -> tuple[int, int, str]:
        return (
            answer_counts[_answer_identity_key(row)],
            _cad_model_identity_count(row, source_counts),
            _stable_row_key(row),
        )

    return key


def _parameter_diversity_keep_priority(rows: list[dict[str, Any]]) -> Any:
    answer_counts = Counter(_answer_identity_key(row) for row in rows)
    parameter_counts: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        family = _prompt_family(row)
        for dimension in PARAMETER_DIVERSITY_DIMENSIONS:
            for value in _sampled_parameter_values(row, dimension):
                parameter_counts[(family, dimension, value)] += 1

    def key(row: dict[str, Any]) -> tuple[int, int, str]:
        family = _prompt_family(row)
        parameter_frequency = 0
        for dimension in PARAMETER_DIVERSITY_DIMENSIONS:
            for value in _sampled_parameter_values(row, dimension):
                parameter_frequency += parameter_counts[(family, dimension, value)]
        return (parameter_frequency, answer_counts[_answer_identity_key(row)], _stable_row_key(row))

    return key


def _answer_identity_key(row: dict[str, Any]) -> str:
    answer = row.get("gold_answer")
    if row.get("answer_format") == "entity_id":
        return f"{row.get('source_id')}::{answer}"
    return str(answer)


def _cad_model_identity_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(key for row in rows if (key := _cad_model_identity_key(row)))


def _cad_model_identity_count(row: dict[str, Any], counts: Counter[str]) -> int:
    key = _cad_model_identity_key(row)
    return counts[key] if key else 10**12


def _would_drop_last_cad_model_identity(
    row: dict[str, Any],
    counts: Counter[str],
    *,
    min_cad_model_count: int | None,
) -> bool:
    if min_cad_model_count is None or len([count for count in counts.values() if count > 0]) > min_cad_model_count:
        return False
    key = _cad_model_identity_key(row)
    return bool(key and counts[key] <= 1)


def _record_cad_model_identity_drop(row: dict[str, Any], counts: Counter[str]) -> None:
    key = _cad_model_identity_key(row)
    if key:
        counts[key] -= 1


def _cad_model_identity_key(row: dict[str, Any]) -> str:
    metadata = row.get("source_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    for source in (metadata, row):
        for key in ("cad_model_id", "source_model_id", "model_id", "source_id"):
            value = source.get(key)
            if value:
                return str(value)
    return ""


def _is_main_browsecomp_hop_row(row: dict[str, Any]) -> bool:
    return int(row.get("logical_hop_count") or 0) >= 3


def _stable_row_key(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("prompt") or row.get("query_program", {}).get("query_id") or "")


def _balance_exclusion(
    row: dict[str, Any],
    *,
    reason: str,
    maximum_share: float | None = None,
    minimum_share: float | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    exclusion = {
        "row_id": row.get("row_id"),
        "source_id": row.get("source_id"),
        "prompt_family": _prompt_family(row),
        "prompt_template": _prompt_template(row),
        "reason": reason,
    }
    if maximum_share is not None:
        exclusion["maximum_share"] = maximum_share
    if minimum_share is not None:
        exclusion["minimum_share"] = minimum_share
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
    query = row.get("query_program")
    if isinstance(query, dict):
        canonical = query.get("canonical_prompt_family")
        if isinstance(canonical, str) and canonical:
            return canonical
        sampled = query.get("sampled_parameters")
        if isinstance(sampled, dict):
            values = sampled.get("canonical_prompt_family")
            if isinstance(values, list) and values:
                return str(values[0])
            if isinstance(values, str) and values:
                return values
        query_id = query.get("query_id")
    else:
        query_id = None
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
