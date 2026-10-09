# 01 — rows loader

## Purpose

Turn the **CAD-QA dataset file** (`rows.parquet`) into **decoded CAD-QA dataset rows** consumed by
teacher sampling, preparation, and evaluation.

## Inputs / outputs

- **In:** the **CAD-QA dataset file** — `rows.parquet` from `dataset_generation` (the immutable benchmark
  rows; see [00-overview.md](00-overview.md#datasets-in-play)). The External datasets and the Mixed
  training dataset enter later, at 03.
- **Out:** decoded CAD-QA dataset rows — `row_id`, `prompt`, `answer_format`, `gold_answer` (decoded),
  `reasoning_hop_count` (the `DatasetRow.logical_hop_count` column, under the glossary term),
  `geometry_hop_count`, `difficulty_bucket`, `relation_families`, `measurement_scopes`.
- **Filter semantics:** by `split`; rows missing `prompt` or `gold_answer`, and rows with
  `release_ready is False`, are dropped. The `[answer contract]` suffix is appended to each prompt.

## Requirement

Every retained row gets a prompt that names the correct **submit tool** for its `answer_format`, and a
`gold_answer` the shared matcher (`train_and_eval/tool_calls.py::tool_call_matches`) accepts for that
tool. If either is wrong, every downstream agent training trace and every evaluation score is wrong for
that row.

The loader exposes `reasoning_hop_count` (and `difficulty_bucket`) per row but does not filter or order
by it — the progressive curriculum is a mix concern, applied in the Sample + mix step (`../system.md`
§7).

## Current status

`missing` — the Phase 3 loader is to be written (re-implemented from the retained loader/tool contract;
FT-D12); the 2026-08 gemma stack is dropped.

## Verification

```bash
uv run pytest <loader test> -q
```

## Open questions

- **Q1.** Confirm every Answer format maps to a submit tool — the old typed contract omitted `boolean`.

## Resolved questions

- **Q2.** *(2026-10-09)* The decoded hop field is `reasoning_hop_count` (glossary) and reads the row
  column `logical_hop_count`; the Gold query program's unqualified `hop_count` stays internal to the
  dataset and is not exposed to the fine-tuning stages.
