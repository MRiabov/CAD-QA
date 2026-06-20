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

from cad_qa.dataset.parameter_balance import parameter_balance_report
from cad_qa.dataset.release_report import (
    _is_cross_feature_value_bearing_row,
    _is_value_bearing_measurement_row,
    release_gate_profile,
)
from cad_qa.dataset.sft import prompt_family
from cad_qa.io import write_json


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
    parser.add_argument("--out", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    rows = _read_pool_rows(args.dataset_stream)
    report = release_gate_feasibility_report(rows, release_tier=args.release_tier)
    if args.out is not None:
        write_json(args.out, report)
    print(json.dumps(report, indent=2, sort_keys=True))


def release_gate_feasibility_report(rows: list[dict[str, Any]], *, release_tier: str) -> dict[str, Any]:
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
    return {
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
    }


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


if __name__ == "__main__":
    main()
