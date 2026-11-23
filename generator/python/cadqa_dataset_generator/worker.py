"""Worker entry point for the CAD-QA dataset generator.

The Go orchestrator starts one long-lived worker per pipeline stage:

    python -m cadqa_dataset_generator.worker <pipeline_stage>

The worker imports its pipeline stage module, calls its optional ``preload()``
hook, and writes one ready document to standard output:

    {"ok": true, "protocol_version": 1, "result": {"ready": true}}

It then serves newline-delimited JSON requests: one JSON request document per
line on standard input, one JSON response document per line on standard output:

    {"ok": true, "protocol_version": 1, "result": ...}
    {"ok": false, "protocol_version": 1, "error": {"code": "...", "message": "..."}}

A handled pipeline stage rejection is data, not a process exit. Exit code 0
means the worker reached EOF or was closed cleanly. Exit code 1 means the
worker could not start its pipeline stage. Logs go to standard error so
standard output stays one JSON document per line.

A pipeline stage with an entry in
:data:`cadqa_dataset_generator.contracts.PIPELINE_STAGE_CONTRACTS` validates its request
and result against the typed model before and after the runner.
A pipeline stage without a contract keeps the free-form dict path until its
contract lands.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from typing import Any

import orjson
from pydantic import ValidationError

from cadqa_dataset_generator import PipelineStageNotImplemented
from cadqa_dataset_generator.contracts import (
    PIPELINE_STAGE_CONTRACTS,
    WORKER_PROTOCOL_VERSION,
    WorkerError,
    WorkerResponse,
)

PipelineStageRunner = Callable[[Any], Any]

# TODO(bootstrap): remove the free-form fallback as each remaining
# pipeline stage gets an entry in PIPELINE_STAGE_CONTRACTS.

# Wire pipeline stage name -> module that implements it. The module name is `s` + name.
# The wire name is the snake-case pipeline stage name used by the failure record.
PIPELINE_STAGE_MODULES: dict[str, str] = {
    "01d_normalize_programs": "cadqa_dataset_generator.s01d_normalize_programs",
    "02a_extract_cadquery_ast": "cadqa_dataset_generator.s02a_extract_cadquery_ast",
    "02b_execute_cadquery": "cadqa_dataset_generator.s02b_execute_cadquery",
}


def pipeline_stage_names() -> list[str]:
    """Return the dispatchable stage names in stable order."""

    return sorted(PIPELINE_STAGE_MODULES)


def resolve_pipeline_stage(pipeline_stage: str) -> PipelineStageRunner:
    """Import the module for one pipeline stage and return its ``run`` function."""

    module_name = PIPELINE_STAGE_MODULES[pipeline_stage]
    module = importlib.import_module(module_name)
    runner = getattr(module, "run", None)
    if runner is None or not callable(runner):
        raise TypeError(f"stage module {module_name} has no callable run()")
    return runner


def preload_pipeline_stage(pipeline_stage: str) -> None:
    """Import a pipeline stage module and call its optional ``preload`` hook."""

    module = importlib.import_module(PIPELINE_STAGE_MODULES[pipeline_stage])
    preload = getattr(module, "preload", None)
    if callable(preload):
        preload()


def _failure(code: str, message: str) -> WorkerResponse:
    return WorkerResponse(
        ok=False,
        protocol_version=WORKER_PROTOCOL_VERSION,
        error=WorkerError(code=code, message=message),
    )


def _typed_request(pipeline_stage: str, request: dict[str, Any]) -> Any:
    """Validate a request when a pipeline stage has a contract, else pass it through."""

    contract = PIPELINE_STAGE_CONTRACTS.get(pipeline_stage)
    if contract is None:
        return request
    return contract.request.model_validate(request)


def _typed_result(pipeline_stage: str, result: Any) -> dict[str, Any]:
    """Validate a result when a pipeline stage has a contract, else require a JSON object."""

    contract = PIPELINE_STAGE_CONTRACTS.get(pipeline_stage)
    if contract is None:
        if not isinstance(result, dict):
            raise TypeError(
                f"pipeline stage {pipeline_stage} returned {type(result).__name__}, want dict"
            )
        return result
    typed = contract.result.model_validate(result)
    return typed.model_dump(mode="json")


def handle(
    pipeline_stage: str,
    request: dict[str, Any],
    runner: PipelineStageRunner | None = None,
) -> WorkerResponse:
    """Dispatch one request and convert pipeline stage failures to data."""

    if runner is None:
        try:
            runner = resolve_pipeline_stage(pipeline_stage)
        except KeyError:
            expected = ", ".join(pipeline_stage_names())
            return _failure(
                "unknown_stage",
                f"unknown stage {pipeline_stage!r}; expected one of {expected}",
            )
        except (ImportError, TypeError) as exc:
            return _failure("stage_unavailable", str(exc))

    try:
        typed_request = _typed_request(pipeline_stage, request)
    except ValidationError as exc:
        return _failure("invalid_request", str(exc))

    try:
        result = runner(typed_request)
    except PipelineStageNotImplemented as exc:
        return _failure("stage_not_implemented", str(exc))
    except Exception as exc:  # noqa: BLE001 - the worker boundary converts failures to data
        return _failure("stage_failed", f"{type(exc).__name__}: {exc}")

    try:
        typed_result = _typed_result(pipeline_stage, result)
    except (ValidationError, TypeError) as exc:
        return _failure("invalid_result", str(exc))

    return WorkerResponse(
        ok=True,
        protocol_version=WORKER_PROTOCOL_VERSION,
        result=typed_result,
    )


def _document(response: WorkerResponse) -> dict[str, Any]:
    """Return the wire document, omitting the outcome field that does not apply."""

    return response.model_dump(mode="json", exclude_none=True)


def _write_document(document: dict[str, Any]) -> None:
    payload = orjson.dumps(document, option=orjson.OPT_SORT_KEYS)
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()


def _serve(pipeline_stage: str) -> int:
    """Preload one pipeline stage, signal ready, and serve requests until EOF."""

    try:
        runner = resolve_pipeline_stage(pipeline_stage)
    except KeyError:
        expected = ", ".join(pipeline_stage_names())
        _write_document(
            _document(
                _failure(
                    "unknown_stage",
                    f"unknown stage {pipeline_stage!r}; expected one of {expected}",
                )
            )
        )
        return 1
    except (ImportError, TypeError) as exc:
        _write_document(_document(_failure("stage_unavailable", str(exc))))
        return 1

    try:
        preload_pipeline_stage(pipeline_stage)
    except Exception as exc:  # noqa: BLE001 - a preload failure is a pipeline stage failure
        _write_document(
            _document(
                _failure(
                    "stage_unavailable",
                    f"{type(exc).__name__}: {exc}",
                )
            )
        )
        return 1

    _write_document(
        _document(
            WorkerResponse(
                ok=True,
                protocol_version=WORKER_PROTOCOL_VERSION,
                result={"ready": True},
            )
        )
    )

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
            response = handle(pipeline_stage, request, runner)
        _write_document(_document(response))

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker command line."""

    parser = argparse.ArgumentParser(
        prog="cadqa_dataset_generator.worker",
        description="Run one CAD-QA dataset generator Python stage worker.",
    )
    parser.add_argument("pipeline_stage", nargs="?", help="pipeline stage to serve")
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="print the dispatchable stage names as JSON",
    )
    args = parser.parse_args(argv)

    if args.list_stages:
        _write_document(
            {
                "protocol_version": WORKER_PROTOCOL_VERSION,
                "stages": pipeline_stage_names(),
            }
        )
        return 0
    if args.pipeline_stage is None:
        parser.error("a pipeline stage is required unless --list-stages is given")

    return _serve(args.pipeline_stage)


if __name__ == "__main__":
    raise SystemExit(main())
