"""Detect answers that appear as numeric literals in the rendered prompt."""

from __future__ import annotations

import re

from experiments.old.cq_query_scratch.models import AnswerFormat, TaskDefinition

NUMBER_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _numbers(text: str) -> list[float]:
    out = []
    for token in NUMBER_RE.findall(text):
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(1e-6, 1e-3 * abs(b))


def audit_prompt(task: TaskDefinition, prompt: str) -> str | None:
    """Return a leak reason, or None. Counts are not flagged: small integers appear everywhere."""
    match task.native_answer_format:
        case AnswerFormat.NUMBER:
            gold = float(task.gold_answer)
            if any(_close(value, gold) for value in _numbers(prompt)):
                return "numeric_literal"
        case AnswerFormat.COORDINATE:
            gold = [float(x) for x in task.gold_answer]
            forms = [
                "(" + ", ".join(str(x) for x in gold) + ")",
                "[" + ", ".join(str(x) for x in gold) + "]",
                "(" + ", ".join(f"{x:.4g}" for x in gold) + ")",
                "[" + ", ".join(f"{x:.4g}" for x in gold) + "]",
            ]
            if any(form in prompt for form in forms):
                return "coordinate_literal"
        case AnswerFormat.INTEGER:
            return None
    return None
