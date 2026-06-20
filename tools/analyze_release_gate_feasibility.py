"""Analyze whether generated rows can satisfy strict release gates.

This is a read-only diagnostic tool. It inspects generated row shard parquets
before release selection and reports whether the pool has enough source,
family, value-bearing, cross-feature, and parameter diversity capacity for the
benchmark-release profile.
"""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--out", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    rows = _read_pool_rows(args.dataset_stream)
    graph_records = _iter_graph_records(args.graph_dir) if args.graph_dir is not None else None
    report = release_gate_feasibility_report(
        rows,
        release_tier=args.release_tier,
        graph_records=graph_records,
        analyze_missing_query_counts=args.analyze_missing_query_counts,
        max_missing_query_analysis=args.max_missing_query_analysis,
        simulate_release_balance=args.simulate_release_balance,
    )
    if args.out is not None:
        write_json(args.out, report)
    print(json.dumps(report, indent=2, sort_keys=True))


def release_gate_feasibility_report(
    rows: list[dict[str, Any]],
    *,
    release_tier: str,
    graph_records: Any | None = None,
    analyze_missing_query_counts: bool = False,
    max_missing_query_analysis: int | None = None,
    simulate_release_balance: bool = False,
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
        report["simulated_release_balance"] = simulated_release_balance_report(rows, release_tier=profile.name)
    return report


def simulated_release_balance_report(rows: list[dict[str, Any]], *, release_tier: str) -> dict[str, Any]:
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
    return {
        "input_row_count": len(rows),
        "output_row_count": len(capped_rows),
        "release_floor": release_floor,
        "exclusion_count": len(exclusions),
        "exclusion_reason_counts": dict(Counter(item["reason"] for item in exclusions).most_common()),
        "passes_prompt_family_balance": balance["passes_prompt_family_balance"],
        "passes_prompt_template_balance": balance["passes_prompt_template_balance"],
        "passes_value_bearing_measurement_coverage": balance["passes_value_bearing_measurement_coverage"],
        "value_bearing_measurement_share": balance["value_bearing_measurement_share"],
        "passes_cross_feature_value_bearing_coverage": balance["passes_cross_feature_value_bearing_coverage"],
        "cross_feature_value_bearing_share": balance["cross_feature_value_bearing_share"],
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
        "parameter_balance_top_violation_pool_context": parameter_violation_classification["top_context"],
    }


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


def _read_pool_rows(dataset_stream: Path) -> list[dict[str, Any]]:
    paths = [
        *sorted((dataset_stream / "row_shards").glob("part-*.parquet")),
        *sorted((dataset_stream / "row_graph_shards").glob("part-*.parquet")),
    ]
    if not paths:
        raise FileNotFoundError(f"no row shard parquets found under {dataset_stream}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        parquet_file = pq.ParquetFile(path)
        columns = [column for column in ROW_COLUMNS if column in parquet_file.schema.names]
        for batch in parquet_file.iter_batches(batch_size=5000, columns=columns):
            for row in batch.to_pylist():
                query_program = row.get("query_program")
                if isinstance(query_program, str):
                    row["query_program"] = json.loads(query_program)
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
        "top_classification_counts": dict(
            Counter(item["classification"] for item in top_context).most_common()
        ),
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
