"""Release-scale verifier and quarantine reports."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.dataset.audit import leakage_audit
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
from cad_qa.io import read_jsonl, write_json
from cad_qa.prompts.render import prompt_template_id_from_mapping

MIN_RELEASE_BALANCE_ROWS = 20
MIN_PROMPT_FAMILY_COUNT = 4
MAX_PROMPT_FAMILY_SHARE = 0.35
MIN_PROMPT_TEMPLATE_COUNT = 4
MAX_PROMPT_TEMPLATE_SHARE = 0.35
MIN_UNIQUE_ANSWER_COUNT = 8
MIN_ANSWER_ENTROPY_BITS = 2.0
MIN_GEOMETRY_HOP_POSITIVE_SHARE = 0.75
MAX_SYNTAX_ONLY_CALIBRATION_SHARE = 0.10


def release_verifier_report(
    rows: list[dict[str, Any]],
    *,
    failures: list[dict[str, Any]] | None = None,
    split: dict[str, Any] | None = None,
    public_rows: list[dict[str, Any]] | None = None,
    private_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate release-readiness gates and verifier/quarantine taxonomy."""

    split = split or split_manifest(rows)
    dataset = dataset_report(rows)
    validation = validate_rows(rows)
    release_validation = validate_rows(rows, release=True)
    leakage = leakage_audit(rows, split)
    split_quality = split_audit(rows, split)
    quarantine = quarantine_report(rows)
    training_readiness = training_readiness_report(rows)
    release_balance = release_balance_report(rows)
    shortcut_resistance = dataset["shortcut_resistance"]
    failures_by_reason = failure_report(failures or [])
    public_private = public_private_audit(public_rows, private_rows) if public_rows is not None and private_rows is not None else None
    stop_gates = {
        "row_validation": validation["valid"],
        "release_validation": release_validation["valid"],
        "group_safe_split_audit": split_quality["valid"],
        "leakage_audit": leakage["valid"],
        "no_quarantined_rows": quarantine["quarantine_count"] == 0,
        "default_sft_geometry_critical_dominance": training_readiness["passes_geometry_critical_dominance"],
        "prompt_family_balance": release_balance["passes_prompt_family_balance"],
        "prompt_template_balance": release_balance["passes_prompt_template_balance"],
        "answer_entropy": release_balance["passes_answer_entropy"],
        "geometry_hop_coverage": release_balance["passes_geometry_hop_coverage"],
        "syntax_only_calibration_cap": release_balance["passes_syntax_only_calibration_cap"],
        "geometry_critical_prompt_family_coverage": _passes_geometry_critical_family_coverage(
            shortcut_resistance
        ),
        "public_private_audit": public_private["valid"] if public_private is not None else None,
    }
    blocking = [name for name, passed in stop_gates.items() if passed is False]
    return {
        "row_count": len(rows),
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
        "shortcut_resistance": shortcut_resistance,
        "failure_report": failures_by_reason,
        "split_manifest": split,
        "public_private_audit": public_private,
    }


