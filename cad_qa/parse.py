"""Answer parsing and grading policies."""

from __future__ import annotations

import json
import math
import re
from typing import Any

NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def grade_candidate(row: dict[str, Any], candidate: str) -> dict[str, Any]:
    policy = row.get("parse_policy")
    answer = row.get("answer")
    try:
        if policy == "strict_integer_v1":
            parsed = parse_strict_integer(candidate)
            correct = parsed == answer
        elif policy == "strict_enum_v1":
            parsed = candidate.strip()
            choices = row.get("choices") or []
            correct = parsed == answer and (not choices or parsed in choices)
        elif policy == "strict_json_bbox_v1":
            parsed = parse_bbox(candidate)
            correct = bbox_close(parsed, answer, float(row.get("numeric_tolerance") or 0.0))
        elif policy == "strict_json_v1":
            parsed = parse_json(candidate)
            correct = parsed == answer
        elif policy == "numeric_4_sigfig_v1":
            parsed = parse_single_number(candidate)
            correct = number_close(parsed, float(answer), row.get("numeric_tolerance"))
        else:
            parsed = candidate.strip()
            correct = parsed == answer
    except ValueError as exc:
        return {"valid": False, "correct": False, "parsed": None, "error": str(exc)}
    return {"valid": True, "correct": bool(correct), "parsed": parsed, "error": None}


def parse_strict_integer(candidate: str) -> int:
    stripped = candidate.strip()
    if not re.fullmatch(r"\d+", stripped):
        raise ValueError("expected exactly one non-negative integer")
    return int(stripped)


def parse_single_number(candidate: str) -> float:
    matches = NUMBER_RE.findall(candidate.strip())
    if len(matches) != 1:
        raise ValueError("expected exactly one finite number")
    value = float(matches[0])
    if not math.isfinite(value):
        raise ValueError("number is not finite")
    return value


def parse_bbox(candidate: str) -> dict[str, list[float]]:
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("expected JSON bbox") from exc
    if not isinstance(value, dict) or set(value) < {"min", "max"}:
        raise ValueError("bbox must contain min and max")
    parsed = {"min": _triplet(value["min"]), "max": _triplet(value["max"])}
    return parsed


def parse_json(candidate: str) -> Any:
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("expected JSON") from exc


def number_close(parsed: float, answer: float, numeric_tolerance: Any) -> bool:
    tolerance = max(float(numeric_tolerance or 0.0), four_sigfig_half_unit(answer))
    return abs(parsed - answer) <= tolerance


def bbox_close(parsed: dict[str, list[float]], answer: Any, numeric_tolerance: float) -> bool:
    if not isinstance(answer, dict):
        return False
    for key in ("min", "max"):
        expected = answer.get(key)
        if not isinstance(expected, list) or len(expected) != 3:
            return False
        for got, want in zip(parsed[key], expected, strict=True):
            tolerance = max(numeric_tolerance, four_sigfig_half_unit(float(want)))
            if abs(float(got) - float(want)) > tolerance:
                return False
    return True


def four_sigfig_half_unit(answer: float) -> float:
    if answer == 0:
        return 0.0
    return 0.5 * 10 ** (math.floor(math.log10(abs(answer))) - 3)


def _triplet(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("bbox coordinates must be length-3 arrays")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise ValueError("bbox coordinates must be finite")
    return result
