"""Load CAD-QA rows from local parquet/jsonl artifacts into RL/eval row dicts.

Bridges the graph-first dataset artifacts (`rows.parquet` / `rows.jsonl` from
`cadqa dataset materialize`) into the shape consumed by the tool-call harness:

- `eval_bench.py` (native tool-call eval loop)
- `grpo_train.py` (GRPO curriculum training)
- `export_rl_data.py` (RL data export)

The harness expects, per row: `row_id`, `prompt`, `answer_format`,
`gold_answer`, plus `logical_hop_count` for curriculum bucketing. The loader
decodes the JSON-encoded `gold_answer` and, when `tool_suffix=True`, appends
the `[answer contract]` suffix so the LLM model is instructed to end its response
with the matching `submit_*` tool call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from pydantic import BaseModel, Field

from tool_calls import tool_call_prompt_suffix


class RLRawRow(BaseModel):
    """Typed view of a CAD-QA dataset row as the RL/eval harness consumes it."""

    row_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    answer_format: str = Field(min_length=1)
    gold_answer: Any = None
    logical_hop_count: int | None = Field(default=None, ge=0)
    difficulty_bucket: str | None = Field(default=None, min_length=1)
    geometry_hop_count: int | None = Field(default=None, ge=0)
    relation_families: Any = None

    model_config = {"extra": "ignore"}


def _decode_gold(gold: Any) -> Any:
    """rows.parquet stores gold_answer JSON-encoded; decode it once."""
    if isinstance(gold, str):
        try:
            return json.loads(gold)
        except (json.JSONDecodeError, TypeError):
            return gold
    return gold


def load_local_rows(
    path: Path,
    *,
    split: str | None = "train",
    tool_suffix: bool = True,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    """Load harness-ready row dicts from a local rows.parquet or rows.jsonl.

    Args:
        path: parquet or jsonl artifact (rows.parquet / rows.jsonl).
        split: filter on the row `split` field; None loads every split.
        tool_suffix: append the per-format `[answer contract]` suffix to prompts.
        max_rows: cap on returned rows (useful for probes).
    """
    path = Path(path)
    records: list[dict[str, Any]]
    if path.suffix == ".parquet":
        table = pq.read_table(path)
        names = table.column_names
        records = [
            {name: table.column(name)[i].as_py() for name in names}
            for i in range(table.num_rows)
        ]
    else:
        with path.open(encoding="utf-8") as fh:
            records = [json.loads(line) for line in fh if line.strip()]

    rows: list[dict[str, Any]] = []
    for rec in records:
        if split is not None and rec.get("split") not in (None, split):
            continue
        if not rec.get("prompt") or rec.get("gold_answer") is None:
            continue
        if rec.get("release_ready") is False:
            continue
        fmt = str(rec.get("answer_format") or "text")
        prompt = str(rec["prompt"])
        if tool_suffix:
            prompt += tool_call_prompt_suffix(fmt)
        row = RLRawRow(
            row_id=str(rec["row_id"]),
            prompt=prompt,
            answer_format=fmt,
            gold_answer=_decode_gold(rec["gold_answer"]),
            logical_hop_count=rec.get("logical_hop_count"),
            difficulty_bucket=rec.get("difficulty_bucket"),
            geometry_hop_count=rec.get("geometry_hop_count"),
            relation_families=rec.get("relation_families"),
        )
        rows.append(row.model_dump())
        if max_rows is not None and len(rows) >= max_rows:
            break
    return rows
