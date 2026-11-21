"""Worker CLI contract tests.

The Go bridge and the Python worker agree on one request document on standard
input and one response document on standard output. These tests pin that
boundary before any pipeline stage logic exists.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import pytest

from cadqa_dataset_generator import cli


def run_worker(*args: str, request: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cadqa_dataset_generator.cli", *args],
        input=request,
        text=True,
        capture_output=True,
        check=False,
    )


def response_of(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(result.stdout)


def test_list_stages_is_json() -> None:
    result = run_worker("--list-stages")

    assert result.returncode == 0
    assert response_of(result) == {
        "stages": [
            "01d_normalize_programs",
            "02a_extract_cadquery_ast",
            "02b_execute_cadquery",
        ]
    }


def test_stage_not_implemented_is_data() -> None:
    result = run_worker("01d_normalize_programs", request="{}")

    assert result.returncode == 1
    assert response_of(result) == {
        "ok": False,
        "result": None,
        "error": {
            "code": "stage_not_implemented",
            "message": "pipeline stage 01d_normalize_programs is not implemented yet",
        },
    }


def test_unknown_stage_is_data() -> None:
    result = run_worker("99_not_a_stage", request="{}")

    assert result.returncode == 1
    body = response_of(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "unknown_stage"


def test_invalid_request_is_data() -> None:
    result = run_worker("01d_normalize_programs", request="not json")

    assert result.returncode == 1
    body = response_of(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_request"


def test_request_must_be_an_object() -> None:
    result = run_worker("01d_normalize_programs", request="[1, 2]")

    assert result.returncode == 1
    body = response_of(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_request"


def test_handle_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: dict[str, Any]) -> dict[str, Any]:
        return {"echo": request["value"]}

    monkeypatch.setattr(cli, "resolve_stage", lambda stage: runner)

    response = cli.handle("01d_normalize_programs", {"value": 3})

    assert response.ok is True
    assert response.result == {"echo": 3}
    assert response.error is None


def test_handle_stage_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: dict[str, Any]) -> dict[str, Any]:
        del request
        raise ValueError("bad input")

    monkeypatch.setattr(cli, "resolve_stage", lambda stage: runner)

    response = cli.handle("01d_normalize_programs", {})

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "stage_failed"
    assert "bad input" in response.error.message
