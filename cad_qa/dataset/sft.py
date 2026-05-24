"""SFT export helpers for graph-first rows."""

from __future__ import annotations

from typing import Any


def default_training_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows exported by default for SFT: geometry-critical, not calibration-only."""

    return [
        row
        for row in rows
        if is_training_eligible_row(row)
    ]


def training_readiness_report(
    input_rows: list[dict[str, Any]],
    training_rows: list[dict[str, Any]] | None = None,
    *,
    include_calibration: bool = False,
    dominance_threshold: float = 0.95,
    max_syntax_only_share: float = 0.0,
) -> dict[str, Any]:
    exported_rows = training_rows if training_rows is not None else (
        input_rows if include_calibration else default_training_rows(input_rows)
    )
    geometry_critical_training_rows = sum(1 for row in exported_rows if is_geometry_critical_row(row))
    syntax_only_training_rows = sum(1 for row in exported_rows if is_syntax_only_calibration_row(row))
    quarantined_training_rows = sum(
        1
        for row in exported_rows
        if row.get("release_ready") is False or row.get("quarantine_reasons")
    )
    training_count = len(exported_rows)
    geometry_share = geometry_critical_training_rows / training_count if training_count else 0.0
    syntax_only_share = syntax_only_training_rows / training_count if training_count else 0.0
    default_rows = default_training_rows(input_rows)
    passes_syntax_only_cap = training_count > 0 and syntax_only_share <= max_syntax_only_share
    return {
        "input_rows": len(input_rows),
        "training_rows": training_count,
        "default_training_rows": len(default_rows),
        "excluded_calibration_noncritical_or_quarantined_rows": len(input_rows) - len(default_rows),
        "geometry_critical_training_rows": geometry_critical_training_rows,
        "syntax_only_training_rows": syntax_only_training_rows,
        "syntax_only_training_share": syntax_only_share,
        "max_syntax_only_training_share": max_syntax_only_share,
        "quarantined_training_rows": quarantined_training_rows,
        "geometry_critical_training_share": geometry_share,
        "dominance_threshold": dominance_threshold,
        "passes_syntax_only_training_cap": passes_syntax_only_cap,
        "passes_geometry_critical_dominance": (
            training_count > 0
            and geometry_share >= dominance_threshold
            and passes_syntax_only_cap
            and quarantined_training_rows == 0
        ),
        "include_calibration": include_calibration,
    }


def is_training_eligible_row(row: dict[str, Any]) -> bool:
    if row.get("release_ready") is False:
        return False
    if row.get("quarantine_reasons"):
        return False
    return is_geometry_critical_row(row) and not is_syntax_only_calibration_row(row)


def is_syntax_only_calibration_row(row: dict[str, Any]) -> bool:
    family = prompt_family(row)
    if family == "first_operation":
        return True
    return int(row.get("geometry_hop_count") or 0) == 0


def is_geometry_critical_row(row: dict[str, Any]) -> bool:
    relation_families = set(row.get("relation_families") or [])
    if relation_families & {
        "has_kernel_stable_face_id",
        "has_kernel_stable_edge_id",
        "has_kernel_stable_vertex_id",
        "has_kernel_material_region_geometry",
        "has_kernel_void_region_geometry",
    }:
        return True
    return any(_is_geometry_critical_metric(metric) for metric in _query_metrics(row))


def _query_metrics(row: dict[str, Any]) -> set[str]:
    query = row.get("query_program") or {}
    metrics: set[str] = set()
    aggregation_metric = query.get("aggregation_metric")
    if isinstance(aggregation_metric, str):
        metrics.add(aggregation_metric)
    tie_break_metric = query.get("tie_break_metric")
    if isinstance(tie_break_metric, str):
        metrics.add(tie_break_metric)
    for clause in query.get("clauses") or []:
        if isinstance(clause, dict) and isinstance(clause.get("metric"), str):
            metrics.add(clause["metric"])
    return metrics


def _is_geometry_critical_metric(metric: str) -> bool:
    if metric in {
        "volume",
        "volume_delta_magnitude",
        "signed_volume_delta",
        "centroid",
        "centroid_delta_magnitude",
        "centroid_x",
        "centroid_y",
        "centroid_z",
        "coordinate_z",
        "distance_to_origin",
        "midpoint_distance_to_origin",
        "nearest_point_distance_to_origin",
        "segment_length",
    }:
        return True
    return metric.startswith(("bbox", "topology", "centroid", "coordinate", "distance"))


def prompt_family(row: dict[str, Any]) -> str:
    query_id = row.get("query_program", {}).get("query_id")
    if isinstance(query_id, str) and ":" in query_id:
        return query_id.rsplit(":", 1)[-1]
    row_id = row.get("row_id")
    if isinstance(row_id, str) and ":" in row_id:
        return row_id.rsplit(":", 1)[-1]
    return "unknown"


def answer_sft_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "messages": [
                {"role": "user", "content": row["prompt"]},
                {"role": "assistant", "content": str(row["gold_answer"])},
            ]
        }
        for row in rows
    ]


def reasoning_sft_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for row in rows:
        trace_lines = []
        for step in row.get("candidate_trace", {}).get("steps", []):
            after = step.get("after") or step.get("candidate_ids") or []
            trace_lines.append(f"{step.get('step')}: {len(after)} candidates")
        content = "\n".join([*trace_lines, f"answer: {row['gold_answer']}"])
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": content},
                ]
            }
        )
    return examples


def ablation_sft_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(f"hop_{row['logical_hop_count']}", []).append(row)
        groups.setdefault(f"difficulty_{row['difficulty_bucket']}", []).append(row)
    return {name: answer_sft_rows(group_rows) for name, group_rows in sorted(groups.items())}


def scaling_sft_groups(rows: list[dict[str, Any]], sizes: list[int]) -> dict[str, list[dict[str, str]]]:
    ordered = sorted(rows, key=lambda row: row["row_id"])
    return {
        f"size_{size}": answer_sft_rows(ordered[: min(size, len(ordered))])
        for size in sizes
    }
