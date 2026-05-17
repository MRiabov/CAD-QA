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
    """Check that public clue entries trace to hidden query clauses."""

    query = row.get("query_program") or {}
    clause_ids = [
        clause.get("id")
        for clause in query.get("clauses", [])
        if isinstance(clause, dict) and clause.get("id")
    ]
    expected = set(clause_ids)
    if query.get("aggregation"):
        expected.add("aggregation")
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
