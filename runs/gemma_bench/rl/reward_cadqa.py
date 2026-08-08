"""Self-contained CAD-QA reward function for GRPO (drop-in for Unsloth Studio).

This file intentionally has NO imports from the cad_qa package so it can be
pasted into a training notebook (Unsloth Studio / Colab / Vast) and used as the
verifiable reward for RL. It mirrors the repo grader exactly:
`parse_answer(raw, answer_format)` + exact match against the gold answer.

Reward contract for GRPO-style loops:
    reward_cadqa(gold_answer, answer_format, completion) -> float  # 0.0 or 1.0

The dataset rows must carry `answer_format` and `gold_answer` (see
`export_rl_data.py` / `docs/rl_runbook.md`).
"""

from __future__ import annotations

import ast
import json
from typing import Any


def parse_answer(text: str, answer_format: str) -> Any:
    stripped = text.strip()
    if answer_format in {"entity_id", "candidate_label"}:
        return stripped
    if answer_format == "coordinate":
        return _parse_coordinate_answer(stripped)
    if answer_format == "integer":
        return int(stripped)
    if answer_format == "number":
        return float(stripped)
    if answer_format in {"bbox", "json"}:
        return json.loads(stripped)
    if answer_format == "boolean":
        return stripped.lower() in {"true", "yes", "1"}
    return stripped


def _parse_coordinate_answer(text: str) -> list[float]:
    value = ast.literal_eval(text)
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("coordinate answer must be a 3-item tuple or list")
    return [_clean_number(float(component)) for component in value]


def _clean_number(value: float) -> float | int:
    rounded = round(value, 6)
    if rounded == 0:
        rounded = 0.0
    if float(rounded).is_integer():
        return int(rounded)
    return rounded


def _gold(gold_answer: Any) -> Any:
    """Decode JSON-encoded gold answers (parquet stores them as JSON strings)."""
    if isinstance(gold_answer, str):
        try:
            return json.loads(gold_answer)
        except Exception:  # noqa: BLE001 - plain strings (jsonl path) stay as-is
            return gold_answer
    return gold_answer


def reward_cadqa(gold_answer: Any, answer_format: str, completion: str) -> float:
    """0.0/1.0 exact-match reward for one completion."""
    gold = _gold(gold_answer)
    try:
        parsed = parse_answer(completion, answer_format)
    except Exception:  # noqa: BLE001 - unparseable output is a wrong answer
        return 0.0
    return 1.0 if parsed == gold else 0.0


def reward_batch(rows: list[dict], completions: list[str]) -> list[float]:
    """Reward for a batch of (row, completion) pairs, same order."""
    return [
        reward_cadqa(row["gold_answer"], row["answer_format"], comp)
        for row, comp in zip(rows, completions)
    ]
