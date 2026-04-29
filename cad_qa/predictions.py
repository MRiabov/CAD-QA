"""Prediction artifact normalization for CAD-QA evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_json, read_jsonl


ROW_ID_KEYS = ("row_id", "id", "custom_id")
PREDICTION_KEYS = (
    "prediction",
    "answer",
    "content",
    "output_text",
    "completion",
    "text",
)


def read_prediction_artifact(path: Path) -> dict[str, str]:
    """Read JSON or JSONL predictions into row_id -> answer text."""

    if path.suffix == ".jsonl":
        return normalize_prediction_records(read_jsonl(path))
    value = read_json(path)
    return normalize_prediction_artifact(value)


def normalize_prediction_artifact(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        if "predictions" in value:
            return normalize_prediction_artifact(value["predictions"])
        if _looks_like_prediction_mapping(value):
            return {
                str(key): _prediction_text(prediction)
                for key, prediction in value.items()
            }
        return normalize_prediction_records([value])
    if isinstance(value, list):
        return normalize_prediction_records(value)
    raise ValueError(
        "prediction artifact must be a JSON object, list, or JSONL object stream"
    )


def normalize_prediction_records(records: list[Any]) -> dict[str, str]:
    predictions: dict[str, str] = {}
    errors: list[str] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"record {index}: expected object")
            continue
        row_id = _row_id(record)
        if row_id is None:
            errors.append(f"record {index}: missing row_id/id/custom_id")
            continue
        predictions[row_id] = _prediction_text(record)
    if errors:
        raise ValueError("; ".join(errors))
    return predictions


def _looks_like_prediction_mapping(value: dict[str, Any]) -> bool:
    if not value:
        return True
    reserved = {
        "schema",
        "metadata",
        "model",
        "created_at",
        "request_count",
        "predictions",
    }
    if set(value) & reserved:
        return False
    return not any(key in value for key in ROW_ID_KEYS + PREDICTION_KEYS)


def _row_id(record: dict[str, Any]) -> str | None:
    for key in ROW_ID_KEYS:
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _prediction_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in PREDICTION_KEYS:
            if key in value:
                return _prediction_text(value[key])
        response_text = _provider_response_text(value)
        if response_text is not None:
            return response_text
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _provider_response_text(record: dict[str, Any]) -> str | None:
    response = record.get("response")
    if isinstance(response, dict):
        body = response.get("body")
        if isinstance(body, dict):
            text = _openai_body_text(body)
            if text is not None:
                return text
    return _openai_body_text(record)


def _openai_body_text(body: dict[str, Any]) -> str | None:
    output_text = body.get("output_text")
    if isinstance(output_text, str):
        return output_text
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]
    output = body.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and isinstance(
                        content_item.get("text"), str
                    ):
                        parts.append(content_item["text"])
        if parts:
            return "\n".join(parts)
    return None
