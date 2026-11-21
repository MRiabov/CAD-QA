"""Python worker for the CAD-QA dataset generator.

The Go entry point starts this package as a child process and passes it typed
Parquet paths and a small JSON request. One module lands per pipeline stage; see
``docs/dataset/implementation/file-trees.md``.
"""

from __future__ import annotations


class StageNotImplemented(RuntimeError):
    """Raised when a pipeline stage module exists but has no implementation yet."""

    def __init__(self, stage: str) -> None:
        super().__init__(f"pipeline stage {stage} is not implemented yet")
        self.stage = stage
