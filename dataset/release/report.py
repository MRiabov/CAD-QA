"""Dataset reporting helpers."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from dataset.release.sft import is_geometry_critical_row, is_syntax_only_calibration_row, prompt_family
from dataset.prompts.render import prompt_template_id_from_mapping
from dataset.query.resolver import VALUE_BUCKET_DECIMALS, VALUE_MATCH_TOLERANCE


def dataset_report(rows: list[Any]) -> dict[str, Any]:
    hop_counts: Counter[str] = Counter()
    difficulty_buckets: Counter[str] = Counter()
    relation_families: Counter[str] = Counter()
    measurement_scopes: Counter[str] = Counter()
    verifier_statuses: Counter[str] = Counter()
    answer_formats: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    evidence_tiers: Counter[str] = Counter()
    quarantine_reasons: Counter[str] = Counter()
    release_ready: Counter[str] = Counter()
    prompt_families: Counter[str] = Counter()
    prompt_template_ids: Counter[str] = Counter()
    quality_flags: Counter[str] = Counter()
    for row in rows:
        item = row if isinstance(row, dict) else row.__dict__
        hop_counts[str(item["logical_hop_count"])] += 1
        difficulty_buckets[item["difficulty_bucket"]] += 1
        verifier_statuses[item["verifier_status"]] += 1
        answer_formats[item["answer_format"]] += 1
        if "split" in item:
            split_counts[item["split"]] += 1
        evidence_tiers[item.get("evidence_tier", "unknown")] += 1
        release_ready[str(bool(item.get("release_ready", False))).lower()] += 1
        quarantine_reasons.update(item.get("quarantine_reasons", []))
        relation_families.update(item.get("relation_families", []))
        measurement_scopes.update(item.get("measurement_scopes", []))
        family = prompt_family(item)
        prompt_families[family] += 1
        prompt_template_ids[_prompt_template_id(item)] += 1
        if is_syntax_only_calibration_row(item):
            quality_flags["syntax_only_calibration"] += 1
        if is_geometry_critical_row(item):
            quality_flags["geometry_critical"] += 1
        if _is_value_bearing_measurement_row(item):
            quality_flags["value_bearing_measurement"] += 1
        if _is_cross_feature_value_bearing_row(item):
            quality_flags["cross_feature_value_bearing"] += 1
    return {
        "row_count": len(rows),
        "hop_counts": dict(sorted(hop_counts.items())),
        "difficulty_buckets": dict(sorted(difficulty_buckets.items())),
        "relation_families": dict(sorted(relation_families.items())),
        "measurement_scopes": dict(sorted(measurement_scopes.items())),
        "verifier_statuses": dict(sorted(verifier_statuses.items())),
        "answer_formats": dict(sorted(answer_formats.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "evidence_tiers": dict(sorted(evidence_tiers.items())),
        "release_ready": dict(sorted(release_ready.items())),
        "quarantine_reasons": dict(sorted(quarantine_reasons.items())),
        "prompt_families": dict(sorted(prompt_families.items())),
        "prompt_template_ids": dict(sorted(prompt_template_ids.items())),
        "quality_flags": dict(sorted(quality_flags.items())),
        "measurement_value_policy": _measurement_value_policy(),
        "shortcut_resistance": shortcut_resistance_report(rows),
    }


def _measurement_value_policy() -> dict[str, Any]:
    return {
        "value_bucket_decimals": VALUE_BUCKET_DECIMALS,
        "value_match_tolerance": VALUE_MATCH_TOLERANCE,
    }


def shortcut_resistance_report(rows: list[Any]) -> dict[str, Any]:
    """Summarize shortcut risk by prompt family and geometry-hop coverage."""

    row_items = [_row_item(row) for row in rows]
    row_count = len(row_items)
    family_rows: dict[str, list[dict[str, Any]]] = {}
    for row in row_items:
        family_rows.setdefault(prompt_family(row), []).append(row)

    family_reports = {
        family: _shortcut_family_report(family, items, row_count)
        for family, items in sorted(family_rows.items())
    }
    zero_geometry_families = [
        family
        for family, report in family_reports.items()
        if report["row_count"] > 0 and report["geometry_hop_positive_count"] == 0
    ]
    syntax_only_families = [
        family
        for family, report in family_reports.items()
        if report["row_count"] > 0 and report["syntax_only_calibration_count"] == report["row_count"]
    ]
    low_geometry_coverage_families = [
        family
        for family, report in family_reports.items()
        if report["row_count"] > 0 and report["geometry_hop_positive_share"] < 1.0
    ]
    low_geometry_critical_families = [
        family
        for family, report in family_reports.items()
        if report["row_count"] > 0 and report["geometry_critical_share"] < 1.0
    ]
    weakest_geometry_hop_families = sorted(
        family_reports.values(),
        key=lambda report: (report["geometry_hop_positive_share"], -report["row_count"], report["prompt_family"]),
    )[:10]
    weakest_geometry_critical_families = sorted(
        family_reports.values(),
        key=lambda report: (report["geometry_critical_share"], -report["row_count"], report["prompt_family"]),
    )[:10]
    geometry_hop_positive_count = sum(
        report["geometry_hop_positive_count"] for report in family_reports.values()
    )
    geometry_critical_count = sum(report["geometry_critical_count"] for report in family_reports.values())
    syntax_only_calibration_count = sum(
        report["syntax_only_calibration_count"] for report in family_reports.values()
    )
    return {
        "row_count": row_count,
        "prompt_family_count": len(family_reports),
        "geometry_hop_counts": _counter_dict(_int_counter(row_items, "geometry_hop_count")),
        "static_hop_counts": _counter_dict(_int_counter(row_items, "static_hop_count")),
        "geometry_hop_positive_count": geometry_hop_positive_count,
        "geometry_hop_positive_share": _share(geometry_hop_positive_count, row_count),
        "geometry_critical_count": geometry_critical_count,
        "geometry_critical_share": _share(geometry_critical_count, row_count),
        "syntax_only_calibration_count": syntax_only_calibration_count,
        "syntax_only_calibration_share": _share(syntax_only_calibration_count, row_count),
        "zero_geometry_hop_families": zero_geometry_families,
        "syntax_only_families": syntax_only_families,
        "low_geometry_coverage_families": low_geometry_coverage_families,
        "low_geometry_critical_families": low_geometry_critical_families,
        "weakest_geometry_hop_families": [
            _family_report_summary(report) for report in weakest_geometry_hop_families
        ],
        "weakest_geometry_critical_families": [
            _family_report_summary(report) for report in weakest_geometry_critical_families
        ],
        "by_prompt_family": family_reports,
    }


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


def shortcut_resistance_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CAD-QA Shortcut Resistance Report",
        "",
        "## Summary",
        "",
        _json_block(
            {
                "row_count": report.get("row_count", 0),
                "prompt_family_count": report.get("prompt_family_count", 0),
                "geometry_hop_counts": report.get("geometry_hop_counts", {}),
                "static_hop_counts": report.get("static_hop_counts", {}),
                "geometry_hop_positive_share": report.get("geometry_hop_positive_share", 0.0),
                "geometry_critical_share": report.get("geometry_critical_share", 0.0),
                "syntax_only_calibration_share": report.get("syntax_only_calibration_share", 0.0),
                "zero_geometry_hop_families": report.get("zero_geometry_hop_families", []),
                "syntax_only_families": report.get("syntax_only_families", []),
                "low_geometry_coverage_families": report.get("low_geometry_coverage_families", []),
                "low_geometry_critical_families": report.get("low_geometry_critical_families", []),
            }
        ),
        "",
        "## Weakest Geometry-Hop Families",
        "",
        _json_block({"families": report.get("weakest_geometry_hop_families", [])}),
        "",
        "## Weakest Geometry-Critical Families",
        "",
        _json_block({"families": report.get("weakest_geometry_critical_families", [])}),
        "",
        "## By Prompt Family",
        "",
        _json_block(report.get("by_prompt_family", {})),
        "",
    ]
    return "\n".join(lines)


def failure_report(failures: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    graphs: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for failure in failures:
        trace = failure.get("candidate_trace", {})
        trace_reason = trace.get("failure_reason") if isinstance(trace, dict) else getattr(trace, "failure_reason", None)
        final_candidates = trace.get("final_candidates", []) if isinstance(trace, dict) else getattr(trace, "final_candidates", [])
        reason = failure.get("reason") or trace_reason or "unknown"
        graph_id = failure.get("graph_id", "unknown")
        reasons[reason] += 1
        graphs[graph_id] += 1
        if len(examples) < 10:
            examples.append(
                {
                    "graph_id": graph_id,
                    "query_id": failure.get("query_id"),
                    "reason": reason,
                    "final_candidates": final_candidates,
                }
            )
    return {
        "failure_count": len(failures),
        "reasons": dict(sorted(reasons.items())),
        "graphs_with_failures": dict(sorted(graphs.items())),
        "examples": examples,
    }


def dataset_card_markdown(
    *,
    dataset_path: Path,
    report: dict[str, Any],
    validation: dict[str, Any] | None = None,
    audit: dict[str, Any] | None = None,
    failures: dict[str, Any] | None = None,
) -> str:
    lines = [
        "# CAD-QA Graph Dataset Card",
        "",
        f"Dataset path: `{dataset_path}`",
        "",
        "## Framing",
        "",
        "Rows are public prompts rendered from hidden deterministic CAD graph query programs. Low-hop rows and high-hop BrowseComp-style rows share the same graph extraction, resolver, verifier, and materialization path.",
        "",
        "## Composition",
        "",
        _json_block(
            {
                "row_count": report.get("row_count", 0),
                "hop_counts": report.get("hop_counts", {}),
                "difficulty_buckets": report.get("difficulty_buckets", {}),
                "split_counts": report.get("split_counts", {}),
                "evidence_tiers": report.get("evidence_tiers", {}),
                "release_ready": report.get("release_ready", {}),
                "quarantine_reasons": report.get("quarantine_reasons", {}),
                "prompt_families": report.get("prompt_families", {}),
                "prompt_template_ids": report.get("prompt_template_ids", {}),
                "quality_flags": report.get("quality_flags", {}),
            }
        ),
        "",
        "## Shortcut Resistance",
        "",
        _json_block(
            {
                "geometry_hop_counts": report.get("shortcut_resistance", {}).get("geometry_hop_counts", {}),
                "static_hop_counts": report.get("shortcut_resistance", {}).get("static_hop_counts", {}),
                "geometry_hop_positive_share": report.get("shortcut_resistance", {}).get(
                    "geometry_hop_positive_share",
                    0.0,
                ),
                "geometry_critical_share": report.get("shortcut_resistance", {}).get(
                    "geometry_critical_share",
                    0.0,
                ),
                "syntax_only_calibration_share": report.get("shortcut_resistance", {}).get(
                    "syntax_only_calibration_share",
                    0.0,
                ),
                "zero_geometry_hop_families": report.get("shortcut_resistance", {}).get(
                    "zero_geometry_hop_families",
                    [],
                ),
                "low_geometry_critical_families": report.get("shortcut_resistance", {}).get(
                    "low_geometry_critical_families",
                    [],
                ),
                "weakest_geometry_hop_families": report.get("shortcut_resistance", {}).get(
                    "weakest_geometry_hop_families",
                    [],
                ),
                "weakest_geometry_critical_families": report.get("shortcut_resistance", {}).get(
                    "weakest_geometry_critical_families",
                    [],
                ),
            }
        ),
        "",
        "## Relation And Metric Families",
        "",
        _json_block(
            {
                "relation_families": report.get("relation_families", {}),
                "measurement_scopes": report.get("measurement_scopes", {}),
                "answer_formats": report.get("answer_formats", {}),
            }
        ),
    ]
    if validation is not None:
        lines.extend(["", "## Validation", "", _json_block(validation)])
    if audit is not None:
        lines.extend(["", "## Leakage Audit", "", _json_block(audit)])
    if failures is not None:
        lines.extend(["", "## Query Failure Manifest", "", _json_block(failures)])
    lines.extend(
        [
            "",
            "## Intended Use",
            "",
            "Use `public.parquet` or request exports for model input. Use `private.parquet`, hidden query programs, candidate traces, and verifier outputs only for dataset construction, auditing, grading, and error analysis.",
            "",
        ]
    )
    return "\n".join(lines)


def _json_block(value: dict[str, Any]) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"


def _row_item(row: Any) -> dict[str, Any]:
    return row if isinstance(row, dict) else row.__dict__


def _shortcut_family_report(
    family: str,
    rows: list[dict[str, Any]],
    total_rows: int,
) -> dict[str, Any]:
    row_count = len(rows)
    geometry_hop_positive_count = sum(1 for row in rows if int(row.get("geometry_hop_count") or 0) > 0)
    geometry_critical_count = sum(1 for row in rows if is_geometry_critical_row(row))
    syntax_only_calibration_count = sum(1 for row in rows if is_syntax_only_calibration_row(row))
    release_ready_count = sum(
        1
        for row in rows
        if row.get("release_ready") is not False and not row.get("quarantine_reasons")
    )
    unique_answer_count = len({_answer_key(row.get("gold_answer")) for row in rows})
    return {
        "prompt_family": family,
        "row_count": row_count,
        "row_share": _share(row_count, total_rows),
        "static_hop_counts": _counter_dict(_int_counter(rows, "static_hop_count")),
        "geometry_hop_counts": _counter_dict(_int_counter(rows, "geometry_hop_count")),
        "geometry_hop_positive_count": geometry_hop_positive_count,
        "geometry_hop_positive_share": _share(geometry_hop_positive_count, row_count),
        "geometry_critical_count": geometry_critical_count,
        "geometry_critical_share": _share(geometry_critical_count, row_count),
        "syntax_only_calibration_count": syntax_only_calibration_count,
        "syntax_only_calibration_share": _share(syntax_only_calibration_count, row_count),
        "release_ready_count": release_ready_count,
        "release_ready_share": _share(release_ready_count, row_count),
        "unique_answer_count": unique_answer_count,
    }


def _family_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_family": report["prompt_family"],
        "row_count": report["row_count"],
        "geometry_hop_positive_share": report["geometry_hop_positive_share"],
        "geometry_critical_share": report["geometry_critical_share"],
        "syntax_only_calibration_share": report["syntax_only_calibration_share"],
        "geometry_hop_counts": report["geometry_hop_counts"],
    }


def _int_counter(rows: list[dict[str, Any]], key: str) -> Counter[str]:
    return Counter(str(int(row.get(key) or 0)) for row in rows)


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: int(item[0])))


def _share(count: int, total: int) -> float:
    return count / total if total else 0.0


def _answer_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)
