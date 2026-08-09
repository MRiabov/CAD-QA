"""CAD-QA tool-call contract: typed answer tools, extraction, and gold validation.

The model's completion is reasoning text ending with a JSON tool call envelope
``{"name": "submit_bbox", "arguments": {...}}``. One tool per answer format; no
raw-JSON emission anywhere. Comparison: exact for strings/ints, 1e-3 relative
for floats (user-specified). The 'text' format tolerates float-formatting
differences when the gold is a cq.Plane string (decomposed and compared as
vectors); otherwise exact after whitespace normalization.
"""
from __future__ import annotations

import json
import math
import re
from enum import StrEnum
from typing import Any, TypeAlias

from pydantic import BaseModel, Field, TypeAdapter

from reward_cadqa import _decode_gold

Vec3: TypeAlias = tuple[float, float, float]


class AnswerFormat(StrEnum):
    BBOX = "bbox"
    CANDIDATE_LABEL = "candidate_label"
    COORDINATE = "coordinate"
    INTEGER = "integer"
    JSON = "json"
    NUMBER = "number"
    TEXT = "text"


class ToolName(StrEnum):
    SUBMIT_LABEL = "submit_label"
    SUBMIT_TEXT = "submit_text"
    SUBMIT_INTEGER = "submit_integer"
    SUBMIT_NUMBER = "submit_number"
    SUBMIT_COORDINATE = "submit_coordinate"
    SUBMIT_BBOX = "submit_bbox"
    SUBMIT_WORKPLANE = "submit_workplane"
    COMPACT_TRACE = "compact_trace"


# --- typed tool arguments ---------------------------------------------------

class SubmitLabelArgs(BaseModel):
    label: str = Field(min_length=1, max_length=128, description="Candidate label, e.g. 'wp9'.")


class SubmitTextArgs(BaseModel):
    text: str = Field(min_length=1, max_length=1024, description="Free-text answer (entity id or cq.Plane string).")


class SubmitIntegerArgs(BaseModel):
    value: int = Field(description="Integer answer.")


class SubmitNumberArgs(BaseModel):
    value: float = Field(description="Numeric answer.")


class SubmitCoordinateArgs(BaseModel):
    value: Vec3 = Field(min_length=3, max_length=3, description="3D coordinate [x, y, z].")


class SubmitBboxArgs(BaseModel):
    min: Vec3 = Field(min_length=3, max_length=3, description="Bounding-box min corner [x, y, z].")
    max: Vec3 = Field(min_length=3, max_length=3, description="Bounding-box max corner [x, y, z].")


class SubmitWorkplaneArgs(BaseModel):
    feature_id: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=64)
    base: str = Field(min_length=1, max_length=64)
    origin: Vec3 = Field(min_length=3, max_length=3)
    x_dir: Vec3 = Field(min_length=3, max_length=3)
    normal: Vec3 = Field(min_length=3, max_length=3)


class CompactTraceArgs(BaseModel):
    reasoning: str = Field(min_length=1, max_length=8192, description="Hop-structured compressed reasoning chain.")


FORMAT_TO_TOOL: dict[AnswerFormat, ToolName] = {
    AnswerFormat.BBOX: ToolName.SUBMIT_BBOX,
    AnswerFormat.CANDIDATE_LABEL: ToolName.SUBMIT_LABEL,
    AnswerFormat.COORDINATE: ToolName.SUBMIT_COORDINATE,
    AnswerFormat.INTEGER: ToolName.SUBMIT_INTEGER,
    AnswerFormat.JSON: ToolName.SUBMIT_WORKPLANE,
    AnswerFormat.NUMBER: ToolName.SUBMIT_NUMBER,
    AnswerFormat.TEXT: ToolName.SUBMIT_TEXT,
}

_ARGS_MODELS: dict[ToolName, type[BaseModel]] = {
    ToolName.SUBMIT_LABEL: SubmitLabelArgs,
    ToolName.SUBMIT_TEXT: SubmitTextArgs,
    ToolName.SUBMIT_INTEGER: SubmitIntegerArgs,
    ToolName.SUBMIT_NUMBER: SubmitNumberArgs,
    ToolName.SUBMIT_COORDINATE: SubmitCoordinateArgs,
    ToolName.SUBMIT_BBOX: SubmitBboxArgs,
    ToolName.SUBMIT_WORKPLANE: SubmitWorkplaneArgs,
    ToolName.COMPACT_TRACE: CompactTraceArgs,
}

_ADAPTERS: dict[ToolName, TypeAdapter] = {
    name: TypeAdapter(model) for name, model in _ARGS_MODELS.items()
}


def format_to_tool(fmt: str) -> ToolName:
    return FORMAT_TO_TOOL[AnswerFormat(fmt)]


def tool_schema(name: ToolName) -> dict[str, Any]:
    """JSON schema of one tool for the teacher prompt."""
    return {
        "name": name.value,
        "parameters": _ARGS_MODELS[name].model_json_schema(),
    }


