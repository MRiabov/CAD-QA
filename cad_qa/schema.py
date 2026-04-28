"""Dataclass records and lightweight schema validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import math
import re
from typing import Any


TASK_TYPES = {
    "operation_count",
    "selector_count",
    "bbox_after_step",
    "signed_volume_delta",
    "topology_count_after_step",
    "point_membership",
    "feature_provenance_choice",
    "workplane_state",
    "coordinate_frame",
    "counterfactual_parameter",
    "ambiguous_question_detection",
}

ANSWER_TYPES = {
    "integer",
    "number",
    "bbox",
    "choice",
    "enum",
    "coordinate",
    "json",
    "invalid_or_ambiguous",
}

SPLITS = {
    "train",
    "validation",
    "test_random",
    "test_generator_heldout",
    "test_source_subtree_heldout",
    "test_operation_heldout",
    "test_topology_heldout",
    "test_near_boundary",
}

POINT_CLASSIFICATIONS = {"inside", "outside", "on_boundary", "ambiguous"}
PROVENANCE_RELATIONS = {
    "created_by",
    "modified_by",
    "deleted_by",
    "inherited_from",
    "bounded_by",
    "ambiguous_or_merged",
}

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source: str
    archive_member_path: str | None
    normalized_archive_member_path: str | None
    source_subtree: str | None
    generator_id: str | None
    license: str | None
    raw_code: str
    normalized_code: str
    hashes: dict[str, Any]


@dataclass(frozen=True)
class OperationNode:
    feature_id: str
    step_index: int
    source_line: int | None
    target: str | None
    base: str | None
    operation: str
    args_repr: list[str]
    input_features: list[str]
    status: str = "ok"


@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    source_id: str
    operation_graph_status: str
    execution_status: str
    result_variable: str | None
    operation_nodes: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    label_policy: dict[str, Any]
    environment: dict[str, Any]
    hashes: dict[str, Any]
    failure_reason: str | None = None
    selector_tables: list[dict[str, Any]] = field(default_factory=list)
    point_queries: list[dict[str, Any]] = field(default_factory=list)
    provenance_records: list[dict[str, Any]] = field(default_factory=list)
    topology_matches: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PublicTaskRow:
    id: str
    dataset_version: str
    task_type: str
    source_id: str
    trace_id: str
    target_feature_id: str | None
    split: str
    prompt: str
    answer_type: str
    answer: Any
    choices: list[str] | None
    unit: str | None
    numeric_tolerance: float | None
    requires: list[str]
    difficulty_tags: list[str]
    labels: dict[str, Any]
    diagnostics: dict[str, Any]
    provenance: dict[str, Any]
    hashes: dict[str, Any]
    parse_policy: str


def to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    raise TypeError(f"cannot convert {type(value)!r} to dict")


def validate_source_record(record: dict[str, Any]) -> list[str]:
    errors = _require_keys(
        record,
        {
            "source_id",
            "source",
            "archive_member_path",
            "normalized_archive_member_path",
            "source_subtree",
            "generator_id",
            "license",
            "raw_code",
            "normalized_code",
            "hashes",
        },
    )
    if record.get("source") not in {"cadevolve", "synthetic"}:
        errors.append("source must be 'cadevolve' or 'synthetic'")
    errors.extend(_validate_hashes(record.get("hashes", {})))
    return errors


def validate_trace_record(record: dict[str, Any]) -> list[str]:
    errors = _require_keys(
        record,
        {
            "trace_id",
            "source_id",
            "operation_graph_status",
            "execution_status",
            "result_variable",
            "operation_nodes",
            "snapshots",
            "label_policy",
            "environment",
            "hashes",
            "failure_reason",
        },
    )
    if not isinstance(record.get("operation_nodes"), list):
        errors.append("operation_nodes must be a list")
    if not isinstance(record.get("snapshots"), list):
        errors.append("snapshots must be a list")
    errors.extend(_validate_hashes(record.get("hashes", {})))
    return errors


def validate_public_row(row: dict[str, Any]) -> list[str]:
    errors = _require_keys(
        row,
        {
            "id",
            "dataset_version",
            "task_type",
            "source_id",
            "trace_id",
            "target_feature_id",
            "split",
            "prompt",
            "answer_type",
            "answer",
            "choices",
            "unit",
            "numeric_tolerance",
            "requires",
            "difficulty_tags",
            "labels",
            "diagnostics",
            "provenance",
            "hashes",
            "parse_policy",
        },
    )
    if row.get("task_type") not in TASK_TYPES:
        errors.append(f"invalid task_type: {row.get('task_type')!r}")
    if row.get("answer_type") not in ANSWER_TYPES:
        errors.append(f"invalid answer_type: {row.get('answer_type')!r}")
    if row.get("split") not in SPLITS:
        errors.append(f"invalid split: {row.get('split')!r}")
    if not isinstance(row.get("prompt"), str) or not row.get("prompt", "").strip():
        errors.append("prompt must be non-empty")
    _validate_answer(row, errors)
    if not isinstance(row.get("requires"), list):
        errors.append("requires must be a list")
    if not isinstance(row.get("difficulty_tags"), list):
        errors.append("difficulty_tags must be a list")
    errors.extend(_validate_hashes(row.get("hashes", {})))
    provenance = row.get("provenance")
    if isinstance(provenance, dict):
        for key in ("local_path", "cache_path", "source_root"):
            if key in provenance:
                errors.append(f"public provenance leaks local path key: {key}")
    else:
        errors.append("provenance must be an object")
    return errors


def _validate_answer(row: dict[str, Any], errors: list[str]) -> None:
    answer_type = row.get("answer_type")
    answer = row.get("answer")
    task_type = row.get("task_type")
    if answer_type == "integer" and (not isinstance(answer, int) or answer < 0):
        errors.append("integer answers must be non-negative integers")
    if answer_type == "number" and not _finite_number(answer):
        errors.append("number answers must be finite")
    if answer_type == "bbox" and not _valid_bbox(answer):
        errors.append("bbox answers must contain finite min/max arrays of length 3")
    if answer_type in {"choice", "enum"}:
        choices = row.get("choices")
        if not isinstance(answer, str):
            errors.append("choice/enum answer must be a string")
        if choices is not None and answer not in choices:
            errors.append("choice answer is not listed in choices")
    if task_type == "point_membership" and answer not in POINT_CLASSIFICATIONS:
        errors.append("point_membership answer must be a point classification")
    if task_type == "feature_provenance_choice" and answer != "ambiguous_or_merged":
        choices = row.get("choices")
        if not isinstance(choices, list) or answer not in choices:
            errors.append("feature_provenance_choice answer must be in choices or ambiguous_or_merged")


def _valid_bbox(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return _finite_triplet(value.get("min")) and _finite_triplet(value.get("max"))


def _finite_triplet(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(_finite_number(item) for item in value)
    )


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _require_keys(record: dict[str, Any], keys: set[str]) -> list[str]:
    return [f"missing required key: {key}" for key in sorted(keys - set(record))]


def _validate_hashes(hashes: Any) -> list[str]:
    if not isinstance(hashes, dict):
        return ["hashes must be an object"]
    errors: list[str] = []
    for key, value in hashes.items():
        if key.endswith("_hash") or key == "prompt_hash":
            if not isinstance(value, str) or not HASH_RE.match(value):
                errors.append(f"invalid hash for {key}")
    return errors
