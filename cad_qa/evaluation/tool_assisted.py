"""Tool-assisted upper-bound evaluation artifacts."""

from __future__ import annotations

import json
from typing import Any

from cad_qa.evaluation.grade import grade_public_private


def tool_assisted_responses(
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit deterministic tool-assisted answers from private verifier artifacts."""

    private_by_id = {row["row_id"]: row for row in private_rows}
    responses: list[dict[str, Any]] = []
    for public in public_rows:
        private = private_by_id.get(public["row_id"])
        if private is None or private.get("verifier_status") != "resolved" or private.get("gold_answer") is None:
            continue
        query = private.get("query_program", {})
        trace = private.get("candidate_trace", {})
        responses.append(
            {
                "row_id": public["row_id"],
                "answer": _format_answer(private["gold_answer"], private.get("answer_format", public.get("answer_format", "entity_id"))),
                "confidence": 1.0,
                "tool": "private_graph_resolver",
                "provenance": {
                    "query_id": query.get("query_id"),
                    "verifier_status": private.get("verifier_status"),
                    "final_candidates": trace.get("final_candidates", []),
                    "clue_count": len(private.get("clue_map", [])),
                },
            }
        )
    return responses


def run_tool_assisted_upper_bound(
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    responses = tool_assisted_responses(public_rows, private_rows)
    metrics = grade_public_private(public_rows, private_rows, responses)
    response_ids = {response["row_id"] for response in responses}
    public_ids = {row["row_id"] for row in public_rows}
    return {
        "setting": "tool_assisted_upper_bound",
        "tool": "private_graph_resolver",
        "public_row_count": len(public_rows),
        "private_row_count": len(private_rows),
        "response_count": len(responses),
        "coverage": len(response_ids & public_ids) / len(public_ids) if public_ids else 0.0,
        "metrics": {key: value for key, value in metrics.items() if key != "graded"},
        "graded": metrics["graded"],
        "responses": responses,
    }


def _format_answer(answer: Any, answer_format: str) -> str:
    if answer_format in {"bbox", "json"}:
        return json.dumps(answer, sort_keys=True)
    if answer_format == "boolean":
        return "true" if bool(answer) else "false"
    return str(answer)
