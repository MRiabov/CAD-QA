"""Query IR for deterministic CAD-QA resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cad_qa.query.parameters import normalize_sampled_parameters


@dataclass(frozen=True)
class Clause:
    id: str
    kind: str
    relation: str | None = None
    target_type: str | None = None
    metric: str | None = None
    reference_metric: str | None = None
    operator: str | None = None
    value: Any = None
    text: str | None = None


@dataclass(frozen=True)
class QueryProgram:
    query_id: str
    target_type: str
    answer_type: str = "entity_id"
    clauses: list[Clause] = field(default_factory=list)
    aggregation: str | None = None
    aggregation_metric: str | None = None
    aggregation_rank: int | None = None
    tie_break_aggregation: str | None = None
    tie_break_metric: str | None = None
    hop_count: int = 0
    difficulty: str = "low"
    reject_unless_unique: bool = True
    min_individual_clause_candidates: int = 3
    sampled_parameters: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateSetTrace:
    query_id: str
    steps: list[dict[str, Any]]
    final_candidates: list[str]
    status: str
    failure_reason: str | None = None


@dataclass(frozen=True)
class QueryResolution:
    query_program: QueryProgram
    gold_answer: Any
    candidate_trace: CandidateSetTrace
    relation_families: list[str]
    measurement_scopes: list[str]
    verifier_status: str


def query_from_dict(data: dict[str, Any]) -> QueryProgram:
    return QueryProgram(
        query_id=data["query_id"],
        target_type=data["target_type"],
        answer_type=data.get("answer_type", "entity_id"),
        clauses=[Clause(**clause) for clause in data.get("clauses", [])],
        aggregation=data.get("aggregation"),
        aggregation_metric=data.get("aggregation_metric"),
        aggregation_rank=int(data["aggregation_rank"]) if data.get("aggregation_rank") is not None else None,
        tie_break_aggregation=data.get("tie_break_aggregation"),
        tie_break_metric=data.get("tie_break_metric"),
        hop_count=int(data.get("hop_count", 0)),
        difficulty=data.get("difficulty", "low"),
        reject_unless_unique=bool(data.get("reject_unless_unique", True)),
        min_individual_clause_candidates=int(data.get("min_individual_clause_candidates", 3)),
        sampled_parameters=normalize_sampled_parameters(data.get("sampled_parameters")),
    )