def validate_arguments(name: ToolName, arguments: dict[str, Any]) -> BaseModel | None:
    """Parse tool arguments against the tool's typed schema; None on mismatch."""
    try:
        return _ADAPTERS[name].validate_python(arguments)
    except Exception:
        return None


# --- extraction -------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _last_json_block(text: str) -> str | None:
    candidates = [m.group(1) for m in _CODE_FENCE_RE.finditer(text)]
    m = _JSON_BLOCK_RE.search(text)
    if m is not None:
        candidates.append(m.group(0))
    for candidate in reversed(candidates):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    return None


def extract_tool_call(text: str, expected: ToolName) -> tuple[ToolName, BaseModel] | None:
    """Parse the completion's tool call; returns (name, typed-args) or None.

    Prefers the envelope form; falls back to treating the last JSON block as
    the expected tool's arguments.
    """
    block = _last_json_block(text)
    if block is None:
        return None
    try:
        data = json.loads(block)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    arguments = data.get("arguments")
    if isinstance(name, str) and isinstance(arguments, dict):
        try:
            tool = ToolName(name)
        except ValueError:
            return None
        args = validate_arguments(tool, arguments)
        return (tool, args) if args is not None else None
    args = validate_arguments(expected, data)
    return (expected, args) if args is not None else None


# --- gold comparison --------------------------------------------------------

_REL_TOL = 1e-3


def _vec_close(a: Vec3, b: Vec3) -> bool:
    return all(math.isclose(x, y, rel_tol=_REL_TOL) for x, y in zip(a, b))


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


_PLANE_RE = re.compile(
    r"cq\.Plane\(origin=cq\.Vector\(([^)]*)\),\s*xDir=cq\.Vector\(([^)]*)\),\s*normal=cq\.Vector\(([^)]*)\)\)"
)


def _decompose_plane(s: str) -> tuple[Vec3, Vec3, Vec3] | None:
    m = _PLANE_RE.search(s)
    if m is None:
        return None

    def vec(group: str) -> Vec3:
        return tuple(float(x) for x in group.split(","))  # type: ignore[return-value]

    return vec(m.group(1)), vec(m.group(2)), vec(m.group(3))


def _text_matches(pred: str, gold: str) -> bool:
    if _normalize_text(pred) == _normalize_text(gold):
        return True
    gp = _decompose_plane(gold)
    if gp is None:
        return False
    pp = _decompose_plane(pred)
    return pp is not None and all(_vec_close(a, b) for a, b in zip(pp, gp))


def _json_matches(pred: SubmitWorkplaneArgs, gold: dict[str, Any]) -> bool:
    frame = gold.get("coordinate_frame")
    if not isinstance(frame, str):
        return False
    parts = _decompose_plane(frame)
    if parts is None:
        return False
    return (
        pred.feature_id == gold.get("feature_id")
        and pred.operation == gold.get("operation")
        and pred.base == gold.get("base")
        and _vec_close(pred.origin, parts[0])
        and _vec_close(pred.x_dir, parts[1])
        and _vec_close(pred.normal, parts[2])
    )


def tool_call_matches(name: ToolName, args: BaseModel, gold_raw: str, fmt: str) -> bool:
    """Whether a parsed tool call matches the row's gold."""
    gold = _decode_gold(gold_raw)
    match name:
        case ToolName.SUBMIT_LABEL:
            return isinstance(gold, str) and args.label == gold  # type: ignore[attr-defined]
        case ToolName.SUBMIT_TEXT:
            return isinstance(gold, str) and _text_matches(args.text, gold)  # type: ignore[attr-defined]
        case ToolName.SUBMIT_INTEGER:
            return isinstance(gold, int) and args.value == gold  # type: ignore[attr-defined]
        case ToolName.SUBMIT_NUMBER:
            return isinstance(gold, (int, float)) and math.isclose(float(args.value), float(gold), rel_tol=_REL_TOL)  # type: ignore[attr-defined]
        case ToolName.SUBMIT_COORDINATE:
            return isinstance(gold, list) and len(gold) == 3 and _vec_close(args.value, tuple(float(x) for x in gold))  # type: ignore[attr-defined]
        case ToolName.SUBMIT_BBOX:
            return (
                isinstance(gold, dict)
                and isinstance(gold.get("min"), list)
                and isinstance(gold.get("max"), list)
                and _vec_close(args.min, tuple(float(x) for x in gold["min"]))  # type: ignore[attr-defined]
                and _vec_close(args.max, tuple(float(x) for x in gold["max"]))  # type: ignore[attr-defined]
            )
        case ToolName.SUBMIT_WORKPLANE:
            return isinstance(gold, dict) and _json_matches(args, gold)  # type: ignore[arg-type]
        case ToolName.COMPACT_TRACE:
            return True
        case _:
            return False


def tool_call_matches_raw(completion: str, expected: ToolName, gold_raw: str, fmt: str) -> bool:
    parsed = extract_tool_call(completion, expected)
    return parsed is not None and tool_call_matches(parsed[0], parsed[1], gold_raw, fmt)
