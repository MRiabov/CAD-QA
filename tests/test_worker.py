"""Worker protocol tests.

The Go bridge and the Python worker agree on a long-lived, newline-delimited
JSON protocol: one ready document, then one response per request line. These
tests pin that boundary before any pipeline stage logic exists.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from typing import Any

import pytest

from cadqa_dataset_generator import worker

S01D_REQUEST: dict[str, Any] = {
    "program_pool_part_paths": ["runs/run0001/01c/pool-000.parquet"],
    "output_directory": "runs/run0001/01d",
    "shard_index": 0,
}
S01D_RESULT: dict[str, Any] = {
    "normalized_part_path": "runs/run0001/01d/normalized-000.parquet",
    "failure_part_path": "runs/run0001/01d/failures-000.parquet",
    "normalized_count": 10,
    "failure_count": 1,
    "normalization_version": "01d-v1",
}


def run_worker(*args: str, request: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cadqa_dataset_generator.worker", *args],
        input=request,
        text=True,
        capture_output=True,
        check=False,
    )


def responses_of(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def response_of(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return responses_of(result)[-1]


def resolver(runner: Callable[..., Any]) -> Callable[[str], Callable[..., Any]]:
    def resolve(pipeline_stage: str) -> Callable[..., Any]:
        del pipeline_stage
        return runner

    return resolve


def test_list_stages_is_json() -> None:
    result = run_worker("--list-stages")

    assert result.returncode == 0
    assert response_of(result) == {
        "protocol_version": 1,
        "stages": [
            "01d_normalize_programs",
            "02a_extract_cadquery_ast",
            "02b_execute_cadquery",
        ],
    }


def test_ready_document() -> None:
    result = run_worker("01d_normalize_programs")

    assert result.returncode == 0
    assert responses_of(result) == [
        {"ok": True, "protocol_version": 1, "result": {"ready": True}}
    ]


def test_stage_not_implemented_is_data() -> None:
    # 02a has no typed contract yet, so it exercises the free-form path.
    result = run_worker("02a_extract_cadquery_ast", request="{}\n")

    assert result.returncode == 0
    assert response_of(result) == {
        "ok": False,
        "protocol_version": 1,
        "error": {
            "code": "stage_not_implemented",
            "message": "pipeline stage 02a_extract_cadquery_ast is not implemented yet",
        },
    }


def test_unknown_stage_is_data() -> None:
    result = run_worker("99_not_a_stage", request="{}\n")

    assert result.returncode == 1
    body = response_of(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "unknown_stage"


def test_invalid_request_is_data() -> None:
    result = run_worker("01d_normalize_programs", request="not json\n")

    assert result.returncode == 0
    body = response_of(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_request"


def test_request_must_be_an_object() -> None:
    result = run_worker("01d_normalize_programs", request="[1, 2]\n")

    assert result.returncode == 0
    body = response_of(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_request"


def test_worker_serves_multiple_requests() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cadqa_dataset_generator.worker",
            "02a_extract_cadquery_ast",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdin is not None
        assert process.stdout is not None

        ready = json.loads(process.stdout.readline())
        assert ready == {
            "ok": True,
            "protocol_version": 1,
            "result": {"ready": True},
        }

        process.stdin.write("{}\n{}\n")
        process.stdin.flush()

        first = json.loads(process.stdout.readline())
        second = json.loads(process.stdout.readline())
        assert first["error"]["code"] == "stage_not_implemented"
        assert second["error"]["code"] == "stage_not_implemented"

        process.stdin.close()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_handle_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: dict[str, Any]) -> dict[str, Any]:
        return {"echo": request["value"]}

    monkeypatch.setattr(worker, "resolve_pipeline_stage", resolver(runner))

    response = worker.handle("02a_extract_cadquery_ast", {"value": 3})

    assert response.ok is True
    assert response.result == {"echo": 3}
    assert response.error is None


def test_handle_stage_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: dict[str, Any]) -> dict[str, Any]:
        del request
        raise ValueError("bad input")

    monkeypatch.setattr(worker, "resolve_pipeline_stage", resolver(runner))

    response = worker.handle("02a_extract_cadquery_ast", {})

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "stage_failed"
    assert "bad input" in response.error.message


def test_handle_invalid_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: dict[str, Any]) -> Any:
        del request
        return [1, 2]

    monkeypatch.setattr(worker, "resolve_pipeline_stage", resolver(runner))

    response = worker.handle("02a_extract_cadquery_ast", {})

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "invalid_result"


def test_handle_rejects_invalid_typed_request() -> None:
    response = worker.handle("01d_normalize_programs", {})

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "invalid_request"


def test_handle_accepts_typed_request_until_stage_lands() -> None:
    response = worker.handle("01d_normalize_programs", S01D_REQUEST)

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "stage_not_implemented"


def test_handle_rejects_invalid_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {}

    monkeypatch.setattr(worker, "resolve_pipeline_stage", resolver(runner))

    response = worker.handle("01d_normalize_programs", S01D_REQUEST)

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "invalid_result"


def test_handle_accepts_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(request: Any) -> dict[str, Any]:
        assert request.shard_index == 0
        return S01D_RESULT

    monkeypatch.setattr(worker, "resolve_pipeline_stage", resolver(runner))

    response = worker.handle("01d_normalize_programs", S01D_REQUEST)

    assert response.ok is True
    assert response.result == S01D_RESULT
