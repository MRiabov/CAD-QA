"""Python worker for the CAD-QA dataset generator.

The Go entry point starts this package as a child process and passes it typed
Parquet paths and a small JSON request. One module lands per pipeline stage; see
``docs/dataset/implementation/file-trees.md``.
"""

from __future__ import annotations


class PipelineStageNotImplemented(RuntimeError):
    """Raised when a pipeline stage module exists but has no implementation yet."""

    def __init__(self, pipeline_stage: str) -> None:
        super().__init__(f"pipeline stage {pipeline_stage} is not implemented yet")
        self.pipeline_stage = pipeline_stage
