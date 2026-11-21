"""Typed contracts for the JSON documents exchanged with the Go orchestrator.

The Go orchestrator and the Python worker share no process memory. Bulk data
crosses the boundary as typed Parquet tables; the small control request and
response documents cross standard input and standard output as JSON. This module
is the Python executable form of those documents. The checked-in JSON Schema
files under ``contracts/worker/v1/`` are the language-neutral form, and the Go
structs are generated from them.

Each pipeline stage doc owns the meaning of each field. A contract change here
is a schema change: bump :data:`WORKER_PROTOCOL_VERSION` for a breaking change
and regenerate the schema and Go structs.
"""

from __future__ import annotations

from typing import Any, NamedTuple, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# The wire version of the request and response documents. It is independent of
# pipeline stage schema versions and of the generator version.
WORKER_PROTOCOL_VERSION = 1


class WorkerError(BaseModel):
    """A structured worker error returned as data."""

    model_config = ConfigDict(title="WorkerError", extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class WorkerResponse(BaseModel):
    """The one JSON document a worker writes to standard output.

    A response is either a success carrying ``result`` or a failure carrying
    ``error``. The validator keeps the two shapes from being mixed.
    """

    model_config = ConfigDict(title="WorkerResponse", extra="forbid")

    ok: bool
    protocol_version: int = Field(ge=1)
    result: dict[str, Any] | None = None
    error: WorkerError | None = None

    @model_validator(mode="after")
    def _check_outcome(self) -> Self:
        if self.ok:
            if self.result is None:
                raise ValueError("a successful worker response requires result")
            if self.error is not None:
                raise ValueError("a successful worker response cannot carry error")
        else:
            if self.error is None:
                raise ValueError("a failed worker response requires error")
            if self.result is not None:
                raise ValueError("a failed worker response cannot carry result")
        return self


class S01dNormalizeProgramsRequest(BaseModel):
    """The 01d request: which program pool parts to normalize and where to write."""

    model_config = ConfigDict(title="S01dNormalizeProgramsRequest", extra="forbid")

    program_pool_part_paths: list[str] = Field(min_length=1)
    output_directory: str = Field(min_length=1)
    shard_index: int = Field(ge=0)


class S01dNormalizeProgramsResult(BaseModel):
    """The 01d result: the written parts, their counts, and the normalization version."""

    model_config = ConfigDict(title="S01dNormalizeProgramsResult", extra="forbid")

    normalized_part_path: str = Field(min_length=1)
    failure_part_path: str = Field(min_length=1)
    normalized_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    normalization_version: str = Field(min_length=1)


class S01dNormalizeProgramsContract(BaseModel):
    """The 01d request and result pair, exported as one JSON Schema document."""

    model_config = ConfigDict(title="S01dNormalizeProgramsContract")

    request: S01dNormalizeProgramsRequest
    result: S01dNormalizeProgramsResult


class PipelineStageContract(NamedTuple):
    """The request and result models for one pipeline stage."""

    request: type[BaseModel]
    result: type[BaseModel]


# Only pipeline stages with a typed contract appear here. A pipeline stage
# without an entry keeps the bootstrap free-form dict path until its contract
# lands.
PIPELINE_STAGE_CONTRACTS: dict[str, PipelineStageContract] = {
    "01d_normalize_programs": PipelineStageContract(
        request=S01dNormalizeProgramsRequest,
        result=S01dNormalizeProgramsResult,
    ),
}

# The models exported to `contracts/worker/v1/`. The key is the file stem.
SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "envelope": WorkerResponse,
    "s01d_normalize_programs": S01dNormalizeProgramsContract,
}
