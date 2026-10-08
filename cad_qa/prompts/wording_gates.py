"""Prompt wording gates."""

from __future__ import annotations

from typing import Any

BANNED_PUBLIC_TERMS = {
    "ontology",
    "material_region",
    "void_region",
    "measurement scope",
    "candidate-set trace",
}


def banned_terms(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(term for term in BANNED_PUBLIC_TERMS if term in lowered)


def clue_breadth_violations(
    row: dict[str, Any],
    *,
    default_min_candidates: int = 3,
) -> list[dict[str, Any]]:
    """Return high-hop clue steps that collapse below the breadth threshold."""

    query = row.get("query_program") or {}
    hop_count = int(row.get("logical_hop_count") or query.get("hop_count") or 0)
    if hop_count < 3:
        return []
    threshold = int(query.get("min_individual_clause_candidates") or default_min_candidates)
    if threshold <= 1:
        return []
    clause_ids = {
        clause.get("id")
        for clause in query.get("clauses", [])
        if isinstance(clause, dict) and clause.get("id")
    }
    violations: list[dict[str, Any]] = []
    for step in row.get("candidate_trace", {}).get("steps", []):
        if not isinstance(step, dict) or step.get("step") not in clause_ids:
            continue
        after = step.get("after") or step.get("candidate_ids") or []
        after_count = len(after) if isinstance(after, list) else 0
        if after_count < threshold:
            violations.append(
                {
                    "clause_id": step.get("step"),
                    "after_count": after_count,
                    "min_candidates": threshold,
                }
            )
    return violations


def clue_map_traceability_errors(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Check that public clue entries map to hidden Gold query predicates."""

    query = row.get("query_program") or {}
    clause_ids = [
        clause.get("id")
        for clause in query.get("clauses", [])
        if isinstance(clause, dict) and clause.get("id")
    ]
    expected = set(clause_ids)
    if query.get("aggregation"):
        expected.add("aggregation")
    if query.get("tie_break_aggregation"):
        expected.add("tie_break_aggregation")
    seen = {
        clue.get("clause_id")
        for clue in row.get("clue_map", [])
        if isinstance(clue, dict) and clue.get("clause_id")
    }
    errors: list[dict[str, Any]] = []
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing:
        errors.append({"error": "missing_clue_clause_map", "clause_ids": missing})
    if extra:
        errors.append({"error": "unknown_clue_clause_map", "clause_ids": extra})
    return errors


def geometry_first_prompt_policy_issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return row-level prompt policy issues for geometry-first release gates."""

    family = _prompt_family(row)
    geometry_hops = int(row.get("geometry_hop_count") or 0)
    syntax_calibration = family in {"first_operation"} or geometry_hops == 0
    issues: list[dict[str, Any]] = []
    if syntax_calibration:
        issues.append(
            {
                "severity": "warning",
                "issue": "syntax_only_calibration_row",
                "prompt_family": family,
                "geometry_hop_count": geometry_hops,
            }
        )
        return issues
    if not _is_geometry_critical_row(row):
        issues.append(
            {
                "severity": "error",
                "issue": "non_geometry_critical_prompt",
                "prompt_family": family,
                "geometry_hop_count": geometry_hops,
            }
        )
    for clause in (row.get("query_program") or {}).get("clauses", []):
        if not isinstance(clause, dict):
            continue
        if clause.get("kind") == "property_equals" and clause.get("value") is not None:
            issues.append(
                {
                    "severity": "error",
                    "issue": "literal_property_clause",
                    "clause_id": clause.get("id"),
                    "metric": clause.get("metric"),
                    "prompt_family": family,
                }
            )
    return issues


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


def _is_geometry_critical_row(row: dict[str, Any]) -> bool:
    relation_families = set(row.get("relation_families") or [])
    if relation_families & {
        "has_kernel_stable_face_id",
        "has_kernel_stable_edge_id",
        "has_kernel_stable_vertex_id",
        "has_kernel_material_region_geometry",
        "has_kernel_void_region_geometry",
    }:
        return True
    query = row.get("query_program") or {}
    metrics = {
        metric
        for metric in [query.get("aggregation_metric"), query.get("tie_break_metric")]
        if isinstance(metric, str)
    }
    metrics.update(
        clause["metric"]
        for clause in query.get("clauses") or []
        if isinstance(clause, dict) and isinstance(clause.get("metric"), str)
    )
    return any(_is_geometry_critical_metric(metric) for metric in metrics)


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
