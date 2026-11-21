"""Worker entry point for the CAD-QA dataset generator.

The Go orchestrator starts ``python -m cadqa_dataset_generator.cli <pipeline_stage>``,
writes one JSON request document to standard input, and reads one JSON response
document from standard output:

    {"ok": true, "result": ...}
    {"ok": false, "error": {"code": "...", "message": "..."}}

Exit code 0 means the worker handled the request, including a pipeline stage rejection
returned as data. Exit code 1 means the request could not be handled. Logs go to
standard error so standard output stays one JSON document.
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
    """The one JSON document a worker writes to standard output."""

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


def handle(stage: str, request: dict[str, Any]) -> WorkerResponse:
    """Dispatch one request and convert stage failures to data."""

    try:
        runner = resolve_stage(stage)
    except KeyError:
        expected = ", ".join(stage_names())
        return WorkerResponse(
            ok=False,
            error=WorkerError(
                code="unknown_stage",
                message=f"unknown stage {stage!r}; expected one of {expected}",
            ),
        )
    except (ImportError, TypeError) as exc:
        return WorkerResponse(
            ok=False,
            error=WorkerError(code="stage_unavailable", message=str(exc)),
        )

    try:
        result = runner(request)
    except StageNotImplemented as exc:
        return WorkerResponse(
            ok=False,
            error=WorkerError(code="stage_not_implemented", message=str(exc)),
        )
    except Exception as exc:  # noqa: BLE001 - the worker boundary converts failures to data
        return WorkerResponse(
            ok=False,
            error=WorkerError(code="stage_failed", message=f"{type(exc).__name__}: {exc}"),
        )
    return WorkerResponse(ok=True, result=result)


def _read_request() -> dict[str, Any]:
    raw = sys.stdin.buffer.read()
    if not raw.strip():
        return {}
    parsed = orjson.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("worker request must be a JSON object")
    return parsed


def _write_response(response: WorkerResponse) -> None:
    payload = orjson.dumps(response.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS)
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker command line."""

    parser = argparse.ArgumentParser(
        prog="cadqa_dataset_generator.cli",
        description="Run one CAD-QA dataset generator Python stage.",
    )
    parser.add_argument("stage", nargs="?", help="pipeline stage to run")
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="print the dispatchable stage names as JSON",
    )
    args = parser.parse_args(argv)

    if args.list_stages:
        sys.stdout.buffer.write(orjson.dumps({"stages": stage_names()}) + b"\n")
        sys.stdout.buffer.flush()
        return 0
    if args.stage is None:
        parser.error("a pipeline stage is required unless --list-stages is given")

    try:
        request = _read_request()
    except (orjson.JSONDecodeError, ValueError) as exc:
        response = WorkerResponse(
            ok=False,
            error=WorkerError(code="invalid_request", message=str(exc)),
        )
    else:
        response = handle(args.stage, request)

    _write_response(response)
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
