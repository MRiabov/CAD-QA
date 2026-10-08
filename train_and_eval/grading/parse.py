"""Answer parsing helpers."""

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
