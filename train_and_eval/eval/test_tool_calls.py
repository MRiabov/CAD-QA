"""Unit tests for the CAD-QA tool-call contract (tool_calls.py)."""
import json
import os as _os
import sys

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import pytest

from tool_calls import (
    ToolName,
    TraceStep,
    TraceStepKind,
    execute_code,
    extract_tool_call,
    format_to_tool,
    render_call_tokens,
    render_tool_response,
    render_trace_steps,
    tool_call_matches_raw,
    validate_arguments,
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


# --- run_code compute tool --------------------------------------------------

def test_run_code_extract_and_validate():
    tool = ToolName.RUN_CODE
    parsed = extract_tool_call('{"name": "run_code", "arguments": {"code": "print(1)"}}', tool)
    assert parsed is not None and parsed[0] == tool
    assert parsed[1].code == "print(1)"  # type: ignore[attr-defined]
    assert validate_arguments(tool, {"code": "x = np.array([1, 2])"}) is not None
    assert validate_arguments(tool, {"code": ""}) is None
    assert validate_arguments(tool, {}) is None
    assert tool_call_matches_raw('{"name": "run_code", "arguments": {"code": "print(1)"}}', tool, "", "text")


def test_run_code_roundtrip_in_trace_steps():
    # a full multi-turn trace: reasoning -> run_code call -> result -> submit
    steps = [
        TraceStep(kind=TraceStepKind.TEXT, text="Let me compute the volume."),
        TraceStep(kind=TraceStepKind.TOOL_CALL, name=ToolName.RUN_CODE,
                  arguments={"code": "print(2*3*4)"}),
        TraceStep(kind=TraceStepKind.TOOL_RESULT, name=ToolName.RUN_CODE, text="24"),
        TraceStep(kind=TraceStepKind.TEXT, text="The volume is 24."),
        TraceStep(kind=TraceStepKind.TOOL_CALL, name=ToolName.SUBMIT_NUMBER,
                  arguments={"value": 24}),
    ]
    rendered = render_trace_steps(steps)
    assert "<|tool_call>call:run_code{\"code\":\"print(2*3*4)\"}<tool_call|>" in rendered
    assert "<|tool_response>response:run_code{value:<|\"|>24<|\"|>}<tool_response|>" in rendered
    assert "<|tool_call>call:submit_number{\"value\":24}<tool_call|>" in rendered
    assert rendered.index("run_code{") < rendered.index("response:run_code") < rendered.index("submit_number")


def test_render_helpers():
    assert render_call_tokens(ToolName.RUN_CODE, {"code": "print(1)"}) == (
        '<|tool_call>call:run_code{"code":"print(1)"}<tool_call|>')
    assert render_tool_response(ToolName.RUN_CODE, "24") == (
        '<|tool_response>response:run_code{value:<|"|>24<|"|>}<tool_response|>')
    # multi-line values are JSON-escaped onto one line
    assert render_tool_response(ToolName.RUN_CODE, "a\nb") == (
        '<|tool_response>response:run_code{value:<|"|>a\\nb<|"|>}<tool_response|>')


def test_execute_code_ok():
    assert execute_code("print(2*3*4)").strip() == "24"
    assert execute_code("import numpy as np\nprint(np.sqrt(16))").strip() == "4.0"


def test_execute_code_exception():
    r = execute_code("raise ValueError('boom')")
    assert r.startswith("Error:")
    assert "boom" in r


def test_execute_code_forbidden_import():
    r = execute_code("import os\nprint('leak')")
    assert r.startswith("Error:")
    assert "blocked" in r
    r2 = execute_code("import cadquery\nprint('leak')")
    assert r2.startswith("Error:")
    r3 = execute_code("import posix\nprint('leak')")
    assert r3.startswith("Error:")
    # numpy file-IO is stripped from the np handle
    r4 = execute_code("import numpy as np\nnp.loadtxt('/etc/hostname')")
    assert r4.startswith("Error:")


def test_execute_code_timeout():
    r = execute_code("import time\ntime.sleep(30)", timeout=1)
    assert "timed out" in r


def test_execute_code_no_file_write():
    r = execute_code("open('/tmp/cadqa_sandbox_pwn', 'w').write('x')")
    assert r.startswith("Error:")
    import os
    assert not os.path.exists("/tmp/cadqa_sandbox_pwn")

