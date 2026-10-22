"""Candidate utilities."""

from __future__ import annotations

from dataset.ontology.nodes import Node, CadGraph


def initial_candidates(graph: CadGraph, target_type: str) -> list[Node]:
    return graph.nodes_by_type(target_type)


def candidate_ids(candidates: list[Node]) -> list[str]:
    return [candidate.id for candidate in candidates]
