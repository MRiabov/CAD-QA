"""Release-scale verifier and quarantine reports."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.family_test_evidence import DEFAULT_FAMILY_TEST_EVIDENCE, family_test_evidence_gate_report
from cad_qa.dataset.parameter_balance import parameter_balance_report
from cad_qa.dataset.preview import DEFAULT_PREVIEW_EVIDENCE_FILENAME, preview_evidence_gate_report
from cad_qa.dataset.public import public_private_audit
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.report import dataset_report, failure_report
from cad_qa.dataset.sft import (
    is_geometry_critical_row,
    is_syntax_only_calibration_row,
    prompt_family,
    training_readiness_report,
)
from cad_qa.dataset.split import split_audit, split_manifest
from cad_qa.dataset.validate import validate_rows
from cad_qa.io import existing_record_artifact_path, read_records, write_json
from cad_qa.prompts.render import prompt_template_id_from_mapping
from cad_qa.query.family_manifest import DEFAULT_FAMILY_MANIFEST, intended_family_coverage_report
from cad_qa.query.resolver import VALUE_BUCKET_DECIMALS, VALUE_MATCH_TOLERANCE

DEFAULT_RELEASE_TIER = "release-candidate"
RELEASE_TIERS = ("smoke", "release-candidate", "benchmark-release")


@dataclass(frozen=True)
class ReleaseGateProfile:
    name: str
    min_applicable_rows: int
    min_release_rows: int | None
    min_distinct_cad_model_share: float | None
    min_default_sft_rows: int | None
    max_default_sft_syntax_only_share: float
    min_prompt_family_count: int
    min_prompt_family_share: float
    max_prompt_family_share: float
    min_prompt_template_count: int
    max_prompt_template_share: float
    min_unique_answer_count: int
    min_answer_entropy_bits: float
    min_geometry_hop_positive_share: float
    max_syntax_only_calibration_share: float
    min_geometry_critical_training_share: float
    min_logical_hop_ge_3_share: float | None
    min_value_bearing_measurement_share: float
    max_value_bearing_measurement_share: float | None
    min_cross_feature_value_bearing_count: int
    min_cross_feature_value_bearing_share: float | None
    max_cross_feature_value_bearing_share: float | None
    min_pre_final_candidate_count: int | None
    min_median_pre_final_candidate_count: float | None
    min_split_groups_per_split: int | None
    enforce_intended_family_coverage: bool
    enforce_parameter_balance: bool
    max_parameter_value_share: float | None
    min_axis_direction_parameter_share: float | None
    enforce_preview_evidence: bool
    min_preview_samples_per_family: int | None
    enforce_family_test_evidence: bool


SMOKE_RELEASE_PROFILE = ReleaseGateProfile(
    name="smoke",
    min_applicable_rows=20,
    min_release_rows=None,
    min_distinct_cad_model_share=None,
    min_default_sft_rows=None,
    max_default_sft_syntax_only_share=0.0,
    min_prompt_family_count=4,
    min_prompt_family_share=0.01,
    max_prompt_family_share=0.10,
    min_prompt_template_count=4,
    max_prompt_template_share=0.35,
    min_unique_answer_count=8,
    min_answer_entropy_bits=2.0,
    min_geometry_hop_positive_share=0.75,
    max_syntax_only_calibration_share=0.10,
    min_geometry_critical_training_share=0.95,
    min_logical_hop_ge_3_share=None,
    min_value_bearing_measurement_share=0.05,
    max_value_bearing_measurement_share=None,
    min_cross_feature_value_bearing_count=1,
    min_cross_feature_value_bearing_share=None,
    max_cross_feature_value_bearing_share=None,
    min_pre_final_candidate_count=None,
    min_median_pre_final_candidate_count=None,
    min_split_groups_per_split=None,
    enforce_intended_family_coverage=False,
    enforce_parameter_balance=False,
    max_parameter_value_share=None,
    min_axis_direction_parameter_share=None,
    enforce_preview_evidence=False,
    min_preview_samples_per_family=None,
    enforce_family_test_evidence=False,
)

RELEASE_CANDIDATE_PROFILE = replace(SMOKE_RELEASE_PROFILE, name="release-candidate")

BENCHMARK_RELEASE_PROFILE = ReleaseGateProfile(
    name="benchmark-release",
    min_applicable_rows=1,
    min_release_rows=10_000,
    min_distinct_cad_model_share=0.10,
    min_default_sft_rows=10_000,
    max_default_sft_syntax_only_share=0.0,
    min_prompt_family_count=10,
    min_prompt_family_share=0.01,
    max_prompt_family_share=0.10,
    min_prompt_template_count=20,
    max_prompt_template_share=0.05,
    min_unique_answer_count=1_000,
    min_answer_entropy_bits=8.0,
    min_geometry_hop_positive_share=0.95,
    max_syntax_only_calibration_share=0.02,
    min_geometry_critical_training_share=0.99,
    min_logical_hop_ge_3_share=0.90,
    min_value_bearing_measurement_share=0.15,
    max_value_bearing_measurement_share=0.30,
    min_cross_feature_value_bearing_count=1,
    min_cross_feature_value_bearing_share=0.05,
    max_cross_feature_value_bearing_share=0.15,
    min_pre_final_candidate_count=2,
    min_median_pre_final_candidate_count=4.0,
    min_split_groups_per_split=3,
    enforce_intended_family_coverage=True,
    enforce_parameter_balance=True,
    max_parameter_value_share=0.35,
    min_axis_direction_parameter_share=0.20,
    enforce_preview_evidence=True,
    min_preview_samples_per_family=20,
    enforce_family_test_evidence=True,
)

RELEASE_GATE_PROFILES = {
    "smoke": SMOKE_RELEASE_PROFILE,
    "release-candidate": RELEASE_CANDIDATE_PROFILE,
    "benchmark-release": BENCHMARK_RELEASE_PROFILE,
}

MIN_RELEASE_BALANCE_ROWS = RELEASE_CANDIDATE_PROFILE.min_applicable_rows
MIN_PROMPT_FAMILY_COUNT = RELEASE_CANDIDATE_PROFILE.min_prompt_family_count
MIN_PROMPT_FAMILY_SHARE = RELEASE_CANDIDATE_PROFILE.min_prompt_family_share
MAX_PROMPT_FAMILY_SHARE = RELEASE_CANDIDATE_PROFILE.max_prompt_family_share
MIN_PROMPT_TEMPLATE_COUNT = RELEASE_CANDIDATE_PROFILE.min_prompt_template_count
MAX_PROMPT_TEMPLATE_SHARE = RELEASE_CANDIDATE_PROFILE.max_prompt_template_share
MIN_UNIQUE_ANSWER_COUNT = RELEASE_CANDIDATE_PROFILE.min_unique_answer_count
MIN_ANSWER_ENTROPY_BITS = RELEASE_CANDIDATE_PROFILE.min_answer_entropy_bits
MIN_GEOMETRY_HOP_POSITIVE_SHARE = RELEASE_CANDIDATE_PROFILE.min_geometry_hop_positive_share
MAX_SYNTAX_ONLY_CALIBRATION_SHARE = RELEASE_CANDIDATE_PROFILE.max_syntax_only_calibration_share
MIN_VALUE_BEARING_MEASUREMENT_SHARE = RELEASE_CANDIDATE_PROFILE.min_value_bearing_measurement_share
MIN_CROSS_FEATURE_VALUE_BEARING_COUNT = RELEASE_CANDIDATE_PROFILE.min_cross_feature_value_bearing_count


def release_verifier_report(
    rows: list[dict[str, Any]],
    *,
    failures: list[dict[str, Any]] | None = None,
    split: dict[str, Any] | None = None,
    public_rows: list[dict[str, Any]] | None = None,
    private_rows: list[dict[str, Any]] | None = None,
    release_tier: str = DEFAULT_RELEASE_TIER,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
    preview_evidence: dict[str, Any] | None = None,
    family_test_evidence: Path | None = DEFAULT_FAMILY_TEST_EVIDENCE,
) -> dict[str, Any]:
    """Aggregate release-readiness gates and verifier/quarantine taxonomy."""

    profile = release_gate_profile(release_tier)
    split = split or split_manifest(rows)
    dataset = dataset_report(rows)
    validation = validate_rows(rows)
    release_validation = validate_rows(rows, release=True)
    leakage = leakage_audit(rows, split)
    split_quality = split_audit(rows, split)
    quarantine = quarantine_report(rows)
    training_readiness = training_readiness_report(
        rows,
        dominance_threshold=profile.min_geometry_critical_training_share,
        max_syntax_only_share=profile.max_default_sft_syntax_only_share,
    )
    release_balance = release_balance_report(rows, release_tier=profile.name)
    intended_family_coverage = intended_family_coverage_report(
        rows,
        manifest_path=family_manifest,
        enforce=profile.enforce_intended_family_coverage,
    )
    intended_family_share_feasibility = intended_family_share_feasibility_report(
        intended_family_coverage,
        profile,
    )
    parameter_balance = parameter_balance_report(
        rows,
        family_manifest=family_manifest,
        max_parameter_value_share=profile.max_parameter_value_share,
        min_axis_direction_share=profile.min_axis_direction_parameter_share,
        enforce=profile.enforce_parameter_balance,
    )
    preview_evidence_report = preview_evidence_gate_report(
        rows,
        evidence=preview_evidence,
        family_manifest=family_manifest,
        min_samples_per_family=profile.min_preview_samples_per_family,
        enforce=profile.enforce_preview_evidence,
    )
    family_test_evidence_report = family_test_evidence_gate_report(
        rows,
        evidence_path=family_test_evidence,
        family_manifest=family_manifest,
        enforce=profile.enforce_family_test_evidence,
    )
    shortcut_resistance = dataset["shortcut_resistance"]
    failures_by_reason = failure_report(failures or [])
    public_private = public_private_audit(public_rows, private_rows) if public_rows is not None and private_rows is not None else None
    stop_gates = {
        "release_row_count": _passes_minimum_count(len(rows), profile.min_release_rows),
        "row_validation": validation["valid"],
        "release_validation": release_validation["valid"],
        "group_safe_split_audit": split_quality["valid"],
        "benchmark_split_group_coverage": _passes_split_group_coverage(
            split_quality,
            profile.min_split_groups_per_split,
        ),
        "leakage_audit": leakage["valid"],
        "no_quarantined_rows": quarantine["quarantine_count"] == 0,
        "default_sft_geometry_critical_dominance": training_readiness["passes_geometry_critical_dominance"],
        "default_sft_row_count": _passes_minimum_count(
            training_readiness["default_training_rows"],
            profile.min_default_sft_rows,
        ),
        "default_sft_syntax_only_cap": training_readiness["passes_syntax_only_training_cap"],
        "distinct_cad_model_coverage": release_balance["passes_distinct_cad_model_coverage"],
        "prompt_family_balance": release_balance["passes_prompt_family_balance"],
        "prompt_template_balance": release_balance["passes_prompt_template_balance"],
        "answer_entropy": release_balance["passes_answer_entropy"],
        "geometry_hop_coverage": release_balance["passes_geometry_hop_coverage"],
        "main_browsecomp_hop_coverage": release_balance["passes_main_browsecomp_hop_coverage"],
        "syntax_only_calibration_cap": release_balance["passes_syntax_only_calibration_cap"],
        "value_bearing_measurement_coverage": release_balance["passes_value_bearing_measurement_coverage"],
        "cross_feature_value_bearing_coverage": release_balance["passes_cross_feature_value_bearing_coverage"],
        "candidate_breadth": release_balance["passes_candidate_breadth"],
        "intended_family_coverage": intended_family_coverage["valid"],
        "intended_family_share_feasibility": intended_family_share_feasibility["valid"],
        "parameter_balance": parameter_balance["valid"],
        "preview_evidence": preview_evidence_report["valid"],
        "family_test_evidence": family_test_evidence_report["valid"],
        "geometry_critical_prompt_family_coverage": _passes_geometry_critical_family_coverage(
            shortcut_resistance
        ),
        "public_private_audit": public_private["valid"] if public_private is not None else None,
    }
    blocking = [name for name, passed in stop_gates.items() if passed is False]
    return {
        "row_count": len(rows),
        "release_tier": profile.name,
        "release_gate_profile": release_gate_profile_report(profile),
        "valid_for_release": not blocking,
        "blocking_gates": blocking,
        "stop_gates": stop_gates,
        "dataset": dataset,
        "validation": validation,
        "release_validation": release_validation,
        "split_audit": split_quality,
        "leakage_audit": leakage,
        "quarantine": quarantine,
        "training_readiness": training_readiness,
        "release_balance": release_balance,
        "intended_family_coverage": intended_family_coverage,
        "intended_family_share_feasibility": intended_family_share_feasibility,
        "parameter_balance": parameter_balance,
        "preview_evidence": preview_evidence_report,
        "family_test_evidence": family_test_evidence_report,
        "shortcut_resistance": shortcut_resistance,
        "failure_report": failures_by_reason,
        "split_manifest": split,
        "public_private_audit": public_private,
    }


def release_balance_report(
    rows: list[dict[str, Any]],
    *,
    release_tier: str = DEFAULT_RELEASE_TIER,
) -> dict[str, Any]:
    """Summarize release composition checks that catch shortcut-heavy datasets."""

    profile = release_gate_profile(release_tier)
    row_count = len(rows)
    prompt_family_counts = Counter(prompt_family(row) for row in rows)
    prompt_template_counts = Counter(_prompt_template_id(row) for row in rows)
    answer_counts = Counter(_answer_identity_key(row) for row in rows)
    answer_format_counts = Counter(str(row.get("answer_format") or "unknown") for row in rows)
    distinct_cad_model_ids = {model_id for row in rows if (model_id := _cad_model_identity_key(row))}
    distinct_cad_model_count = len(distinct_cad_model_ids)
    minimum_distinct_cad_model_count = (
        _minimum_distinct_cad_model_count(row_count, profile.min_distinct_cad_model_share)
        if profile.min_distinct_cad_model_share is not None
        else None
    )
    geometry_hop_positive_count = sum(1 for row in rows if int(row.get("geometry_hop_count") or 0) > 0)
    logical_hop_ge_3_count = sum(1 for row in rows if int(row.get("logical_hop_count") or 0) >= 3)
    geometry_critical_count = sum(1 for row in rows if is_geometry_critical_row(row))
    syntax_only_calibration_count = sum(1 for row in rows if is_syntax_only_calibration_row(row))
    value_bearing_measurement_count = sum(1 for row in rows if _is_value_bearing_measurement_row(row))
    cross_feature_value_bearing_count = sum(1 for row in rows if _is_cross_feature_value_bearing_row(row))
    value_bearing_family_counts = Counter(prompt_family(row) for row in rows if _is_value_bearing_measurement_row(row))
    cross_feature_value_bearing_family_counts = Counter(
        prompt_family(row) for row in rows if _is_cross_feature_value_bearing_row(row)
    )
    value_bearing_only_family_count = _predicate_only_family_count(rows, _is_value_bearing_measurement_row)
    cross_feature_only_family_count = _predicate_only_family_count(rows, _is_cross_feature_value_bearing_row)
    minimum_value_bearing_share_from_family_floor = min(
        1.0,
        value_bearing_only_family_count * profile.min_prompt_family_share,
    )
    minimum_cross_feature_share_from_family_floor = min(
        1.0,
        cross_feature_only_family_count * profile.min_prompt_family_share,
    )
    largest_prompt_family, largest_prompt_family_count = _largest_counter_item(prompt_family_counts)
    largest_prompt_template, largest_prompt_template_count = _largest_counter_item(prompt_template_counts)
    largest_prompt_family_share = largest_prompt_family_count / row_count if row_count else 0.0
    largest_prompt_template_share = largest_prompt_template_count / row_count if row_count else 0.0
    prompt_family_share_reports = _counter_share_reports(prompt_family_counts, row_count)
    underrepresented_prompt_families = [
        report for report in prompt_family_share_reports if report["share"] < profile.min_prompt_family_share
    ]
    overrepresented_prompt_families = [
        report for report in prompt_family_share_reports if report["share"] > profile.max_prompt_family_share
    ]
    geometry_hop_positive_share = geometry_hop_positive_count / row_count if row_count else 0.0
    logical_hop_ge_3_share = logical_hop_ge_3_count / row_count if row_count else 0.0
    geometry_critical_share = geometry_critical_count / row_count if row_count else 0.0
    syntax_only_calibration_share = syntax_only_calibration_count / row_count if row_count else 0.0
    value_bearing_measurement_share = value_bearing_measurement_count / row_count if row_count else 0.0
    cross_feature_value_bearing_share = cross_feature_value_bearing_count / row_count if row_count else 0.0
    minimum_value_bearing_measurement_count = _minimum_count_for_share(
        row_count,
        profile.min_value_bearing_measurement_share,
    )
    maximum_value_bearing_measurement_count = _maximum_count_for_share(
        row_count,
        profile.max_value_bearing_measurement_share,
    )
    minimum_cross_feature_value_bearing_share_count = _minimum_count_for_share(
        row_count,
        profile.min_cross_feature_value_bearing_share,
    )
    minimum_cross_feature_value_bearing_count = max(
        profile.min_cross_feature_value_bearing_count,
        minimum_cross_feature_value_bearing_share_count or 0,
    )
    maximum_cross_feature_value_bearing_count = _maximum_count_for_share(
        row_count,
        profile.max_cross_feature_value_bearing_share,
    )
    pre_final_candidate_counts = _pre_final_candidate_counts(rows)
    minimum_pre_final_candidate_count = min(pre_final_candidate_counts) if pre_final_candidate_counts else 0
    median_pre_final_candidate_count = _median(pre_final_candidate_counts)
    applicable = row_count >= profile.min_applicable_rows
    answer_entropy_bits = _entropy_bits(answer_counts)
    answer_identity_counts_by_format = _answer_identity_counts_by_format(rows)
    answer_entropy_by_format = _answer_entropy_by_format(answer_identity_counts_by_format)
    answer_entropy_capacity_bits = _answer_entropy_capacity_bits(answer_identity_counts_by_format)
    prompt_family_count = len(prompt_family_counts)
    prompt_template_count = len(prompt_template_counts)
    unique_answer_count = len(answer_counts)
    return {
        "row_count": row_count,
        "release_tier": profile.name,
        "release_gate_profile": release_gate_profile_report(profile),
        "applicable": applicable,
        "minimum_applicable_rows": profile.min_applicable_rows,
        "distinct_cad_model_count": distinct_cad_model_count,
        "minimum_distinct_cad_model_count": minimum_distinct_cad_model_count,
        "minimum_distinct_cad_model_share": profile.min_distinct_cad_model_share,
        "cad_model_identity_scope": "source_metadata cad_model_id/source_model_id/model_id, else source_id",
        "passes_distinct_cad_model_coverage": (
            None
            if not applicable or minimum_distinct_cad_model_count is None
            else distinct_cad_model_count >= minimum_distinct_cad_model_count
        ),
        "prompt_family_counts": dict(sorted(prompt_family_counts.items())),
        "prompt_family_count": prompt_family_count,
        "minimum_prompt_family_count": profile.min_prompt_family_count,
        "largest_prompt_family": largest_prompt_family,
        "largest_prompt_family_count": largest_prompt_family_count,
        "largest_prompt_family_share": largest_prompt_family_share,
        "minimum_prompt_family_share": profile.min_prompt_family_share,
        "maximum_prompt_family_share": profile.max_prompt_family_share,
        "underrepresented_prompt_families": underrepresented_prompt_families,
        "overrepresented_prompt_families": overrepresented_prompt_families,
        "passes_prompt_family_balance": (
            None
            if not applicable
            else prompt_family_count >= profile.min_prompt_family_count
            and not underrepresented_prompt_families
            and not overrepresented_prompt_families
        ),
        "prompt_template_counts": dict(sorted(prompt_template_counts.items())),
        "prompt_template_count": prompt_template_count,
        "minimum_prompt_template_count": profile.min_prompt_template_count,
        "largest_prompt_template": largest_prompt_template,
        "largest_prompt_template_count": largest_prompt_template_count,
        "largest_prompt_template_share": largest_prompt_template_share,
        "maximum_prompt_template_share": profile.max_prompt_template_share,
        "passes_prompt_template_balance": (
            None
            if not applicable
            else prompt_template_count >= profile.min_prompt_template_count
            and largest_prompt_template_share <= profile.max_prompt_template_share
        ),
        "unique_answer_count": unique_answer_count,
        "answer_identity_scope": "source_scoped_for_entity_id_raw_public_answer_otherwise",
        "answer_format_counts": dict(sorted(answer_format_counts.items())),
        "answer_entropy_by_format": answer_entropy_by_format,
        "minimum_unique_answer_count": profile.min_unique_answer_count,
        "answer_entropy_bits": answer_entropy_bits,
        "answer_entropy_capacity_bits": answer_entropy_capacity_bits,
        "answer_entropy_capacity_scope": "maximum entropy with current answer_format counts and observed public answer identities",
        "passes_answer_entropy_capacity": (
            None
            if not applicable
            else unique_answer_count >= profile.min_unique_answer_count
            and answer_entropy_capacity_bits >= profile.min_answer_entropy_bits
        ),
        "minimum_answer_entropy_bits": profile.min_answer_entropy_bits,
        "passes_answer_entropy": (
            None
            if not applicable
            else unique_answer_count >= profile.min_unique_answer_count
            and answer_entropy_bits >= profile.min_answer_entropy_bits
        ),
        "static_hop_counts": _int_counter(rows, "static_hop_count"),
        "geometry_hop_counts": _int_counter(rows, "geometry_hop_count"),
        "logical_hop_counts": _int_counter(rows, "logical_hop_count"),
        "geometry_hop_positive_count": geometry_hop_positive_count,
        "geometry_hop_positive_share": geometry_hop_positive_share,
        "minimum_geometry_hop_positive_share": profile.min_geometry_hop_positive_share,
        "logical_hop_ge_3_count": logical_hop_ge_3_count,
        "logical_hop_ge_3_share": logical_hop_ge_3_share,
        "minimum_logical_hop_ge_3_share": profile.min_logical_hop_ge_3_share,
        "geometry_critical_count": geometry_critical_count,
        "geometry_critical_share": geometry_critical_share,
        "syntax_only_calibration_count": syntax_only_calibration_count,
        "syntax_only_calibration_share": syntax_only_calibration_share,
        "value_bearing_measurement_count": value_bearing_measurement_count,
        "value_bearing_measurement_share": value_bearing_measurement_share,
        "value_bearing_prompt_family_counts": dict(sorted(value_bearing_family_counts.items())),
        "value_bearing_prompt_family_shares": _counter_share_reports(value_bearing_family_counts, row_count),
        "value_bearing_only_prompt_family_count": value_bearing_only_family_count,
        "minimum_value_bearing_share_from_family_floor": minimum_value_bearing_share_from_family_floor,
        "value_bearing_family_floor_feasible": (
            profile.max_value_bearing_measurement_share is None
            or minimum_value_bearing_share_from_family_floor <= profile.max_value_bearing_measurement_share
        ),
        "minimum_value_bearing_measurement_count": minimum_value_bearing_measurement_count,
        "value_bearing_measurement_deficit_count": max(
            0,
            minimum_value_bearing_measurement_count - value_bearing_measurement_count,
        ),
        "maximum_value_bearing_measurement_count": maximum_value_bearing_measurement_count,
        "value_bearing_measurement_excess_count": (
            None
            if maximum_value_bearing_measurement_count is None
            else max(0, value_bearing_measurement_count - maximum_value_bearing_measurement_count)
        ),
        "minimum_value_bearing_measurement_share": profile.min_value_bearing_measurement_share,
        "maximum_value_bearing_measurement_share": profile.max_value_bearing_measurement_share,
        "cross_feature_value_bearing_count": cross_feature_value_bearing_count,
        "cross_feature_value_bearing_share": cross_feature_value_bearing_share,
        "cross_feature_value_bearing_prompt_family_counts": dict(sorted(cross_feature_value_bearing_family_counts.items())),
        "cross_feature_value_bearing_prompt_family_shares": _counter_share_reports(
            cross_feature_value_bearing_family_counts,
            row_count,
        ),
        "cross_feature_only_prompt_family_count": cross_feature_only_family_count,
        "minimum_cross_feature_share_from_family_floor": minimum_cross_feature_share_from_family_floor,
        "cross_feature_family_floor_feasible": (
            profile.max_cross_feature_value_bearing_share is None
            or minimum_cross_feature_share_from_family_floor <= profile.max_cross_feature_value_bearing_share
        ),
        "minimum_cross_feature_value_bearing_count": minimum_cross_feature_value_bearing_count,
        "minimum_cross_feature_value_bearing_count_floor": profile.min_cross_feature_value_bearing_count,
        "minimum_cross_feature_value_bearing_share_count": minimum_cross_feature_value_bearing_share_count,
        "cross_feature_value_bearing_deficit_count": max(
            0,
            minimum_cross_feature_value_bearing_count - cross_feature_value_bearing_count,
        ),
        "maximum_cross_feature_value_bearing_count": maximum_cross_feature_value_bearing_count,
        "cross_feature_value_bearing_excess_count": (
            None
            if maximum_cross_feature_value_bearing_count is None
            else max(0, cross_feature_value_bearing_count - maximum_cross_feature_value_bearing_count)
        ),
        "minimum_cross_feature_value_bearing_share": profile.min_cross_feature_value_bearing_share,
        "maximum_cross_feature_value_bearing_share": profile.max_cross_feature_value_bearing_share,
        "pre_final_candidate_counts": _candidate_breadth_summary(pre_final_candidate_counts),
        "minimum_pre_final_candidate_count": minimum_pre_final_candidate_count,
        "minimum_required_pre_final_candidate_count": profile.min_pre_final_candidate_count,
        "median_pre_final_candidate_count": median_pre_final_candidate_count,
        "minimum_required_median_pre_final_candidate_count": profile.min_median_pre_final_candidate_count,
        "measurement_value_policy": {
            "value_bucket_decimals": VALUE_BUCKET_DECIMALS,
            "value_match_tolerance": VALUE_MATCH_TOLERANCE,
        },
        "maximum_syntax_only_calibration_share": profile.max_syntax_only_calibration_share,
        "passes_geometry_hop_coverage": (
            None
            if not applicable
            else geometry_hop_positive_share >= profile.min_geometry_hop_positive_share
        ),
        "passes_main_browsecomp_hop_coverage": (
            None
            if not applicable
            else True
            if profile.min_logical_hop_ge_3_share is None
            else logical_hop_ge_3_share >= profile.min_logical_hop_ge_3_share
        ),
        "passes_syntax_only_calibration_cap": (
            None
            if not applicable
            else syntax_only_calibration_share <= profile.max_syntax_only_calibration_share
        ),
        "passes_value_bearing_measurement_coverage": (
            None
            if not applicable
            else value_bearing_measurement_share >= profile.min_value_bearing_measurement_share
            and (
                profile.max_value_bearing_measurement_share is None
                or value_bearing_measurement_share <= profile.max_value_bearing_measurement_share
            )
        ),
        "passes_cross_feature_value_bearing_coverage": (
            None
            if not applicable
            else cross_feature_value_bearing_count >= profile.min_cross_feature_value_bearing_count
            and (
                profile.min_cross_feature_value_bearing_share is None
                or cross_feature_value_bearing_share >= profile.min_cross_feature_value_bearing_share
            )
            and (
                profile.max_cross_feature_value_bearing_share is None
                or cross_feature_value_bearing_share <= profile.max_cross_feature_value_bearing_share
            )
        ),
        "passes_candidate_breadth": (
            None
            if not applicable
            else True
            if profile.min_pre_final_candidate_count is None
            and profile.min_median_pre_final_candidate_count is None
            else bool(pre_final_candidate_counts)
            and minimum_pre_final_candidate_count >= (profile.min_pre_final_candidate_count or 0)
            and median_pre_final_candidate_count >= (profile.min_median_pre_final_candidate_count or 0.0)
        ),
    }


def release_verifier_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CAD-QA Release Verifier Report",
        "",
        f"- Rows: {report['row_count']}",
        f"- Release tier: {report.get('release_tier', DEFAULT_RELEASE_TIER)}",
        f"- Valid for release: {str(report['valid_for_release']).lower()}",
        f"- Blocking gates: {report['blocking_gates']}",
        "",
        "## Stop Gates",
        "",
        _json_block(report["stop_gates"]),
        "",
        "## Dataset",
        "",
        _json_block(
            {
                "hop_counts": report["dataset"].get("hop_counts", {}),
                "difficulty_buckets": report["dataset"].get("difficulty_buckets", {}),
                "relation_families": report["dataset"].get("relation_families", {}),
                "measurement_scopes": report["dataset"].get("measurement_scopes", {}),
                "evidence_tiers": report["dataset"].get("evidence_tiers", {}),
                "prompt_families": report["dataset"].get("prompt_families", {}),
                "prompt_template_ids": report["dataset"].get("prompt_template_ids", {}),
                "quality_flags": report["dataset"].get("quality_flags", {}),
                "measurement_value_policy": report["dataset"].get("measurement_value_policy", {}),
                "release_ready": report["dataset"].get("release_ready", {}),
            }
        ),
        "",
        "## Release Balance",
        "",
        _json_block(report["release_balance"]),
        "",
        "## Intended Family Coverage",
        "",
        _json_block(report["intended_family_coverage"]),
        "",
        "## Intended Family Share Feasibility",
        "",
        _json_block(report["intended_family_share_feasibility"]),
        "",
        "## Parameter Balance",
        "",
        _json_block(report["parameter_balance"]),
        "",
        "## Preview Evidence",
        "",
        _json_block(report["preview_evidence"]),
        "",
        "## Family Test Evidence",
        "",
        _json_block(report["family_test_evidence"]),
        "",
        "## Shortcut Resistance",
        "",
        _json_block(
            {
                "geometry_hop_counts": report["shortcut_resistance"].get("geometry_hop_counts", {}),
                "geometry_hop_positive_share": report["shortcut_resistance"].get(
                    "geometry_hop_positive_share",
                    0.0,
                ),
                "geometry_critical_share": report["shortcut_resistance"].get("geometry_critical_share", 0.0),
                "syntax_only_calibration_share": report["shortcut_resistance"].get(
                    "syntax_only_calibration_share",
                    0.0,
                ),
                "zero_geometry_hop_families": report["shortcut_resistance"].get(
                    "zero_geometry_hop_families",
                    [],
                ),
                "low_geometry_critical_families": report["shortcut_resistance"].get(
                    "low_geometry_critical_families",
                    [],
                ),
                "weakest_geometry_critical_families": report["shortcut_resistance"].get(
                    "weakest_geometry_critical_families",
                    [],
                ),
            }
        ),
        "",
        "## Quarantine",
        "",
        _json_block(report["quarantine"]),
        "",
        "## Training Readiness",
        "",
        _json_block(report["training_readiness"]),
        "",
        "## Verifier Failures",
        "",
        _json_block(report["failure_report"]),
        "",
        "## Validation",
        "",
        _json_block(
            {
                "validation": report["validation"],
                "release_validation": report["release_validation"],
                "split_audit": report["split_audit"],
                "leakage_audit": report["leakage_audit"],
                "public_private_audit": report.get("public_private_audit"),
            }
        ),
        "",
    ]
    return "\n".join(lines)


def write_release_verifier_report(
    dataset_dir: Path,
    *,
    out: Path | None = None,
    release_tier: str = DEFAULT_RELEASE_TIER,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
    preview_evidence: Path | None = None,
    family_test_evidence: Path | None = DEFAULT_FAMILY_TEST_EVIDENCE,
) -> dict[str, Any]:
    rows = read_records(existing_record_artifact_path(dataset_dir, "rows"))
    failure_path = existing_record_artifact_path(dataset_dir, "failure_manifest")
    failures = read_records(failure_path) if failure_path.exists() else []
    split_path = dataset_dir / "split_manifest.json"
    split = json.loads(split_path.read_text(encoding="utf-8")) if split_path.exists() else None
    public_path = existing_record_artifact_path(dataset_dir, "public")
    private_path = existing_record_artifact_path(dataset_dir, "private")
    public = read_records(public_path) if public_path.exists() else None
    private = read_records(private_path) if private_path.exists() else None
    preview_evidence_path = preview_evidence or dataset_dir / DEFAULT_PREVIEW_EVIDENCE_FILENAME
    preview_evidence_payload = (
        json.loads(preview_evidence_path.read_text(encoding="utf-8"))
        if preview_evidence_path.exists()
        else None
    )
    report = release_verifier_report(
        rows,
        failures=failures,
        split=split,
        public_rows=public,
        private_rows=private,
        release_tier=release_tier,
        family_manifest=family_manifest,
        preview_evidence=preview_evidence_payload,
        family_test_evidence=family_test_evidence,
    )
    output_dir = out or dataset_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "release_verifier_report.json", report)
    (output_dir / "RELEASE_VERIFIER_REPORT.md").write_text(release_verifier_markdown(report), encoding="utf-8")
    return report


def release_gate_profile(release_tier: str | ReleaseGateProfile) -> ReleaseGateProfile:
    if isinstance(release_tier, ReleaseGateProfile):
        return release_tier
    try:
        return RELEASE_GATE_PROFILES[release_tier]
    except KeyError as exc:
        raise ValueError(f"unknown release tier: {release_tier}") from exc


def release_gate_profile_report(profile: ReleaseGateProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "min_applicable_rows": profile.min_applicable_rows,
        "min_release_rows": profile.min_release_rows,
        "min_distinct_cad_model_share": profile.min_distinct_cad_model_share,
        "min_default_sft_rows": profile.min_default_sft_rows,
        "max_default_sft_syntax_only_share": profile.max_default_sft_syntax_only_share,
        "min_prompt_family_count": profile.min_prompt_family_count,
        "min_prompt_family_share": profile.min_prompt_family_share,
        "max_prompt_family_share": profile.max_prompt_family_share,
        "min_prompt_template_count": profile.min_prompt_template_count,
        "max_prompt_template_share": profile.max_prompt_template_share,
        "min_unique_answer_count": profile.min_unique_answer_count,
        "min_answer_entropy_bits": profile.min_answer_entropy_bits,
        "min_geometry_hop_positive_share": profile.min_geometry_hop_positive_share,
        "max_syntax_only_calibration_share": profile.max_syntax_only_calibration_share,
        "min_geometry_critical_training_share": profile.min_geometry_critical_training_share,
        "min_logical_hop_ge_3_share": profile.min_logical_hop_ge_3_share,
        "min_value_bearing_measurement_share": profile.min_value_bearing_measurement_share,
        "max_value_bearing_measurement_share": profile.max_value_bearing_measurement_share,
        "min_cross_feature_value_bearing_count": profile.min_cross_feature_value_bearing_count,
        "min_cross_feature_value_bearing_share": profile.min_cross_feature_value_bearing_share,
        "max_cross_feature_value_bearing_share": profile.max_cross_feature_value_bearing_share,
        "min_pre_final_candidate_count": profile.min_pre_final_candidate_count,
        "min_median_pre_final_candidate_count": profile.min_median_pre_final_candidate_count,
        "min_split_groups_per_split": profile.min_split_groups_per_split,
        "enforce_intended_family_coverage": profile.enforce_intended_family_coverage,
        "enforce_parameter_balance": profile.enforce_parameter_balance,
        "max_parameter_value_share": profile.max_parameter_value_share,
        "min_axis_direction_parameter_share": profile.min_axis_direction_parameter_share,
        "enforce_preview_evidence": profile.enforce_preview_evidence,
        "min_preview_samples_per_family": profile.min_preview_samples_per_family,
        "enforce_family_test_evidence": profile.enforce_family_test_evidence,
    }


def intended_family_share_feasibility_report(
    intended_family_coverage: dict[str, Any],
    profile: ReleaseGateProfile | str = DEFAULT_RELEASE_TIER,
) -> dict[str, Any]:
    """Report whether intended release-family count can satisfy family-share gates."""

    profile = release_gate_profile(profile)
    intended_count = int(intended_family_coverage.get("intended_release_family_count") or 0)
    minimum_feasible_count = max(
        profile.min_prompt_family_count,
        math.ceil((1.0 - 1e-12) / profile.max_prompt_family_share),
    )
    maximum_feasible_count = math.floor((1.0 + 1e-12) / profile.min_prompt_family_share)
    violations = []
    if intended_count < minimum_feasible_count:
        violations.append(
            {
                "reason": "too_few_intended_release_families_for_share_band",
                "intended_release_family_count": intended_count,
                "minimum_feasible_release_family_count": minimum_feasible_count,
                "minimum_prompt_family_count": profile.min_prompt_family_count,
                "maximum_prompt_family_share": profile.max_prompt_family_share,
            }
        )
    if intended_count > maximum_feasible_count:
        violations.append(
            {
                "reason": "too_many_intended_release_families_for_share_band",
                "intended_release_family_count": intended_count,
                "maximum_feasible_release_family_count": maximum_feasible_count,
                "minimum_prompt_family_share": profile.min_prompt_family_share,
            }
        )
    return {
        "valid": not violations if profile.enforce_intended_family_coverage else True,
        "enforced": profile.enforce_intended_family_coverage,
        "release_tier": profile.name,
        "intended_release_family_count": intended_count,
        "minimum_feasible_release_family_count": minimum_feasible_count,
        "maximum_feasible_release_family_count": maximum_feasible_count,
        "minimum_prompt_family_share": profile.min_prompt_family_share,
        "maximum_prompt_family_share": profile.max_prompt_family_share,
        "violations": violations,
    }


def _passes_minimum_count(count: int, minimum: int | None) -> bool:
    if minimum is None:
        return True
    return count >= minimum


def _minimum_distinct_cad_model_count(row_count: int, minimum_share: float) -> int:
    return math.ceil(row_count * minimum_share)


def _minimum_count_for_share(row_count: int, minimum_share: float | None) -> int:
    if minimum_share is None:
        return 0
    return math.ceil(row_count * minimum_share - 1e-12)


def _maximum_count_for_share(row_count: int, maximum_share: float | None) -> int | None:
    if maximum_share is None:
        return None
    return math.floor(row_count * maximum_share + 1e-12)


def _passes_split_group_coverage(split_quality: dict[str, Any], minimum: int | None) -> bool:
    if minimum is None:
        return True
    group_counts = split_quality.get("group_counts_by_split", {})
    return all(int(group_counts.get(split, 0) or 0) >= minimum for split in ("train", "validation", "test"))


def _json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"


def _answer_identity_key(row: dict[str, Any]) -> str:
    answer = row.get("gold_answer")
    if row.get("answer_format") == "entity_id":
        return json.dumps(
            {"source_id": row.get("source_id"), "gold_answer": answer},
            sort_keys=True,
            default=str,
        )
    return json.dumps(answer, sort_keys=True, default=str)


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


def _prompt_template_id(row: dict[str, Any]) -> str:
    template_id = row.get("prompt_template_id")
    if template_id:
        return str(template_id)
    query = row.get("query_program")
    if isinstance(query, dict):
        return prompt_template_id_from_mapping(query)
    return str(row.get("prompt_version", "unknown"))


def _is_value_bearing_measurement_row(row: dict[str, Any]) -> bool:
    query = row.get("query_program") or {}
    for clause in query.get("clauses", []):
        if (
            isinstance(clause, dict)
            and clause.get("kind") == "has_measurement"
            and clause.get("metric")
            and clause.get("value") is not None
        ):
            return True
    return False


def _is_cross_feature_value_bearing_row(row: dict[str, Any]) -> bool:
    query = row.get("query_program") or {}
    if query.get("aggregation_metric") == "distance_to_reference_feature_centroid":
        return True
    for clause in query.get("clauses", []):
        if isinstance(clause, dict) and clause.get("kind") == "reference_measurement":
            return True
    return False


def _entropy_bits(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _answer_identity_counts_by_format(rows: list[dict[str, Any]]) -> dict[str, Counter[str]]:
    grouped: dict[str, Counter[str]] = {}
    for row in rows:
        answer_format = str(row.get("answer_format") or "unknown")
        grouped.setdefault(answer_format, Counter())[_answer_identity_key(row)] += 1
    return grouped


def _answer_entropy_by_format(grouped: dict[str, Counter[str]]) -> dict[str, dict[str, Any]]:
    return {
        answer_format: {
            "row_count": sum(counts.values()),
            "unique_answer_count": len(counts),
            "answer_entropy_bits": _entropy_bits(counts),
            "maximum_entropy_bits_with_observed_unique_answers": _max_entropy_for_count_unique(
                sum(counts.values()),
                len(counts),
            ),
            "top_answer_identities": [
                {"answer_identity": answer, "count": count}
                for answer, count in counts.most_common(10)
            ],
        }
        for answer_format, counts in sorted(grouped.items())
    }


def _answer_entropy_capacity_bits(grouped: dict[str, Counter[str]]) -> float:
    total = sum(sum(counts.values()) for counts in grouped.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for counts in grouped.values():
        row_count = sum(counts.values())
        unique_count = len(counts)
        for count in _even_distribution_counts(row_count, unique_count):
            probability = count / total
            entropy -= probability * math.log2(probability)
    return entropy


def _max_entropy_for_count_unique(row_count: int, unique_count: int) -> float:
    if row_count <= 0 or unique_count <= 0:
        return 0.0
    return _entropy_bits(Counter({str(index): count for index, count in enumerate(_even_distribution_counts(row_count, unique_count))}))


def _even_distribution_counts(row_count: int, unique_count: int) -> list[int]:
    if row_count <= 0 or unique_count <= 0:
        return []
    base, remainder = divmod(row_count, unique_count)
    return [base + 1] * remainder + [base] * (unique_count - remainder)


def _largest_counter_item(counts: Counter[str]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    item, count = max(counts.items(), key=lambda entry: (entry[1], entry[0]))
    return item, count


def _counter_share_reports(counts: Counter[str], total: int) -> list[dict[str, Any]]:
    return [
        {
            "prompt_family": key,
            "count": count,
            "share": count / total if total else 0.0,
        }
        for key, count in sorted(counts.items())
    ]


def _predicate_only_family_count(rows: list[dict[str, Any]], predicate: Any) -> int:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_family.setdefault(prompt_family(row), []).append(row)
    return sum(1 for family_rows in by_family.values() if family_rows and all(predicate(row) for row in family_rows))


def _pre_final_candidate_counts(rows: list[dict[str, Any]]) -> list[int]:
    counts = []
    for row in rows:
        if int(row.get("logical_hop_count") or 0) < 3:
            continue
        trace = row.get("candidate_trace") or {}
        steps = trace.get("steps") or []
        for step in steps:
            if step.get("step") == "aggregation":
                before = step.get("before") or []
                if isinstance(before, list):
                    counts.append(len(before))
                break
    return counts


def _candidate_breadth_summary(counts: list[int]) -> dict[str, Any]:
    if not counts:
        return {"count": 0, "min": 0, "median": 0.0}
    return {
        "count": len(counts),
        "min": min(counts),
        "median": _median(counts),
    }


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _int_counter(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(int(row.get(key) or 0)) for row in rows)
    return dict(sorted(counts.items(), key=lambda item: int(item[0])))


def _passes_geometry_critical_family_coverage(shortcut_resistance: dict[str, Any]) -> bool:
    low_critical = set(shortcut_resistance.get("low_geometry_critical_families", []))
    syntax_only = set(shortcut_resistance.get("syntax_only_families", []))
    return not (low_critical - syntax_only)