def release_balance_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize release composition checks that catch shortcut-heavy datasets."""

    row_count = len(rows)
    prompt_family_counts = Counter(prompt_family(row) for row in rows)
    prompt_template_counts = Counter(_prompt_template_id(row) for row in rows)
    answer_counts = Counter(_answer_key(row.get("gold_answer")) for row in rows)
    geometry_hop_positive_count = sum(1 for row in rows if int(row.get("geometry_hop_count") or 0) > 0)
    geometry_critical_count = sum(1 for row in rows if is_geometry_critical_row(row))
    syntax_only_calibration_count = sum(1 for row in rows if is_syntax_only_calibration_row(row))
    value_bearing_measurement_count = sum(1 for row in rows if _is_value_bearing_measurement_row(row))
    largest_prompt_family, largest_prompt_family_count = _largest_counter_item(prompt_family_counts)
    largest_prompt_template, largest_prompt_template_count = _largest_counter_item(prompt_template_counts)
    largest_prompt_family_share = largest_prompt_family_count / row_count if row_count else 0.0
    largest_prompt_template_share = largest_prompt_template_count / row_count if row_count else 0.0
    geometry_hop_positive_share = geometry_hop_positive_count / row_count if row_count else 0.0
    geometry_critical_share = geometry_critical_count / row_count if row_count else 0.0
    syntax_only_calibration_share = syntax_only_calibration_count / row_count if row_count else 0.0
    value_bearing_measurement_share = value_bearing_measurement_count / row_count if row_count else 0.0
    applicable = row_count >= MIN_RELEASE_BALANCE_ROWS
    answer_entropy_bits = _entropy_bits(answer_counts)
    prompt_family_count = len(prompt_family_counts)
    prompt_template_count = len(prompt_template_counts)
    unique_answer_count = len(answer_counts)
    return {
        "row_count": row_count,
        "applicable": applicable,
        "minimum_applicable_rows": MIN_RELEASE_BALANCE_ROWS,
        "prompt_family_counts": dict(sorted(prompt_family_counts.items())),
        "prompt_family_count": prompt_family_count,
        "minimum_prompt_family_count": MIN_PROMPT_FAMILY_COUNT,
        "largest_prompt_family": largest_prompt_family,
        "largest_prompt_family_count": largest_prompt_family_count,
        "largest_prompt_family_share": largest_prompt_family_share,
        "maximum_prompt_family_share": MAX_PROMPT_FAMILY_SHARE,
        "passes_prompt_family_balance": (
            None
            if not applicable
            else prompt_family_count >= MIN_PROMPT_FAMILY_COUNT
            and largest_prompt_family_share <= MAX_PROMPT_FAMILY_SHARE
        ),
        "prompt_template_counts": dict(sorted(prompt_template_counts.items())),
        "prompt_template_count": prompt_template_count,
        "minimum_prompt_template_count": MIN_PROMPT_TEMPLATE_COUNT,
        "largest_prompt_template": largest_prompt_template,
        "largest_prompt_template_count": largest_prompt_template_count,
        "largest_prompt_template_share": largest_prompt_template_share,
        "maximum_prompt_template_share": MAX_PROMPT_TEMPLATE_SHARE,
        "passes_prompt_template_balance": (
            None
            if not applicable
            else prompt_template_count >= MIN_PROMPT_TEMPLATE_COUNT
            and largest_prompt_template_share <= MAX_PROMPT_TEMPLATE_SHARE
        ),
        "unique_answer_count": unique_answer_count,
        "minimum_unique_answer_count": MIN_UNIQUE_ANSWER_COUNT,
        "answer_entropy_bits": answer_entropy_bits,
        "minimum_answer_entropy_bits": MIN_ANSWER_ENTROPY_BITS,
        "passes_answer_entropy": (
            None
            if not applicable
            else unique_answer_count >= MIN_UNIQUE_ANSWER_COUNT
            and answer_entropy_bits >= MIN_ANSWER_ENTROPY_BITS
        ),
        "static_hop_counts": _int_counter(rows, "static_hop_count"),
        "geometry_hop_counts": _int_counter(rows, "geometry_hop_count"),
        "geometry_hop_positive_count": geometry_hop_positive_count,
        "geometry_hop_positive_share": geometry_hop_positive_share,
        "minimum_geometry_hop_positive_share": MIN_GEOMETRY_HOP_POSITIVE_SHARE,
        "geometry_critical_count": geometry_critical_count,
        "geometry_critical_share": geometry_critical_share,
        "syntax_only_calibration_count": syntax_only_calibration_count,
        "syntax_only_calibration_share": syntax_only_calibration_share,
        "value_bearing_measurement_count": value_bearing_measurement_count,
        "value_bearing_measurement_share": value_bearing_measurement_share,
        "maximum_syntax_only_calibration_share": MAX_SYNTAX_ONLY_CALIBRATION_SHARE,
        "passes_geometry_hop_coverage": (
            None
            if not applicable
            else geometry_hop_positive_share >= MIN_GEOMETRY_HOP_POSITIVE_SHARE
        ),
        "passes_syntax_only_calibration_cap": (
            None
            if not applicable
            else syntax_only_calibration_share <= MAX_SYNTAX_ONLY_CALIBRATION_SHARE
        ),
    }


def release_verifier_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CAD-QA Release Verifier Report",
        "",
        f"- Rows: {report['row_count']}",
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
                "release_ready": report["dataset"].get("release_ready", {}),
            }
        ),
        "",
        "## Release Balance",
        "",
        _json_block(report["release_balance"]),
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
) -> dict[str, Any]:
    rows = read_jsonl(dataset_dir / "rows.jsonl")
    failure_path = dataset_dir / "failure_manifest.jsonl"
    failures = read_jsonl(failure_path) if failure_path.exists() else []
    split_path = dataset_dir / "split_manifest.json"
    split = json.loads(split_path.read_text(encoding="utf-8")) if split_path.exists() else None
    public_path = dataset_dir / "public.jsonl"
    private_path = dataset_dir / "private.jsonl"
    public = read_jsonl(public_path) if public_path.exists() else None
    private = read_jsonl(private_path) if private_path.exists() else None
    report = release_verifier_report(
        rows,
        failures=failures,
        split=split,
        public_rows=public,
        private_rows=private,
    )
    output_dir = out or dataset_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "release_verifier_report.json", report)
    (output_dir / "RELEASE_VERIFIER_REPORT.md").write_text(release_verifier_markdown(report), encoding="utf-8")
    return report


def _json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"


def _answer_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


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


def _entropy_bits(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _largest_counter_item(counts: Counter[str]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    item, count = max(counts.items(), key=lambda entry: (entry[1], entry[0]))
    return item, count


def _int_counter(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(int(row.get(key) or 0)) for row in rows)
    return dict(sorted(counts.items(), key=lambda item: int(item[0])))


def _passes_geometry_critical_family_coverage(shortcut_resistance: dict[str, Any]) -> bool:
    low_critical = set(shortcut_resistance.get("low_geometry_critical_families", []))
    syntax_only = set(shortcut_resistance.get("syntax_only_families", []))
    return not (low_critical - syntax_only)
