# 03 — trace normalization

## Purpose

Render each **Agent training trace** into one gemma-native conversation string (the `text` field)
that SFT can train on directly.

## Inputs / outputs

- **In:** `training trace` JSONL (from 02) plus `mode`, `tool_name`, and optional structured
  `steps`.
- **Out:** `normalized text` JSONL — `TRACE_COLUMNS`
  (`row_id`, `prompt`, `trace`, `hop`, `tool_name`, `answer_format`, `gold`, `compacted`,
  `mode`) plus a `text` field ([00-overview.md](00-overview.md#normalized-text)).
  Over-length records are skipped and counted.
- **Persisted as:** `sft_texts.jsonl`.

## Requirement

The rendered assistant turn must use the base model's **native tool-call format** — literal
`<|tool_call>call:<name>{args}<tool_call|>` and `<|tool_response|>` blocks — matching what the
base model was pretrained to emit. A foreign (OpenAI-style JSON envelope) format is the known
failure mode that tripled held-out accuracy when fixed
(`docs/_archive/agent_handoff_2026-08-09.md` sections 3 and 5).

## Current status

`[unverified — needs unsloth gemma-4 processor]` for the full normalizer. The rendering
primitives it depends on pass their offline checks: `render_call_tokens`,
`render_tool_response`, and `render_trace_steps` are covered by passing tests in
`train_and_eval/eval/test_tool_calls.py` (`test_render_helpers`,
`test_run_code_roundtrip_in_trace_steps`).

## Verification

```bash
# rendering primitives (offline)
rtk uv run pytest train_and_eval/eval/test_tool_calls.py -k "render or run_code_roundtrip" -q

# full normalization (needs unsloth gemma-4 processor)
rtk uv run python train_and_eval/train/normalize_traces.py \
  --traces sft_traces_merged.jsonl --out sft_texts.jsonl
# prints: normalized N (skipped K); seq tokens p50/p90/max; over-6144; over-8192
```

The command actually run on 2026-10-07 for the primitives was
`python -m pytest train_and_eval/eval/test_tool_calls.py -q` (all passing, within the 36).

## Local decisions

### FT-03-D1 — Pre-render the conversation to a plain `text` column

- **Status:** accepted (2026-08).
- **Context:** the SFT script must train on a single text field; rendering at train time
  would couple training to a processor.
- **Decision:** `build_text` renders user + assistant messages through
  `processor.apply_chat_template(..., tools=tools, tokenize=False)` and writes the result as
  `text`. `sft_train.py` trains on that column directly.
- **Consequences:** the prompt/completion boundary is not marked, which is why SFT masking is
  unresolved (see [04-sft.md](04-sft.md#open-questions)).

### FT-03-D2 — Emit literal native tokens, bypass the template's tool-call path

- **Status:** accepted (2026-08).
- **Context:** gemma-4 has a legacy response schema; the assistant turn must retain literal
  `<|tool_call|>` / `<|tool_response|>` tokens rather than have the template re-encode them.
- **Decision:** `_assistant_content` builds the assistant content string from `steps` via
  `render_trace_steps`, then passes it as plain `content` with **no** `tool_calls` key, so the
  template's plain-text path keeps the tokens verbatim (`build_text`).
- **Consequences:** the normalizer depends on the render-tokens spelling staying in sync with
  the base tokenizer; the round-trip is covered by unit tests.

### FT-03-D3 — Always declare `run_code`, even for reasoning-only traces

- **Status:** accepted (2026-08).
- **Context:** traces that never call `run_code` still need to teach the student that the
  tool exists but may be skipped.
- **Decision:** the declared tool set is `{answer tools used} ∪ {run_code}`
  (`train_and_eval/train/normalize_traces.py::main`).
- **Consequences:** `run_code` is always in the system declaration; `compact_trace` is not
  (it is a teacher-only, non-answer tool).

## Open questions

- **Prompt masking.** Nothing in `normalize_traces.py` marks the user/system prefix as
  masked; the output is one flat `text` string. Whether SFT masks the prompt is unknown and
  is tracked as the SFT step's primary open question.
- **Sequence-budget policy.** `--max-len` defaults to 64000, but SFT trains at `SEQ=6144`;
  whether a normalized text above 6144 is ever intended is `[unknown]`.
- **Legacy block extraction.** `_args_from_trace` picks the last parseable JSON object; with
  interleaved `run_code` envelopes the "final" call may not be the answer call.
  `[unknown]` whether legacy (no `steps`) traces still occur.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- Emit an explicit `prompt_text` / `completion_text` split so masking is a data property, not
  a trainer option.
