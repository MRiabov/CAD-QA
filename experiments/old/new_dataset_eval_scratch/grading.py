"""Parse a submitted answer and compare it with the stored gold answer."""

from __future__ import annotations

import re

from experiments.old.cq_query_scratch.grading import answers_match
from experiments.old.cq_query_scratch.models import AnswerFormat, TaskDefinition

NUMBER_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _numbers(text: str) -> list[float]:
    out: list[float] = []
    for token in NUMBER_RE.findall(text.replace(",", " ")):
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out


def parse_answer(raw: str | None, fmt: AnswerFormat) -> float | int | list[float] | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    match fmt:
        case AnswerFormat.NUMBER:
            nums = _numbers(text)
            return nums[0] if nums else None
        case AnswerFormat.INTEGER:
            nums = _numbers(text)
            if not nums:
                return None
            value = nums[0]
            return int(value) if float(value).is_integer() else None
        case AnswerFormat.COORDINATE:
            nums = _numbers(text)
            return nums[:3] if len(nums) >= 3 else None
    return None


def grade_answer(task: TaskDefinition, raw: str | None) -> tuple[bool, float | int | list[float] | None, str | None]:
    """Return (correct, parsed_answer, error_type)."""
    parsed = parse_answer(raw, task.native_answer_format)
    if parsed is None:
        return False, None, "unparseable_answer"
    ok = answers_match(parsed, task.gold_answer, task.native_answer_format, task.tolerance_rel, task.tolerance_abs)
    return ok, parsed, None
