"""01d normalize programs — canonical text and identity.

This module lands before its implementation so the worker dispatch, the typed
request boundary, and the failure partition are fixed first. See
``docs/dataset/implementation/pipeline/streamlined/01d-normalize-programs.md``.
"""

from __future__ import annotations

from typing import Any

from cadqa_dataset_generator import StageNotImplemented

STAGE = "01d_normalize_programs"


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Normalize selected programs and write the normalized program artifact."""

    # TODO(01d): decode UTF-8, parse with the pinned ast, unparse, format
    # with the pinned Ruff version, hash, and write the normalized program table.
    del request
    raise StageNotImplemented(STAGE)
