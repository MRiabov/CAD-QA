"""Render prompts from query programs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cad_qa.prompts.templates import PROMPT_VERSION, checklist_prompt
from cad_qa.prompts.wording_gates import banned_terms
from cad_qa.query.ir import QueryProgram


@dataclass(frozen=True)
class RenderedPrompt:
    prompt: str
    prompt_version: str
    clue_map: list[dict[str, Any]]
    warnings: list[str]


def render_prompt(source_code: str, query: QueryProgram) -> RenderedPrompt:
    clues = [clause.text or _default_clause_text(clause.kind) for clause in query.clauses]
    if query.aggregation and query.aggregation_metric:
        direction = "largest" if query.aggregation == "argmax" else "smallest"
        clues.append(f"Among the remaining candidates, choose the one with the {direction} `{query.aggregation_metric}` value.")
    if not clues:
        clues.append(f"The target is a `{query.target_type}` entity from the script.")
    prompt = checklist_prompt(source_code, clues, query.answer_type)
    warnings = banned_terms(prompt)
    clue_map = [
        {"clue_index": index, "clause_id": query.clauses[index].id if index < len(query.clauses) else "aggregation", "text": clue}
        for index, clue in enumerate(clues)
    ]
    return RenderedPrompt(prompt, PROMPT_VERSION, clue_map, warnings)


def _default_clause_text(kind: str) -> str:
    return f"The target satisfies the hidden `{kind}` clause."
