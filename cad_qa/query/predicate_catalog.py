"""Reusable graph predicates for query synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field

from cad_qa.ontology.nodes import Node, OntologyGraph
from cad_qa.query.ir import Clause


@dataclass(frozen=True)
class PredicateInstance:
    """A reusable verifier clause with its candidate effect."""

    id: str
    clause: Clause
    candidate_count_before: int
    candidate_count_after: int
    sampled_parameters: dict[str, list[str]] = field(default_factory=dict)


def relation_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    relation: str,
    target_type: str,
) -> PredicateInstance | None:
    """Instantiate a relation predicate if it preserves at least two candidates."""

    after = [
        node
        for node in candidates
        if any(
            edge.source_id == node.id
            and edge.type == relation
            and (target := graph.node(edge.target_id)) is not None
            and target.type == target_type
            for edge in graph.relations
        )
    ]
    if len(after) < 2:
        return None
    return PredicateInstance(
        id=f"relation:{relation}:{target_type}",
        clause=Clause(
            id=clause_id,
            kind="has_relation",
            relation=relation,
            target_type=target_type,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters={
            "narrowing_predicate_sequence": [f"relation:{relation}:{target_type}"],
            "clause_relation": [relation],
            "clause_target_type": [target_type],
        },
    )


def measurement_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
) -> PredicateInstance | None:
    """Instantiate a measurement-presence predicate if it preserves distractors."""

    after = [
        node
        for node in candidates
        if graph.measurements_for(node.id, metric)
    ]
    if len(after) < 2:
        return None
    params: dict[str, list[str]] = {
        "narrowing_predicate_sequence": [f"measurement:{metric}"],
        "clause_metric": [metric],
    }
    axis = metric_axis(metric)
    if axis is not None:
        params["clause_axis"] = [axis]
    return PredicateInstance(
        id=f"measurement:{metric}",
        clause=Clause(
            id=clause_id,
            kind="has_measurement",
            metric=metric,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters=params,
    )


def merge_sampled_parameters(*mappings: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = {}
    for mapping in mappings:
        for key, values in mapping.items():
            merged.setdefault(key, set()).update(str(value) for value in values if str(value))
    return {key: sorted(values) for key, values in sorted(merged.items()) if values}


def metric_axis(metric: str) -> str | None:
    tokens = [token for token in metric.lower().replace("-", "_").split("_") if token]
    for token in reversed(tokens):
        if token in {"x", "y", "z"}:
            return token
    return None
