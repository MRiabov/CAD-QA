"""02a extract CadQuery AST — program structure without geometry.

This module lands before its implementation so the worker dispatch, the typed
request boundary, and the failure partition are fixed first. See
``docs/dataset/implementation/pipeline/streamlined/02a-extract-cadquery-ast.md``.
"""

from __future__ import annotations

from typing import Any

from cadqa_dataset_generator import PipelineStageNotImplemented

PIPELINE_STAGE = "02a_extract_cadquery_ast"


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Extract the CadQuery program AST and write the AST extraction artifact."""

    # TODO(02a): read the pinned Python AST, apply the allowlist, and write
    # the typed AST extraction tables.
    del request
    raise PipelineStageNotImplemented(PIPELINE_STAGE)
