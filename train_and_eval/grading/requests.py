"""LLM model request export for the no-access-to-CadQuery setting."""

from __future__ import annotations

from typing import Any

from dataset.release.sft import public_answer_text


def zero_shot_requests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "request_id": f"request:{row['row_id']}",
            "row_id": row["row_id"],
            "messages": [
                {"role": "user", "content": row["prompt"]},
            ],
            "answer_format": row["answer_format"],
            "metadata": _request_metadata(row),
        }
        for row in rows
    ]


def few_shot_requests(
    eval_rows: list[dict[str, Any]],
    example_rows: list[dict[str, Any]],
    *,
    shots: int = 3,
) -> list[dict[str, Any]]:
    examples = example_rows[: max(0, shots)]
    prefix_messages: list[dict[str, str]] = []
    for example in examples:
        prefix_messages.extend(
            [
                {"role": "user", "content": example["prompt"]},
                {"role": "assistant", "content": public_answer_text(example)},
            ]
        )
    return [
        {
            "request_id": f"request:{row['row_id']}:fewshot_{len(examples)}",
            "row_id": row["row_id"],
            "messages": [*prefix_messages, {"role": "user", "content": row["prompt"]}],
            "answer_format": row["answer_format"],
            "metadata": {**_request_metadata(row), "shots": len(examples)},
        }
        for row in eval_rows
    ]


def oracle_responses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"row_id": row["row_id"], "answer": public_answer_text(row)} for row in rows]


def _request_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row["source_id"],
        "logical_hop_count": row["logical_hop_count"],
        "difficulty_bucket": row["difficulty_bucket"],
        "relation_families": row.get("relation_families", []),
        "measurement_scopes": row.get("measurement_scopes", []),
    }
