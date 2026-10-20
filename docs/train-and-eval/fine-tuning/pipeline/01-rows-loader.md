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
  `geometry_hop_count`, `difficulty_bucket`, `relation_families`, `measurement_scopes`, `split`, and
  `pool` (`sft_train` / `rl_train` / `eval`, joined from `split_manifest.json`; `../data.md` §5).
- **Filter semantics:** by `split`; rows missing `prompt` or `gold_answer`, and rows with
  `release_ready is False`, are dropped. The `[answer contract]` suffix is appended to each prompt. The
  loader exposes all three pools; it does **not** drop `rl_train` or `eval` — downstream stages select
  `sft_train` for SFT and `rl_train` for the gate.

## Requirement

Every retained row gets a prompt that names the correct **submit tool** for its `answer_format`, and a
`gold_answer` the shared matcher (`train_and_eval/tool_calls.py::tool_call_matches`) accepts for that
tool. If either is wrong, every downstream agent training trace and every evaluation score is wrong for
that row.

The Phase 3 typed contract is defined over the **full** `answer_format` enum the dataset emits — the
union of the 2026-08 `tool_calls.py::FORMAT_TO_TOOL` and `grading/parse.py::parse_answer`, explicitly
adding the formats the old contract omitted (`boolean`, `entity_id`) — so every retained row maps to
exactly one `submit_*` tool by construction (FT-D4, FT-D12; D-E8).

The loader exposes `reasoning_hop_count` (and `difficulty_bucket`) per row but does not filter or order
by it — tier inclusion is a mix/training-phase concern, applied through the measured advancement gate
(`../data.md` §4.1), not by ordering a static dataset.

## Current status

`missing` — the Phase 3 loader is to be written (re-implemented from the retained loader/tool contract;
FT-D12); the 2026-08 gemma stack is dropped.

## Verification

```bash
uv run pytest <loader test> -q
```

## Open questions

None.

## Resolved questions

- **Q1.** *(2026-10-09)* A **scope** decision, not an open verification: Phase 3 rewrites the contract
  (FT-D12), so it is defined over the full `answer_format` enum the dataset emits — including the
  `boolean` and `entity_id` formats the 2026-08 typed contract omitted — and every Answer format maps to
  a submit tool (FT-D4; D-E8, the one-scorer target).
- **Q2.** *(2026-10-09)* The decoded hop field is `reasoning_hop_count` (glossary) and reads the row
  column `logical_hop_count`; the Gold query program's unqualified `hop_count` stays internal to the
  dataset and is not exposed to the fine-tuning stages.
