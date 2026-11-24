"""Contract tests for the JSON documents shared with the Go orchestrator.

The checked-in schemas are the language-neutral form of the Pydantic models.
These tests fail when a contract model changes without a matching schema export,
and they
pin the envelope invariant that a response carries either a result or an error.
"""

from __future__ import annotations

import json

import pytest
from cadqa_dataset_generator.contracts import (
    SCHEMA_MODELS,
    WORKER_PROTOCOL_VERSION,
    S01dNormalizeProgramsContract,
    S01dNormalizeProgramsRequest,
    S01dNormalizeProgramsResult,
    WorkerError,
    WorkerResponse,
)
from pydantic import ValidationError

from tools.contracts.export_worker_schemas import REPO, render_schema, schema_paths

REQUEST = {
    "program_pool_part_paths": ["runs/run0001/01c/pool-000.parquet"],
    "output_directory": "runs/run0001/01d",
    "shard_index": 0,
}
RESULT = {
    "normalized_part_path": "runs/run0001/01d/normalized-000.parquet",
    "failure_part_path": "runs/run0001/01d/failures-000.parquet",
    "normalized_count": 10,
    "failure_count": 1,
    "normalization_version": "01d-v1",
}


def test_exported_schemas_match_models() -> None:
    for stem, path in schema_paths().items():
        assert path.exists(), f"{path.relative_to(REPO)} is missing"
        assert path.read_text(encoding="utf-8") == render_schema(
            stem, SCHEMA_MODELS[stem]
        ), f"{path.relative_to(REPO)} is stale; run the exporter"


def test_exported_schemas_are_valid_json() -> None:
    for path in schema_paths().values():
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert document["$id"].endswith(path.name)


def test_protocol_version_is_positive() -> None:
    assert WORKER_PROTOCOL_VERSION >= 1


def test_worker_response_accepts_success() -> None:
    response = WorkerResponse(
        ok=True,
        protocol_version=WORKER_PROTOCOL_VERSION,
        result={"count": 1},
    )

    assert response.ok is True
    assert response.result == {"count": 1}
    assert response.error is None
    assert response.protocol_version == WORKER_PROTOCOL_VERSION


def test_worker_response_accepts_failure() -> None:
    response = WorkerResponse(
        ok=False,
        protocol_version=WORKER_PROTOCOL_VERSION,
        error=WorkerError(code="bad", message="no"),
    )

    assert response.ok is False
    assert response.result is None
    assert response.error is not None


@pytest.mark.parametrize(
    "document",
    [
        {"ok": True, "protocol_version": WORKER_PROTOCOL_VERSION},
        {"ok": False, "protocol_version": WORKER_PROTOCOL_VERSION},
        {
            "ok": True,
            "protocol_version": WORKER_PROTOCOL_VERSION,
            "result": {},
            "error": {"code": "bad", "message": "no"},
        },
        {
            "ok": False,
            "protocol_version": WORKER_PROTOCOL_VERSION,
            "result": {},
            "error": {"code": "bad", "message": "no"},
        },
    ],
)
def test_worker_response_requires_exactly_one_outcome(
    document: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        WorkerResponse.model_validate(document)


def test_s01d_contract_accepts_valid_documents() -> None:
    contract = S01dNormalizeProgramsContract(request=REQUEST, result=RESULT)

    assert contract.request.shard_index == 0
    assert contract.result.normalized_count == 10


def test_s01d_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        S01dNormalizeProgramsRequest.model_validate({**REQUEST, "extra": True})


def test_s01d_request_rejects_empty_parts() -> None:
    with pytest.raises(ValidationError):
        S01dNormalizeProgramsRequest.model_validate(
            {**REQUEST, "program_pool_part_paths": []}
        )


def test_s01d_result_rejects_negative_counts() -> None:
    document: dict[str, object] = {**RESULT, "normalized_count": -1}
    with pytest.raises(ValidationError):
        S01dNormalizeProgramsResult.model_validate(document)
