"""Worker entry point for the CAD-QA dataset generator.

The Go orchestrator starts one long-lived worker per pipeline stage:

    python -m cadqa_dataset_generator.worker <pipeline_stage>

The worker imports its pipeline stage module, calls its optional ``preload()`` hook, and
writes one ready document to standard output:

    {"ok": true, "result": {"ready": true}}

It then serves newline-delimited JSON requests: one JSON request document per
line on standard input, one JSON response document per line on standard output:

    {"ok": true, "result": ...}
    {"ok": false, "error": {"code": "...", "message": "..."}}

A handled pipeline stage rejection is data, not a process exit. Exit code 0
means the worker reached EOF or was closed cleanly. Exit code 1 means the
worker could not start its pipeline stage. Logs go to standard error so standard output
stays one JSON document per line.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from typing import Any

import orjson
from pydantic import BaseModel, Field

from cadqa_dataset_generator import StageNotImplemented

StageRunner = Callable[[dict[str, Any]], dict[str, Any]]

# TODO(bootstrap): replace the freeform request and result dicts with typed
# pipeline stage models as each pipeline stage lands.

# Wire pipeline stage name -> module that implements it. The module name is `s` + name.
# The wire name is the snake-case pipeline stage name used by the failure record.
STAGE_MODULES: dict[str, str] = {
    "01d_normalize_programs": "cadqa_dataset_generator.s01d_normalize_programs",
    "02a_extract_cadquery_ast": "cadqa_dataset_generator.s02a_extract_cadquery_ast",
    "02b_execute_cadquery": "cadqa_dataset_generator.s02b_execute_cadquery",
}


class WorkerError(BaseModel):
    """A structured worker error returned as data."""

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class WorkerResponse(BaseModel):
    """The one JSON document a worker writes for one request."""

    ok: bool
    result: dict[str, Any] | None = None
    error: WorkerError | None = None


def stage_names() -> list[str]:
    """Return the dispatchable stage names in stable order."""

    return sorted(STAGE_MODULES)


def resolve_stage(stage: str) -> StageRunner:
    """Import the module for one pipeline stage and return its ``run`` function."""

    module_name = STAGE_MODULES[stage]
    module = importlib.import_module(module_name)
    runner = getattr(module, "run", None)
    if runner is None or not callable(runner):
        raise TypeError(f"stage module {module_name} has no callable run()")
    return runner


def preload_stage(stage: str) -> None:
    """Import a pipeline stage module and call its optional ``preload`` hook."""

    module = importlib.import_module(STAGE_MODULES[stage])
    preload = getattr(module, "preload", None)
    if callable(preload):
        preload()


def _failure(code: str, message: str) -> WorkerResponse:
    return WorkerResponse(ok=False, error=WorkerError(code=code, message=message))


def handle(stage: str, request: dict[str, Any]) -> WorkerResponse:
    """Dispatch one request and convert pipeline stage failures to data."""

    try:
        runner = resolve_stage(stage)
    except KeyError:
        expected = ", ".join(stage_names())
        return _failure(
            "unknown_stage",
            f"unknown stage {stage!r}; expected one of {expected}",
        )
    except (ImportError, TypeError) as exc:
        return _failure("stage_unavailable", str(exc))

    try:
        result = runner(request)
    except StageNotImplemented as exc:
        return _failure("stage_not_implemented", str(exc))
    except Exception as exc:  # noqa: BLE001 - the worker boundary converts failures to data
        return _failure("stage_failed", f"{type(exc).__name__}: {exc}")

    if not isinstance(result, dict):
        return _failure(
            "invalid_result",
            f"pipeline stage {stage} returned {type(result).__name__}, want dict",
        )
    return WorkerResponse(ok=True, result=result)


def _write_document(document: dict[str, Any]) -> None:
    payload = orjson.dumps(document, option=orjson.OPT_SORT_KEYS)
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()


def _serve(stage: str) -> int:
    """Preload one pipeline stage, signal ready, and serve requests until EOF."""

    try:
        resolve_stage(stage)
    except KeyError:
        expected = ", ".join(stage_names())
        _write_document(
            _failure(
                "unknown_stage",
                f"unknown stage {stage!r}; expected one of {expected}",
            ).model_dump(mode="json")
        )
        return 1
    except (ImportError, TypeError) as exc:
        _write_document(_failure("stage_unavailable", str(exc)).model_dump(mode="json"))
        return 1

    try:
        preload_stage(stage)
    except Exception as exc:  # noqa: BLE001 - a preload failure is a pipeline stage failure
        _write_document(
            _failure(
                "stage_unavailable",
                f"{type(exc).__name__}: {exc}",
            ).model_dump(mode="json")
        )
        return 1

    _write_document({"ok": True, "result": {"ready": True}})

    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        try:
            request = orjson.loads(line)
            if not isinstance(request, dict):
                raise TypeError("worker request must be a JSON object")
        except (orjson.JSONDecodeError, TypeError) as exc:
            response = _failure("invalid_request", str(exc))
        else:
            response = handle(stage, request)
        _write_document(response.model_dump(mode="json"))

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker command line."""

    parser = argparse.ArgumentParser(
        prog="cadqa_dataset_generator.worker",
        description="Run one CAD-QA dataset generator Python stage worker.",
    )
    parser.add_argument("stage", nargs="?", help="pipeline stage to serve")
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="print the dispatchable stage names as JSON",
    )
    args = parser.parse_args(argv)

    if args.list_stages:
        _write_document({"stages": stage_names()})
        return 0
    if args.stage is None:
        parser.error("a pipeline stage is required unless --list-stages is given")

    return _serve(args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
