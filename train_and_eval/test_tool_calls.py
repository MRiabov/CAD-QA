"""Unit tests for the CAD-QA tool-call contract (tool_calls.py)."""
import json

import pytest

from tool_calls import (
    ToolName,
    extract_tool_call,
    format_to_tool,
    tool_call_matches,
    tool_call_matches_raw,
)

BBOX_GOLD = {"min": [-25.74, 92.42, -56.0], "max": [-16.26, 95.58, -46.0]}
PLANE_GOLD = (
    "cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))"
)
WORKPLANE_GOLD = {
    "base": "cq",
    "coordinate_frame": "cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))",
    "feature_id": "wp23",
    "operation": "Workplane",
}


def _env(fmt, comp):
    return format_to_tool(fmt), json.dumps(BBOX_GOLD) if fmt == "bbox" else (
        json.dumps(WORKPLANE_GOLD) if fmt == "json" else (PLANE_GOLD if fmt == "text" else _gold(fmt))
    ), fmt

def _gold(fmt):
    return {"candidate_label": "wp9", "coordinate": [-94.330903, -20, -22.73805],
            "integer": 1, "number": 374900}[fmt]


@pytest.mark.parametrize("fmt,comp", [
    ("candidate_label", '{"name": "submit_label", "arguments": {"label": "wp9"}}'),
    ("coordinate", '{"name": "submit_coordinate", "arguments": {"value": [-94.331, -20.0, -22.738]}}'),
    ("integer", '{"name": "submit_integer", "arguments": {"value": 1}}'),
    ("number", '{"name": "submit_number", "arguments": {"value": 374900}}'),
    ("bbox", '{"name": "submit_bbox", "arguments": {"min": [-25.74, 92.42, -56.0], "max": [-16.26, 95.58, -46.0]}}'),
    ("json", '{"name": "submit_workplane", "arguments": {"feature_id": "wp23", "operation": "Workplane", "base": "cq", "origin": [28, 85, 18], "x_dir": [3, -1, 0], "normal": [1, 3, 0]}}'),
    ("text", '{"name": "submit_text", "arguments": {"text": "cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))"}}'),
])
def test_valid_envelope_matches(fmt, comp):
    tool, gold, _ = _env(fmt, comp)
    assert tool_call_matches_raw(comp, tool, gold, fmt)


def test_number_tolerance():
    tool, gold, _ = _env("number", None)
    assert tool_call_matches_raw('{"name": "submit_number", "arguments": {"value": 374900.1}}', tool, gold, "number")
    assert not tool_call_matches_raw('{"name": "submit_number", "arguments": {"value": 375300}}', tool, gold, "number")


def test_bbox_tolerance_and_order():
    tool, gold, _ = _env("bbox", None)
    assert tool_call_matches_raw(
        '{"name": "submit_bbox", "arguments": {"min": [-25.742, 92.419, -56.0], "max": [-16.261, 95.58, -46.0]}}',
        tool, gold, "bbox")
    assert not tool_call_matches_raw(
        '{"name": "submit_bbox", "arguments": {"min": [-25.0, 92.42, -56.0], "max": [-16.26, 95.58, -46.0]}}',
        tool, gold, "bbox")


def test_text_plane_float_formatting():
    tool, gold, _ = _env("text", None)
    assert tool_call_matches_raw(
        '{"name": "submit_text", "arguments": {"text": "cq.Plane(origin=cq.Vector(-72.0, 53.0, 36.0), xDir=cq.Vector(-2.0, -2.0, 0.0), normal=cq.Vector(-2.0, 2.0, 0.0))"}}',
        tool, gold, "text")
    assert not tool_call_matches_raw(
        '{"name": "submit_text", "arguments": {"text": "cq.Plane(origin=cq.Vector(0, 0, 0), xDir=cq.Vector(1, 0, 0), normal=cq.Vector(0, 0, 1))"}}',
        tool, gold, "text")


def test_workplane_mismatch():
    tool, gold, _ = _env("json", None)
    comp = '{"name": "submit_workplane", "arguments": {"feature_id": "wp99", "operation": "Workplane", "base": "cq", "origin": [28, 85, 18], "x_dir": [3, -1, 0], "normal": [1, 3, 0]}}'
    assert not tool_call_matches_raw(comp, tool, gold, "json")


def test_reasoning_prefix_and_fence():
    tool = ToolName.SUBMIT_LABEL
    comp = 'Let me think... The id is wp9.\n```json\n{"name": "submit_label", "arguments": {"label": "wp9"}}\n```'
    parsed = extract_tool_call(comp, tool)
    assert parsed is not None and parsed[0] == tool
    assert tool_call_matches_raw(comp, tool, "wp9", "candidate_label")


def test_bare_arguments_fallback():
    tool = ToolName.SUBMIT_INTEGER
    parsed = extract_tool_call('The value is 5. {"value": 5}', tool)
    assert parsed is not None and parsed[0] == tool


def test_malformed_rejected():
    assert extract_tool_call("no json here", ToolName.SUBMIT_LABEL) is None
    assert extract_tool_call('{"name": "submit_label", "arguments": {"label": 42}}', ToolName.SUBMIT_LABEL) is None
    assert extract_tool_call('{"name": "nope", "arguments": {"label": "wp9"}}', ToolName.SUBMIT_LABEL) is None
    assert extract_tool_call('{"name": "submit_bbox", "arguments": {"min": "nope"}}', ToolName.SUBMIT_BBOX) is None
    assert extract_tool_call('{"label": "wp9", "extra": [}', ToolName.SUBMIT_LABEL) is None


def test_wrong_label_rejected():
    tool = ToolName.SUBMIT_LABEL
    assert not tool_call_matches_raw('{"name": "submit_label", "arguments": {"label": "wp3"}}', tool, "wp9", "candidate_label")


def test_compact_trace_validates():
    tool = ToolName.COMPACT_TRACE
    parsed = extract_tool_call('{"name": "compact_trace", "arguments": {"reasoning": "step1 -> step2"}}', tool)
    assert parsed is not None and parsed[0] == tool
    assert not tool_call_matches_raw('{"name": "compact_trace", "arguments": {"reasoning": ""}}', tool, "", "text")
