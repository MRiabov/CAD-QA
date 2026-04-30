"""Answer parsing helpers."""

from __future__ import annotations

import json
from typing import Any


def parse_answer(text: str, answer_format: str) -> Any:
    stripped = text.strip()
    if answer_format == "entity_id":
        return stripped
    if answer_format == "integer":
        return int(stripped)
    if answer_format == "number":
        return float(stripped)
    if answer_format in {"bbox", "json"}:
        return json.loads(stripped)
    if answer_format == "boolean":
        return stripped.lower() in {"true", "yes", "1"}
    return stripped
