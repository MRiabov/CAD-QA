# 01 — rows loader

## Purpose

Turn a **dataset file** (`rows.parquet` / `rows.jsonl`) into **decoded CAD-QA dataset rows**
consumed by teacher sampling, GRPO, and evaluation.

## Inputs / outputs

- **In:** `dataset file` — `rows.parquet` or `rows.jsonl` from `dataset_generation`
  (fields in [00-overview.md](00-overview.md#dataset-file)).
- **Out:** `decoded CAD-QA dataset rows` (list of Python dicts; not persisted) — fields
  `row_id`, `prompt`, `answer_format`, `gold_answer` (decoded), `logical_hop_count`,
  `difficulty_bucket`, `geometry_hop_count`, `relation_families`
  ([00-overview.md](00-overview.md#decoded-cad-qa-dataset-rows)).
- **Filter semantics:** default `split="train"`; rows whose `split` is neither null nor the
  requested split are dropped; rows missing `prompt` or `gold_answer`, and rows with
  `release_ready is False`, are dropped. `[answer contract]` is appended to each prompt
  unless `tool_suffix=False`.

## Requirement

The loader must produce, for every retained row, a prompt that names the correct **submit
tool** for the row's `answer_format`, and a `gold_answer` that the shared matcher
(`train_and_eval/tool_calls.py::tool_call_matches`) accepts for that tool. If either is
wrong, every downstream agent training trace and every eval score is wrong for that row.

## Current status

`verified` — `train_and_eval/rows_loader.py::load_local_rows` exercised by its test suite
against the real `runs/current_cadevolve1000_10k_regen_20260613/release_10k/rows.parquet`
(10,000 rows; formats `candidate_label`/`coordinate`/`text`; hops `{2,3,4,5}`). 36/36 tests
passing across `train_and_eval/test_rows_loader.py` and
`train_and_eval/eval/test_tool_calls.py`.

## Verification

```bash
rtk uv run pytest train_and_eval/test_rows_loader.py -q
```

The full command actually run on 2026-10-07 was:

```bash
python -m pytest train_and_eval/test_rows_loader.py train_and_eval/eval/test_tool_calls.py -q
# 36 passed
```

`jsonl`-only paths are covered by synthetic fixtures in the same test file; the
`release_10k` fixture skips itself if the artifact is absent, so an artifact-less checkout
still verifies the loader logic but not the real schema.

## Local decisions

### FT-01-D1 — Append the `[answer contract]` suffix at load time

- **Status:** accepted (2026-08).
- **Context:** the model must end with a `submit_*` tool call; both the teacher and the
  student need the same instruction.
- **Decision:** `load_local_rows` appends `tool_call_prompt_suffix(answer_format)` to the
  prompt by default, so every consumer gets the contract without re-implementing it.
- **Consequences:** the teacher prompt and the SFT/eval prompt share one suffix source
  (`train_and_eval/tool_calls.py::tool_call_prompt_suffix`). `tool_suffix=False` exists for
  callers that want the bare prompt.

### FT-01-D2 — Decode the JSON-encoded gold once, in the loader

- **Status:** accepted (2026-08).
- **Context:** `rows.parquet` stores `gold_answer` as a JSON string (e.g. `"wp19"` for text,
  `[-1.5, 0, 2.25]` for coordinate).
- **Decision:** `_decode_gold` decodes a string gold once; downstream compares the decoded
  value. `reward_cadqa._decode_gold` independently double-decodes because HF rows can be
  double-encoded.
- **Consequences:** two decoders exist for the same concept. If the encodings diverge, the
  loader and the reward can disagree.

## Open questions

- **Split filtering is optimistic.** A row with `split=None` passes every split filter
  (`rec.get("split") not in (None, split)`). `[unknown]` whether any artifact row has a null
  split; if so, held-out leakage is possible.
- **`boolean` answer format is unhandled.** `train_and_eval/rows_loader.py::RLRawRow` and
  `train_and_eval/tool_calls.py::tool_call_prompt_suffix` route through
  `format_to_tool`, which has no `boolean` entry; the glossary lists `boolean` as an answer
  format. A `boolean` row would raise at load or eval time. See
  [06-harness-modes.md](06-harness-modes.md#open-questions).

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- Emit a typed `HarnessRow` Pydantic model instead of a bare `dict` (the repo's typed-code
  standard prefers explicit models between functions).
