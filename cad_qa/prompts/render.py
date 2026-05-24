"""Render prompts from query programs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cad_qa.prompts.templates import (
    CHECKLIST_TEMPLATE_ID,
    PROMPT_VERSION,
    aggregation_prompt,
    checklist_prompt,
    clause_prompt,
    no_clause_prompt,
)
from cad_qa.prompts.wording_gates import banned_terms
from cad_qa.query.ir import Clause
from cad_qa.query.ir import QueryProgram


@dataclass(frozen=True)
class RenderedPrompt:
    prompt: str
    prompt_version: str
    prompt_template_id: str
    clue_map: list[dict[str, Any]]
    warnings: list[str]


def render_prompt(source_code: str, query: QueryProgram) -> RenderedPrompt:
    clues = [clause_prompt(clause, query=query) for clause in query.clauses]
    if query.aggregation and query.aggregation_metric:
        clues.append(aggregation_prompt(query.aggregation, query.aggregation_metric))
    if not clues:
        clues.append(no_clause_prompt(query.target_type))
    prompt = checklist_prompt(source_code, clues, query.answer_type)
    warnings = banned_terms(prompt)
    template_id = prompt_template_id(query)
    clue_map = []
    for index, clue in enumerate(clues):
        clause_id = query.clauses[index].id if index < len(query.clauses) else "aggregation"
        clue_map.append(
            {
                "clue_index": index,
                "clause_id": clause_id,
                "template_id": template_id,
                "prompt_version": PROMPT_VERSION,
                "text": clue,
            }
        )
    return RenderedPrompt(prompt, PROMPT_VERSION, template_id, clue_map, warnings)


def prompt_template_id(query: QueryProgram) -> str:
    """Return a stable, coarse template ID for release/reporting quotas."""

    clause_shape = "_".join(_clause_shape(clause) for clause in query.clauses) or "no_clauses"
    aggregation_shape = f"{query.aggregation}_{query.aggregation_metric}" if query.aggregation else "no_aggregation"
    return f"{CHECKLIST_TEMPLATE_ID}:{query.target_type}:{clause_shape}:{aggregation_shape}"


def prompt_template_id_from_mapping(query: dict[str, Any]) -> str:
    clauses = query.get("clauses") or []
    clause_shape = "_".join(_clause_mapping_shape(clause) for clause in clauses if isinstance(clause, dict))
    clause_shape = clause_shape or "no_clauses"
    aggregation = query.get("aggregation")
    aggregation_metric = query.get("aggregation_metric")
    aggregation_shape = f"{aggregation}_{aggregation_metric}" if aggregation else "no_aggregation"
    return f"{CHECKLIST_TEMPLATE_ID}:{query.get('target_type', 'unknown')}:{clause_shape}:{aggregation_shape}"


def _clause_shape(clause: Clause) -> str:
    if clause.kind == "has_relation":
        return f"relation_{clause.relation or 'unknown'}"
    if clause.kind == "has_measurement":
        return f"measurement_{clause.metric or 'unknown'}"
    if clause.kind == "reference_measurement":
        return f"reference_{clause.metric or 'unknown'}"
    if clause.kind == "metric_compare":
        return f"metric_compare_{clause.metric or 'unknown'}_{clause.operator or 'op'}"
    if clause.kind == "property_equals":
        return f"property_{clause.metric or 'unknown'}"
    return clause.kind


def _clause_mapping_shape(clause: dict[str, Any]) -> str:
    kind = clause.get("kind")
    if kind == "has_relation":
        return f"relation_{clause.get('relation') or 'unknown'}"
    if kind == "has_measurement":
        return f"measurement_{clause.get('metric') or 'unknown'}"
    if kind == "reference_measurement":
        return f"reference_{clause.get('metric') or 'unknown'}"
    if kind == "metric_compare":
        return f"metric_compare_{clause.get('metric') or 'unknown'}_{clause.get('operator') or 'op'}"
    if kind == "property_equals":
        return f"property_{clause.get('metric') or 'unknown'}"
    return str(kind or "unknown")
