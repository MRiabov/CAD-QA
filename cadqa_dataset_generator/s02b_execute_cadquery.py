"""02b execute CadQuery — runtime captures or a failure tombstone.

This module lands before its implementation so the worker dispatch, the typed
request boundary, and the failure partition are fixed first. See
``docs/dataset/implementation/pipeline/streamlined/02b-execute-cadquery.md``.
"""

from __future__ import annotations

from typing import Any

from cadqa_dataset_generator import StageNotImplemented

STAGE = "02b_execute_cadquery"


def preload() -> None:
    """Import CadQuery and OCP once per worker before the first request."""

    import cadquery  # noqa: F401
    import OCP  # noqa: F401


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Execute one normalized program and write runtime captures or a tombstone."""

    # TODO(02b): run the program in the child process, capture runtime
    # entities and probes, and write captures or a failure tombstone.
    del request
    raise StageNotImplemented(STAGE)
