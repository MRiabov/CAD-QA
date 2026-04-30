"""SFT export helpers for graph-first rows."""

from __future__ import annotations

from typing import Any


def answer_sft_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "messages": [
                {"role": "user", "content": row["prompt"]},
                {"role": "assistant", "content": str(row["gold_answer"])},
            ]
        }
        for row in rows
    ]


def reasoning_sft_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for row in rows:
        trace_lines = []
        for step in row.get("candidate_trace", {}).get("steps", []):
            after = step.get("after") or step.get("candidate_ids") or []
            trace_lines.append(f"{step.get('step')}: {len(after)} candidates")
        content = "\n".join([*trace_lines, f"answer: {row['gold_answer']}"])
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": content},
                ]
            }
        )
    return examples


def ablation_sft_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(f"hop_{row['logical_hop_count']}", []).append(row)
        groups.setdefault(f"difficulty_{row['difficulty_bucket']}", []).append(row)
    return {name: answer_sft_rows(group_rows) for name, group_rows in sorted(groups.items())}


def scaling_sft_groups(rows: list[dict[str, Any]], sizes: list[int]) -> dict[str, list[dict[str, str]]]:
    ordered = sorted(rows, key=lambda row: row["row_id"])
    return {
        f"size_{size}": answer_sft_rows(ordered[: min(size, len(ordered))])
        for size in sizes
    }
