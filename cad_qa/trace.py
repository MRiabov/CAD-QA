"""Trace record placeholders for graph-first CAD-QA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TraceRecord:
    source_id: str
    execution_status: str = "not_run"
    snapshots: list[dict[str, Any]] | None = None
    operation_effects: list[dict[str, Any]] | None = None
    environment: dict[str, Any] | None = None
    failure_reason: str | None = None
