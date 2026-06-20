"""Analyze whether generated rows can satisfy strict release gates.

This is a read-only diagnostic tool. It inspects generated row shard parquets
before release selection and reports whether the pool has enough source,
family, value-bearing, cross-feature, and parameter diversity capacity for the
benchmark-release profile.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from cad_qa.dataset.parameter_balance import parameter_balance_report, row_sampled_parameters
from cad_qa.dataset.release import _cap_release_balance_rows
from cad_qa.dataset.release_report import (
    _is_cross_feature_value_bearing_row,
    _is_value_bearing_measurement_row,
    release_balance_report,
    release_gate_profile,
)
from cad_qa.dataset.sft import prompt_family
from cad_qa.io import iter_records, write_json
from cad_qa.ontology.nodes import graph_from_dict
from cad_qa.query.family_manifest import load_family_manifest
from cad_qa.query.synthesis import synthesize_graph_hop_queries


ROW_COLUMNS = (
    "row_id",
    "source_id",
    "answer_format",
    "gold_answer",
    "query_program",
    "logical_hop_count",
    "geometry_hop_count",
    "static_hop_count",
    "prompt_template_id",
    "prompt",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-stream",
        type=Path,
        required=True,
        help="Path containing row_shards/ and optionally row_graph_shards/.",
    )
    parser.add_argument(
        "--release-tier",
        default="benchmark-release",
        help="Release gate profile to analyze against.",
    )
    parser.add_argument(
        "--graph-dir",
        type=Path,
        help="Optional graph shard directory. Adds source coverage diagnostics against graph artifacts.",
    )
    parser.add_argument(
        "--analyze-missing-query-counts",
        action="store_true",
        help="For graph sources with no generated rows, rebuild current synthesis query counts.",
    )
    parser.add_argument(
        "--max-missing-query-analysis",
        type=int,
        help="Optional cap on missing graph sources to run through query synthesis.",
    )
    parser.add_argument(
        "--simulate-release-balance",
        action="store_true",
        help="Run the release balance capping pass and report compact post-cap gate diagnostics.",
    )
    parser.add_argument(
        "--include-candidate-trace",
        action="store_true",
        help="Load candidate_trace for candidate-breadth diagnostics. This is slower on large row pools.",
    )
    parser.add_argument(
        "--simulate-parameter-repair",
        action="store_true",
        help="After release-balance simulation, run a dry-run same-family parameter-diversity repair.",
    )
    parser.add_argument(
        "--max-parameter-repair-swaps",
        type=int,
        default=1000,
        help="Maximum same-family row swaps for --simulate-parameter-repair.",
    )
    parser.add_argument("--out", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Write --out without printing the full JSON report to stdout.",
    )
    args = parser.parse_args()

    rows = _read_pool_rows(args.dataset_stream, include_candidate_trace=bool(args.include_candidate_trace))
    graph_records = _iter_graph_records(args.graph_dir) if args.graph_dir is not None else None
    report = release_gate_feasibility_report(
        rows,
        release_tier=args.release_tier,
        graph_records=graph_records,
        analyze_missing_query_counts=args.analyze_missing_query_counts,
        max_missing_query_analysis=args.max_missing_query_analysis,
        simulate_release_balance=args.simulate_release_balance,
        simulate_parameter_repair=args.simulate_parameter_repair,
        max_parameter_repair_swaps=args.max_parameter_repair_swaps,
    )
    if args.out is not None:
        write_json(args.out, report)
    if not args.quiet:
        print(json.dumps(report, indent=2, sort_keys=True))


def release_gate_feasibility_report(
    rows: list[dict[str, Any]],
    *,
    release_tier: str,
    graph_records: Any | None = None,
    analyze_missing_query_counts: bool = False,
    max_missing_query_analysis: int | None = None,
    simulate_release_balance: bool = False,
    simulate_parameter_repair: bool = False,
    max_parameter_repair_swaps: int = 1000,
) -> dict[str, Any]:
    profile = release_gate_profile(release_tier)
    row_count = len(rows)
    source_ids = {row.get("source_id") for row in rows if row.get("source_id")}
    family_counts = Counter(prompt_family(row) for row in rows)
    value_rows = [row for row in rows if _is_value_bearing_measurement_row(row)]
    cross_rows = [row for row in rows if _is_cross_feature_value_bearing_row(row)]
    value_family_counts = Counter(prompt_family(row) for row in value_rows)
    cross_family_counts = Counter(prompt_family(row) for row in cross_rows)
    parameter_report = parameter_balance_report(
        rows,
        max_parameter_value_share=profile.max_parameter_value_share,
        min_axis_direction_share=profile.min_axis_direction_parameter_share,
        enforce=True,
    )
    min_family_rows = (
        int(profile.min_release_rows * profile.min_prompt_family_share)
        if profile.min_release_rows is not None
        else None
    )
    min_cross_count = (
        int(profile.min_release_rows * profile.min_cross_feature_value_bearing_share)
        if profile.min_release_rows is not None and profile.min_cross_feature_value_bearing_share is not None
        else None
    )
    max_value_count = (
        int(profile.min_release_rows * profile.max_value_bearing_measurement_share)
        if profile.min_release_rows is not None and profile.max_value_bearing_measurement_share is not None
        else None
    )
    parameter_violations = parameter_report.get("violations", [])
    report = {
        "release_tier": profile.name,
        "pool_row_count": row_count,
        "pool_source_count": len(source_ids),
        "pool_family_count": len(family_counts),
        "minimum_release_rows": profile.min_release_rows,
        "minimum_family_rows_for_release": min_family_rows,
        "families_with_at_least_minimum_rows": (
            sum(1 for count in family_counts.values() if min_family_rows is not None and count >= min_family_rows)
            if min_family_rows is not None
            else None
        ),
        "families_below_minimum_rows": (
            [
                {"prompt_family": family, "available_rows": count, "minimum_rows": min_family_rows}
                for family, count in sorted(family_counts.items())
                if min_family_rows is not None and count < min_family_rows
            ]
            if min_family_rows is not None
            else []
        ),
        "family_min_available_rows": min(family_counts.values()) if family_counts else 0,
        "family_max_available_rows": max(family_counts.values()) if family_counts else 0,
        "value_bearing_pool_row_count": len(value_rows),
        "value_bearing_pool_family_count": len(value_family_counts),
        "value_bearing_pool_family_counts": dict(sorted(value_family_counts.items())),
        "maximum_value_bearing_rows_for_release": max_value_count,
        "cross_feature_pool_row_count": len(cross_rows),
        "cross_feature_pool_family_count": len(cross_family_counts),
        "cross_feature_pool_family_counts": dict(sorted(cross_family_counts.items())),
        "minimum_cross_feature_rows_for_release": min_cross_count,
        "parameter_balance_full_pool_valid": bool(parameter_report.get("valid")),
        "parameter_balance_full_pool_violation_count": len(parameter_violations),
        "parameter_balance_full_pool_reason_counts": dict(Counter(v["reason"] for v in parameter_violations)),
        "parameter_balance_full_pool_dimension_counts": dict(Counter(v["dimension"] for v in parameter_violations).most_common()),
        "parameter_balance_full_pool_family_counts": dict(Counter(v["prompt_family"] for v in parameter_violations).most_common()),
        "parameter_balance_full_pool_top_violations": _compact_parameter_violations(parameter_violations),
    }
    if graph_records is not None:
        report.update(
            graph_source_coverage_report(
                source_ids,
                graph_records,
                analyze_missing_query_counts=analyze_missing_query_counts,
                max_missing_query_analysis=max_missing_query_analysis,
            )
        )
    if simulate_release_balance:
        report["simulated_release_balance"] = simulated_release_balance_report(
            rows,
            release_tier=profile.name,
            simulate_parameter_repair=simulate_parameter_repair,
            max_parameter_repair_swaps=max_parameter_repair_swaps,
        )
    return report


def simulated_release_balance_report(
    rows: list[dict[str, Any]],
    *,
    release_tier: str,
    simulate_parameter_repair: bool = False,
    max_parameter_repair_swaps: int = 1000,
) -> dict[str, Any]:
    profile = release_gate_profile(release_tier)
    release_floor = (
        profile.min_release_rows
        if profile.min_release_rows is not None and len(rows) >= profile.min_release_rows
        else None
    )
    capped_rows, exclusions = _cap_release_balance_rows(rows, profile)
    balance = release_balance_report(capped_rows, release_tier=profile.name)
    parameter_report = parameter_balance_report(
        capped_rows,
        max_parameter_value_share=profile.max_parameter_value_share,
        min_axis_direction_share=profile.min_axis_direction_parameter_share,
        enforce=profile.enforce_parameter_balance,
    )
    parameter_violations = parameter_report.get("violations", [])
    parameter_violation_classification = _parameter_violation_classification_report(
        parameter_violations,
        pool_rows=rows,
        selected_rows=capped_rows,
        min_expected_share=profile.min_axis_direction_parameter_share,
    )
    candidate_breadth_loaded = any(isinstance(row.get("candidate_trace"), dict) for row in capped_rows)
    report = {
        "input_row_count": len(rows),
        "output_row_count": len(capped_rows),
        "release_floor": release_floor,
        "exclusion_count": len(exclusions),
        "exclusion_reason_counts": dict(Counter(item["reason"] for item in exclusions).most_common()),
        "distinct_cad_model_count": balance["distinct_cad_model_count"],
        "minimum_distinct_cad_model_count": balance["minimum_distinct_cad_model_count"],
        "distinct_cad_model_deficit_count": balance["distinct_cad_model_deficit_count"],
        "passes_distinct_cad_model_coverage": balance["passes_distinct_cad_model_coverage"],
        "passes_prompt_family_balance": balance["passes_prompt_family_balance"],
        "passes_prompt_template_balance": balance["passes_prompt_template_balance"],
        "passes_answer_entropy": balance["passes_answer_entropy"],
        "answer_entropy_bits": balance["answer_entropy_bits"],
        "answer_entropy_capacity_bits": balance["answer_entropy_capacity_bits"],
        "minimum_answer_entropy_bits": balance["minimum_answer_entropy_bits"],
        "passes_value_bearing_measurement_coverage": balance["passes_value_bearing_measurement_coverage"],
        "value_bearing_measurement_share": balance["value_bearing_measurement_share"],
        "passes_cross_feature_value_bearing_coverage": balance["passes_cross_feature_value_bearing_coverage"],
        "cross_feature_value_bearing_share": balance["cross_feature_value_bearing_share"],
        "candidate_breadth_loaded": candidate_breadth_loaded,
        "passes_candidate_breadth": balance["passes_candidate_breadth"] if candidate_breadth_loaded else None,
        "minimum_required_median_pre_final_candidate_count": (
            balance["minimum_required_median_pre_final_candidate_count"] if candidate_breadth_loaded else None
        ),
        "median_pre_final_candidate_count": balance["median_pre_final_candidate_count"] if candidate_breadth_loaded else None,
        "parameter_balance_valid": bool(parameter_report.get("valid")),
        "parameter_balance_violation_count": len(parameter_violations),
        "parameter_balance_reason_counts": dict(Counter(v["reason"] for v in parameter_violations)),
        "parameter_balance_dimension_counts": dict(Counter(v["dimension"] for v in parameter_violations).most_common()),
        "parameter_balance_family_counts": dict(Counter(v["prompt_family"] for v in parameter_violations).most_common()),
        "parameter_balance_top_violations": _compact_parameter_violations(parameter_violations),
        "parameter_balance_top_violation_classification_counts": dict(
            parameter_violation_classification["top_classification_counts"]
        ),
        "parameter_balance_violation_classification_counts": parameter_violation_classification[
            "classification_counts"
        ],
        "parameter_balance_violation_classification_reason_counts": parameter_violation_classification[
            "classification_reason_counts"
        ],
        "parameter_balance_violation_individual_replacement_capacity_counts": parameter_violation_classification[
            "individual_replacement_capacity_counts"
        ],
        "parameter_balance_violation_classification_replacement_capacity_counts": parameter_violation_classification[
            "classification_replacement_capacity_counts"
        ],
        "parameter_balance_top_violation_pool_context": parameter_violation_classification["top_context"],
        "parameter_balance_top_violation_individual_replacement_capacity_counts": parameter_violation_classification[
            "top_individual_replacement_capacity_counts"
        ],
    }
    if simulate_parameter_repair:
        report["parameter_repair_simulation"] = _simulate_parameter_repair_report(
            rows,
            capped_rows,
            profile=profile,
            max_swaps=max_parameter_repair_swaps,
        )
    return report


def graph_source_coverage_report(
    generated_source_ids: set[str | None],
    graph_records: Any,
    *,
    analyze_missing_query_counts: bool = False,
    max_missing_sample: int = 20,
    max_missing_query_analysis: int | None = None,
) -> dict[str, Any]:
    generated = {source_id for source_id in generated_source_ids if source_id}
    graph_sources: set[str] = set()
    graph_sources_with_rows: set[str] = set()
    missing_sources: list[str] = []
    missing_node_type_counts: Counter[str] = Counter()
    missing_query_counts: Counter[int] = Counter()
    missing_query_count_errors: Counter[str] = Counter()
    missing_query_count_analyzed = 0
    missing_query_count_skipped = 0

    for record in graph_records:
        source_id = _graph_source_id(record)
        if not source_id:
            continue
        graph_sources.add(source_id)
        if source_id in generated:
            graph_sources_with_rows.add(source_id)
            continue
        missing_sources.append(source_id)
        missing_node_type_counts.update(_node_type_counts(record))
        if analyze_missing_query_counts:
            if max_missing_query_analysis is not None and missing_query_count_analyzed >= max_missing_query_analysis:
                missing_query_count_skipped += 1
                continue
            try:
                graph = graph_from_dict(record)
                missing_query_counts.update([len(synthesize_graph_hop_queries(graph, max_per_family=1))])
                missing_query_count_analyzed += 1
            except Exception as exc:  # pragma: no cover - defensive diagnostic path
                missing_query_count_errors.update([type(exc).__name__])
                missing_query_count_analyzed += 1

    graph_sources_missing_rows = sorted(set(missing_sources))
    report = {
        "graph_source_count": len(graph_sources),
        "pool_sources_with_generated_rows": len(generated),
        "graph_sources_with_generated_rows": len(graph_sources_with_rows),
        "graph_sources_missing_generated_rows_count": len(graph_sources_missing_rows),
        "graph_sources_missing_generated_rows_sample": graph_sources_missing_rows[:max_missing_sample],
        "missing_source_node_type_counts": dict(missing_node_type_counts.most_common()),
    }
    if analyze_missing_query_counts:
        report["missing_source_query_count_distribution"] = {
            str(count): total for count, total in sorted(missing_query_counts.items())
        }
        report["missing_source_query_count_analyzed"] = missing_query_count_analyzed
        report["missing_source_query_count_skipped"] = missing_query_count_skipped
        report["missing_source_query_count_error_counts"] = dict(missing_query_count_errors.most_common())
    return report


def _simulate_parameter_repair_report(
    pool_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    *,
    profile: Any,
    max_swaps: int,
) -> dict[str, Any]:
    _cache_sampled_parameters(pool_rows)
    _cache_sampled_parameters(selected_rows)
    family_manifest = load_family_manifest()
    pre_parameter_report = parameter_balance_report(
        selected_rows,
        loaded_family_manifest=family_manifest,
        max_parameter_value_share=profile.max_parameter_value_share,
        min_axis_direction_share=profile.min_axis_direction_parameter_share,
        enforce=profile.enforce_parameter_balance,
    )
    pre_violations = pre_parameter_report.get("violations", [])
    repaired_rows, repair = _greedy_same_family_parameter_repair(
        pool_rows,
        selected_rows,
        profile=profile,
        max_swaps=max_swaps,
        family_manifest=family_manifest,
    )
    balance = release_balance_report(repaired_rows, release_tier=profile.name)
    parameter_report = parameter_balance_report(
        repaired_rows,
        loaded_family_manifest=family_manifest,
        max_parameter_value_share=profile.max_parameter_value_share,
        min_axis_direction_share=profile.min_axis_direction_parameter_share,
        enforce=profile.enforce_parameter_balance,
    )
    violations = parameter_report.get("violations", [])
    return {
        "input_selected_row_count": len(selected_rows),
        "output_row_count": len(repaired_rows),
        "max_swaps": max_swaps,
        "swap_count": repair["swap_count"],
        "stopped_reason": repair["stopped_reason"],
        "attempted_violation_count": repair["attempted_violation_count"],
        "successful_violation_count": repair["successful_violation_count"],
        "failed_violation_count": repair["failed_violation_count"],
        "swap_reason_counts": repair["swap_reason_counts"],
        "pre_parameter_balance_valid": bool(pre_parameter_report.get("valid")),
        "pre_parameter_balance_violation_count": len(pre_violations),
        "pre_parameter_balance_reason_counts": dict(Counter(v["reason"] for v in pre_violations)),
        "pre_parameter_balance_dimension_counts": dict(Counter(v["dimension"] for v in pre_violations).most_common()),
        "pre_parameter_balance_family_counts": dict(Counter(v["prompt_family"] for v in pre_violations).most_common()),
        "post_parameter_balance_valid": bool(parameter_report.get("valid")),
        "post_parameter_balance_violation_count": len(violations),
        "post_parameter_balance_reason_counts": dict(Counter(v["reason"] for v in violations)),
        "post_parameter_balance_dimension_counts": dict(Counter(v["dimension"] for v in violations).most_common()),
        "post_parameter_balance_family_counts": dict(Counter(v["prompt_family"] for v in violations).most_common()),
        "post_distinct_cad_model_count": balance["distinct_cad_model_count"],
        "post_distinct_cad_model_deficit_count": balance["distinct_cad_model_deficit_count"],
        "post_passes_distinct_cad_model_coverage": balance["passes_distinct_cad_model_coverage"],
        "post_passes_prompt_family_balance": balance["passes_prompt_family_balance"],
        "post_passes_prompt_template_balance": balance["passes_prompt_template_balance"],
        "post_passes_answer_entropy": balance["passes_answer_entropy"],
        "post_answer_entropy_bits": balance["answer_entropy_bits"],
        "post_passes_value_bearing_measurement_coverage": balance["passes_value_bearing_measurement_coverage"],
        "post_value_bearing_measurement_share": balance["value_bearing_measurement_share"],
        "post_passes_cross_feature_value_bearing_coverage": balance["passes_cross_feature_value_bearing_coverage"],
        "post_cross_feature_value_bearing_share": balance["cross_feature_value_bearing_share"],
    }


def _cache_sampled_parameters(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["_sampled_parameters_cache"] = row_sampled_parameters(row)


def _greedy_same_family_parameter_repair(
    pool_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    *,
    profile: Any,
    max_swaps: int,
    family_manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = list(selected_rows)
    selected_ids = {_row_identity(row) for row in selected}
    pool_by_family = _rows_by_family(pool_rows)
    swap_count = 0
    successful_violation_count = 0
    attempted_violation_count = 0
    failed_violation_count = 0
    swap_reason_counts: Counter[str] = Counter()

    for _iteration in range(max(1, max_swaps)):
        if swap_count >= max_swaps:
            return selected, {
                "swap_count": swap_count,
                "stopped_reason": "max_swaps",
                "attempted_violation_count": attempted_violation_count,
                "successful_violation_count": successful_violation_count,
                "failed_violation_count": failed_violation_count,
                "swap_reason_counts": dict(swap_reason_counts),
            }
        parameter_report = parameter_balance_report(
            selected,
            loaded_family_manifest=family_manifest,
            max_parameter_value_share=profile.max_parameter_value_share,
            min_axis_direction_share=profile.min_axis_direction_parameter_share,
            enforce=profile.enforce_parameter_balance,
        )
        violations = parameter_report.get("violations", [])
        if not violations:
            return selected, {
                "swap_count": swap_count,
                "stopped_reason": "parameter_balance_valid",
                "attempted_violation_count": attempted_violation_count,
                "successful_violation_count": successful_violation_count,
                "failed_violation_count": failed_violation_count,
                "swap_reason_counts": dict(swap_reason_counts),
            }
        progress = False
        for violation in violations:
            if swap_count >= max_swaps:
                break
            attempted_violation_count += 1
            swap = _find_same_family_parameter_swap(
                violation,
                selected,
                selected_ids=selected_ids,
                pool_by_family=pool_by_family,
            )
            if swap is None:
                failed_violation_count += 1
                continue
            remove_index, replacement = swap
            removed = selected[remove_index]
            selected_ids.remove(_row_identity(removed))
            selected[remove_index] = replacement
            selected_ids.add(_row_identity(replacement))
            swap_count += 1
            successful_violation_count += 1
            swap_reason_counts[str(violation.get("reason"))] += 1
            progress = True
            break
        if not progress:
            return selected, {
                "swap_count": swap_count,
                "stopped_reason": "no_progress",
                "attempted_violation_count": attempted_violation_count,
                "successful_violation_count": successful_violation_count,
                "failed_violation_count": failed_violation_count,
                "swap_reason_counts": dict(swap_reason_counts),
            }
    return selected, {
        "swap_count": swap_count,
        "stopped_reason": "iteration_limit",
        "attempted_violation_count": attempted_violation_count,
        "successful_violation_count": successful_violation_count,
        "failed_violation_count": failed_violation_count,
        "swap_reason_counts": dict(swap_reason_counts),
    }


def _find_same_family_parameter_swap(
    violation: dict[str, Any],
    selected_rows: list[dict[str, Any]],
    *,
    selected_ids: set[str],
    pool_by_family: dict[str, list[dict[str, Any]]],
) -> tuple[int, dict[str, Any]] | None:
    family = str(violation.get("prompt_family") or "")
    dimension = str(violation.get("dimension") or "")
    family_pool = pool_by_family.get(family, [])
    if not family_pool:
        return None
    if violation.get("reason") == "parameter_value_dominates":
        value = str(violation.get("largest_value"))
        remove_index = _selected_row_index_with_value(selected_rows, family, dimension, value)
        if remove_index is None:
            return None
        replacement = _replacement_row_without_value(
            family_pool,
            selected_ids=selected_ids,
            dimension=dimension,
            excluded_value=value,
        )
        return (remove_index, replacement) if replacement is not None else None
    if violation.get("reason") == "axis_or_direction_undercovered":
        values = _violation_values(violation)
        if not values:
            return None
        target_value = max(
            values,
            key=lambda value: _available_value_count(family_pool, selected_ids, dimension, value),
        )
        replacement = _replacement_row_with_value(
            family_pool,
            selected_ids=selected_ids,
            dimension=dimension,
            value=target_value,
        )
        if replacement is None:
            return None
        remove_index = _selected_row_index_without_value(selected_rows, family, dimension, target_value)
        return (remove_index, replacement) if remove_index is not None else None
    return None


def _read_pool_rows(dataset_stream: Path, *, include_candidate_trace: bool = False) -> list[dict[str, Any]]:
    paths = [
        *sorted((dataset_stream / "row_shards").glob("part-*.parquet")),
        *sorted((dataset_stream / "row_graph_shards").glob("part-*.parquet")),
    ]
    if not paths:
        raise FileNotFoundError(f"no row shard parquets found under {dataset_stream}")
    rows: list[dict[str, Any]] = []
    requested_columns = (*ROW_COLUMNS, "candidate_trace") if include_candidate_trace else ROW_COLUMNS
    for path in paths:
        parquet_file = pq.ParquetFile(path)
        columns = [column for column in requested_columns if column in parquet_file.schema_arrow.names]
        for batch in parquet_file.iter_batches(batch_size=5000, columns=columns):
            for row in batch.to_pylist():
                query_program = row.get("query_program")
                if isinstance(query_program, str):
                    row["query_program"] = json.loads(query_program)
                candidate_trace = row.get("candidate_trace")
                if isinstance(candidate_trace, str):
                    row["candidate_trace"] = json.loads(candidate_trace)
                rows.append(row)
    return rows


def _compact_parameter_violations(
    violations: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    compact = []
    for violation in violations[:limit]:
        item = {
            "prompt_family": violation.get("prompt_family"),
            "dimension": violation.get("dimension"),
            "reason": violation.get("reason"),
        }
        if "largest_value" in violation:
            item["largest_value"] = violation.get("largest_value")
            item["largest_share"] = violation.get("largest_share")
            item["maximum_allowed_largest_share"] = violation.get("maximum_allowed_largest_share")
        if "undercovered_expected_values" in violation:
            item["undercovered_expected_values"] = violation.get("undercovered_expected_values")
        compact.append(item)
    return compact


def _parameter_violation_pool_context(
    violations: list[dict[str, Any]],
    *,
    pool_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    min_expected_share: float | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    pool_counters = _parameter_counters_by_family_dimension(pool_rows)
    selected_counters = _parameter_counters_by_family_dimension(selected_rows)
    pool_row_index = _parameter_rows_by_family_dimension_value(pool_rows)
    selected_row_index = _parameter_rows_by_family_dimension_value(selected_rows)
    selected_row_ids = {_row_identity(row) for row in selected_rows}
    contexts = []
    for violation in violations[:limit]:
        family = str(violation.get("prompt_family") or "")
        dimension = str(violation.get("dimension") or "")
        key = (family, dimension)
        pool_counts = pool_counters.get(key, Counter())
        selected_counts = selected_counters.get(key, Counter())
        values = _violation_values(violation)
        contexts.append(
            {
                "prompt_family": family,
                "dimension": dimension,
                "reason": violation.get("reason"),
                "classification": _parameter_violation_classification(
                    violation,
                    pool_counts=pool_counts,
                    selected_counts=selected_counts,
                    min_expected_share=min_expected_share,
                ),
                "pool_total": sum(pool_counts.values()),
                "selected_total": sum(selected_counts.values()),
                "pool_largest": _largest_counter_report(pool_counts),
                "selected_largest": _largest_counter_report(selected_counts),
                "replacement_capacity": _parameter_violation_replacement_capacity(
                    violation,
                    family=family,
                    dimension=dimension,
                    pool_row_index=pool_row_index,
                    selected_row_index=selected_row_index,
                    selected_row_ids=selected_row_ids,
                    selected_counts=selected_counts,
                    min_expected_share=min_expected_share,
                ),
                "values": [
                    {
                        "value": value,
                        "pool_count": pool_counts.get(value, 0),
                        "pool_share": _counter_value_share(pool_counts, value),
                        "selected_count": selected_counts.get(value, 0),
                        "selected_share": _counter_value_share(selected_counts, value),
                    }
                    for value in values
                ],
            }
        )
    return contexts


def _parameter_violation_classification_report(
    violations: list[dict[str, Any]],
    *,
    pool_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    min_expected_share: float | None = None,
    context_limit: int = 25,
) -> dict[str, Any]:
    all_context = _parameter_violation_pool_context(
        violations,
        pool_rows=pool_rows,
        selected_rows=selected_rows,
        min_expected_share=min_expected_share,
        limit=len(violations),
    )
    top_context = all_context[:context_limit]
    return {
        "classification_counts": dict(
            Counter(item["classification"] for item in all_context).most_common()
        ),
        "classification_reason_counts": {
            f"{classification}:{reason}": count
            for (classification, reason), count in Counter(
                (context["classification"], context["reason"])
                for context in all_context
            ).most_common()
        },
        "individual_replacement_capacity_counts": _replacement_capacity_counts(all_context),
        "classification_replacement_capacity_counts": _classification_replacement_capacity_counts(all_context),
        "top_classification_counts": dict(
            Counter(item["classification"] for item in top_context).most_common()
        ),
        "top_individual_replacement_capacity_counts": _replacement_capacity_counts(top_context),
        "top_context": top_context,
    }


def _parameter_violation_classification(
    violation: dict[str, Any],
    *,
    pool_counts: Counter[str],
    selected_counts: Counter[str],
    min_expected_share: float | None,
) -> str:
    reason = violation.get("reason")
    if reason == "parameter_value_dominates":
        value = str(violation.get("largest_value"))
        maximum_share = violation.get("maximum_allowed_largest_share")
        if not isinstance(maximum_share, (int, float)):
            return "unknown_threshold"
        pool_largest = _largest_counter_report(pool_counts)
        selected_share = _counter_value_share(selected_counts, value)
        pool_value_share = _counter_value_share(pool_counts, value)
        if pool_largest["share"] > float(maximum_share):
            return "pool_already_violates"
        if selected_share > float(maximum_share) and pool_value_share <= float(maximum_share):
            return "selection_regressed"
        return "selected_violation"
    if reason == "axis_or_direction_undercovered":
        if min_expected_share is None:
            return "unknown_threshold"
        values = _violation_values(violation)
        if not values:
            return "unknown_value"
        pool_can_cover = [
            _counter_value_share(pool_counts, value) >= min_expected_share
            for value in values
        ]
        if all(pool_can_cover):
            return "selection_regressed"
        if not any(pool_can_cover):
            return "pool_undercovered"
        return "mixed_pool_and_selection"
    return "unclassified"


def _replacement_capacity_counts(contexts: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(_replacement_capacity_label(context) for context in contexts).most_common())


def _classification_replacement_capacity_counts(contexts: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        Counter(
            f"{context.get('classification')}:{_replacement_capacity_label(context)}"
            for context in contexts
        ).most_common()
    )


def _replacement_capacity_label(context: dict[str, Any]) -> str:
    capacity = context.get("replacement_capacity")
    if not isinstance(capacity, dict):
        return "unknown"
    value = capacity.get("appears_selection_fixable")
    if value is True:
        return "appears_individually_fixable"
    if value is False:
        return "not_individually_fixable"
    return "unknown"


def _parameter_counters_by_family_dimension(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], Counter[str]]:
    counters: dict[tuple[str, str], Counter[str]] = {}
    for row in rows:
        family = prompt_family(row)
        for dimension, values in row_sampled_parameters(row).items():
            counter = counters.setdefault((family, dimension), Counter())
            counter.update(values)
    return counters


def _rows_by_family(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(prompt_family(row), []).append(row)
    return grouped


def _selected_row_index_with_value(
    rows: list[dict[str, Any]],
    family: str,
    dimension: str,
    value: str,
) -> int | None:
    for index, row in enumerate(rows):
        if prompt_family(row) != family:
            continue
        if value in row_sampled_parameters(row).get(dimension, []):
            return index
    return None


def _selected_row_index_without_value(
    rows: list[dict[str, Any]],
    family: str,
    dimension: str,
    value: str,
) -> int | None:
    best_index = None
    best_score: tuple[int, int, str] | None = None
    for index, row in enumerate(rows):
        if prompt_family(row) != family:
            continue
        values = row_sampled_parameters(row).get(dimension, [])
        if value in values:
            continue
        score = (
            0 if _is_cross_feature_value_bearing_row(row) else 1,
            0 if _is_value_bearing_measurement_row(row) else 1,
            _row_identity(row),
        )
        if best_score is None or score > best_score:
            best_index = index
            best_score = score
    return best_index


def _replacement_row_without_value(
    rows: list[dict[str, Any]],
    *,
    selected_ids: set[str],
    dimension: str,
    excluded_value: str,
) -> dict[str, Any] | None:
    for row in sorted(rows, key=_row_identity):
        if _row_identity(row) in selected_ids:
            continue
        values = row_sampled_parameters(row).get(dimension, [])
        if values and excluded_value not in values:
            return row
    return None


def _replacement_row_with_value(
    rows: list[dict[str, Any]],
    *,
    selected_ids: set[str],
    dimension: str,
    value: str,
) -> dict[str, Any] | None:
    for row in sorted(rows, key=_row_identity):
        if _row_identity(row) in selected_ids:
            continue
        if value in row_sampled_parameters(row).get(dimension, []):
            return row
    return None


def _available_value_count(
    rows: list[dict[str, Any]],
    selected_ids: set[str],
    dimension: str,
    value: str,
) -> int:
    return sum(
        1
        for row in rows
        if _row_identity(row) not in selected_ids
        and value in row_sampled_parameters(row).get(dimension, [])
    )


def _parameter_rows_by_family_dimension_value(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        family = prompt_family(row)
        for dimension, values in row_sampled_parameters(row).items():
            for value in values:
                index.setdefault((family, dimension, value), []).append(row)
    return index


def _parameter_violation_replacement_capacity(
    violation: dict[str, Any],
    *,
    family: str,
    dimension: str,
    pool_row_index: dict[tuple[str, str, str], list[dict[str, Any]]],
    selected_row_index: dict[tuple[str, str, str], list[dict[str, Any]]],
    selected_row_ids: set[str],
    selected_counts: Counter[str],
    min_expected_share: float | None,
) -> dict[str, Any]:
    reason = violation.get("reason")
    selected_total = sum(selected_counts.values())
    if reason == "parameter_value_dominates":
        value = str(violation.get("largest_value"))
        maximum_share = violation.get("maximum_allowed_largest_share")
        if not isinstance(maximum_share, (int, float)):
            return {"estimated_needed_swaps": None, "reason": "unknown_threshold"}
        allowed_count = math.floor(float(maximum_share) * selected_total + 1e-12)
        selected_value_count = selected_counts.get(value, 0)
        needed_swaps = max(0, selected_value_count - allowed_count)
        available_replacement_rows = _available_unselected_rows_excluding_value(
            family,
            dimension,
            excluded_value=value,
            pool_row_index=pool_row_index,
            selected_row_ids=selected_row_ids,
        )
        removable_rows = selected_row_index.get((family, dimension, value), [])
        return {
            "estimated_needed_swaps": needed_swaps,
            "available_unselected_replacement_rows": len(available_replacement_rows),
            "selected_rows_with_dominant_value": len(removable_rows),
            "appears_selection_fixable": (
                needed_swaps > 0
                and len(available_replacement_rows) >= needed_swaps
                and len(removable_rows) >= needed_swaps
            ),
        }
    if reason == "axis_or_direction_undercovered":
        if min_expected_share is None:
            return {"estimated_needed_additions": None, "reason": "unknown_threshold"}
        required_count = math.ceil(min_expected_share * selected_total - 1e-12)
        values = _violation_values(violation)
        value_reports = []
        total_needed = 0
        total_available = 0
        for value in values:
            selected_value_count = selected_counts.get(value, 0)
            needed = max(0, required_count - selected_value_count)
            available = [
                row
                for row in pool_row_index.get((family, dimension, value), [])
                if _row_identity(row) not in selected_row_ids
            ]
            total_needed += needed
            total_available += len(available)
            value_reports.append(
                {
                    "value": value,
                    "required_count": required_count,
                    "selected_count": selected_value_count,
                    "estimated_needed_additions": needed,
                    "available_unselected_rows_with_value": len(available),
                }
            )
        return {
            "estimated_needed_additions": total_needed,
            "available_unselected_rows_with_needed_values": total_available,
            "appears_selection_fixable": total_needed > 0 and total_available >= total_needed,
            "values": value_reports,
        }
    return {"reason": "unclassified"}


def _available_unselected_rows_excluding_value(
    family: str,
    dimension: str,
    *,
    excluded_value: str,
    pool_row_index: dict[tuple[str, str, str], list[dict[str, Any]]],
    selected_row_ids: set[str],
) -> list[dict[str, Any]]:
    available: dict[str, dict[str, Any]] = {}
    for key, rows in pool_row_index.items():
        key_family, key_dimension, key_value = key
        if key_family != family or key_dimension != dimension or key_value == excluded_value:
            continue
        for row in rows:
            row_id = _row_identity(row)
            if row_id not in selected_row_ids:
                available[row_id] = row
    return list(available.values())


def _violation_values(violation: dict[str, Any]) -> list[str]:
    values = []
    largest = violation.get("largest_value")
    if largest is not None:
        values.append(str(largest))
    for item in violation.get("undercovered_expected_values") or []:
        if isinstance(item, dict) and item.get("value") is not None:
            values.append(str(item["value"]))
    return sorted(set(values))


def _largest_counter_report(counts: Counter[str]) -> dict[str, Any]:
    total = sum(counts.values())
    if total == 0:
        return {"value": None, "count": 0, "share": 0.0}
    value, count = max(counts.items(), key=lambda item: (item[1], item[0]))
    return {"value": value, "count": count, "share": count / total}


def _counter_value_share(counts: Counter[str], value: str) -> float:
    total = sum(counts.values())
    return counts.get(value, 0) / total if total else 0.0


def _row_identity(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("prompt") or row.get("query_program", {}).get("query_id") or id(row))


def _iter_graph_records(graph_dir: Path):
    paths = _record_paths(graph_dir)
    if not paths and (graph_dir / "graphs").is_dir():
        paths = _record_paths(graph_dir / "graphs")
    if not paths:
        raise FileNotFoundError(f"no graph record parquets found under {graph_dir}")
    for path in paths:
        yield from iter_records(path, batch_size=100)


def _record_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.glob("part-*.parquet"))


def _graph_source_id(record: dict[str, Any]) -> str | None:
    source = record.get("source")
    if isinstance(source, dict) and source.get("source_id"):
        return str(source["source_id"])
    graph_id = record.get("graph_id")
    if isinstance(graph_id, str) and graph_id.startswith("graph:"):
        return graph_id.split(":", 1)[1]
    return None


def _node_type_counts(record: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for node in record.get("nodes") or []:
        if isinstance(node, dict) and node.get("type"):
            counts.update([str(node["type"])])
    return counts


if __name__ == "__main__":
    main()
