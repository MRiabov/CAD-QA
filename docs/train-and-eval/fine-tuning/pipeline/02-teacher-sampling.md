# 02 — teacher sampling

## Purpose

Produce **agent training traces** by sampling a **teacher** LLM model on decoded CAD-QA dataset
rows and keeping only the attempts whose typed tool call the Query verifier accepts
(**rejection sampling**). Agent training trace length is bounded by **compaction**.

## Inputs / outputs

- **In:** `decoded CAD-QA dataset rows` (from 01) and, in the current sampler, directly HF config
  `v3_curriculum` (fields `row_id`, `prompt`, `gold_answer`, `answer_format`,
  `logical_hop_count`). An agent training trace's answer tool is derived from the row's
  `answer_format`.
- **Out `agent training traces`:** JSONL `Trace` records
  ([00-overview.md](00-overview.md#agent-training-traces)); any agent training trace longer
  than `MAX_TRACE_TOKENS` (`4000`) is compacted first.
- **Out `sampling log`:** JSONL `AttemptLog` records
  ([00-overview.md](00-overview.md#sampling-log)), one per teacher attempt, recording
  `text`, `reasoning`, `tool_call`, and per-tool-round `rounds` distinctly (the A5 rule).
- **Auxiliary export:** `train_and_eval/train/export_rl_data.py::main` writes RL
  `train.jsonl` / `heldout.jsonl` / `report.json` from a dataset file, excluding the bench
  slices (`runs/gemma_bench/slices/release10k/public.jsonl`,
  `runs/gemma_bench/slices/rc10/rows.jsonl`).
- **Auxiliary generation:** `train_and_eval/train/gen_1hop_queries.py` emits 1-hop query
  records with a CadQuery workplane aggregation and no Gold query predicate, for later
  materialization.
- **Publication:** `train_and_eval/setup/publish_traces.py::main` pushes an agent training trace
  pool to HF `MRiabov/cadqa-rl-2000` as a config (`sft_traces_v1`, `sft_traces_v2`).

## Requirement

A kept agent training trace must contain a tool call that `tool_call_matches` accepts against the
row's gold; a rejected attempt must never enter the pool. Success rate and per-format
coverage must be known and recorded, because a format the teacher never produces cannot be
learned by the student.

## Current status

`[unverified — needs OPENROUTER_API_KEY + network + HF access]`. Code is present;
`train_and_eval/teacher.py::build_teacher_prompt` is covered by a passing unit test, but no
end-to-end sampling run was performed in this audit. Historical runs are recorded in
`docs/_archive/rl_progress_2026-08-09.md` and `docs/_archive/agent_handoff_2026-08-09.md`, which
report an agent training trace pool of 275 → 308 and per-format success (`text` 23%,
`candidate_label` 42%, `coordinate` 23%, `integer` 35%, `bbox` 19%, `json` 0%, `number` 0%).

## Verification

```bash
# teacher client + prompt reuse
rtk uv run pytest train_and_eval/eval/test_tool_calls.py -k teacher -q

# end-to-end: a tiny targeted sample (needs OPENROUTER_API_KEY, HF network)
OPENROUTER_API_KEY=... rtk uv run python train_and_eval/train/rejection_sample.py \
  --attempts-per-row 1 --target-count 2 --only-rows /tmp/ids.txt \
  --out /tmp/traces.jsonl --log /tmp/sampling.jsonl
```

There is no offline test that asserts per-format teacher coverage. `[unknown]` whether a
coverage gate should exist.

## Local decisions

### FT-02-D1 — Rejection sampling with per-hop quotas

- **Status:** accepted (2026-08).
- **Context:** teacher success is low; traces are needed in hop-balanced quantity.
- **Decision:** `DEFAULT_QUOTAS` fixes per-hop targets `{0:50, 1:50, 2:50, 3:75, 5:50}`; the
  sampler cycles rows within a hop bucket, attempts each row up to `attempts_per_row`, and
  stops a bucket at quota (`train_and_eval/train/rejection_sample.py::Sampler`).
- **Consequences:** pool shape is controlled, but a hop with an intrinsically low yield
  (or absent rows) stalls its bucket. `--only-rows` + `--target-count` was added for
  targeted re-sampling (used for the 22 invalid center rows, per
  `docs/_archive/agent_handoff_2026-08-09.md` A2).

### FT-02-D2 — Multi-turn teacher loop with the `run_code` compute tool

- **Status:** accepted (2026-08).
- **Context:** exact numeric answers (CadQuery workplane frames, volumes) are not reliably
  computable in-head; the base LLM model is a code-execution variant.
- **Decision:** the teacher may emit `run_code` tool calls; the sampler executes them
  server-side and continues the conversation until a `submit_*` call
  (`train_and_eval/train/rejection_sample.py::Sampler._attempt_row`). The full round-trip is
  captured as structured `TraceStep`s (`text` / `tool_call` / `tool_result`), with a
  flattened text rendering alongside. `--no-compute-tool` runs reasoning-only.
- **Consequences:** traces can include literal `<|tool_response|>` blocks, which 03 must
  render. `compute_tool` also selects the agent training trace's `mode` (`NUMPY` vs `NO_TOOLS`).

### FT-02-D3 — Always compact a successful agent training trace

- **Status:** accepted (2026-08).
- **Context:** the teacher reasons freely and can exceed 4K tokens; the intent is a concise
  hop-step signal for the student.
- **Decision:** every successful attempt is passed through
  `compact_trace` (`train_and_eval/train/rejection_sample.py::compact_trace`); only the
  reasoning prose is compressed. Tool round-trips and the answer call are spliced back
  **verbatim**, so exact computed values are never re-derived. Traces that fail compaction
  fall back to the uncompacted form with `compacted=False`.
- **Consequences:** `Trace.steps` is emptied when compaction succeeds (the structured
  round-trip is folded into flattened text).

### FT-02-D4 — Agentic re-prompted compaction for over-long traces

- **Status:** accepted (2026-08).
- **Context:** some traces stayed over the cap after one-shot compaction.
- **Decision:** `train_and_eval/train/compact_agentic.py` compacts >4K-token traces to
  `[1000, 4096]` tokens, re-prompting the compactor with its previous output when the length
  is wrong, up to 4 iterations; a ≥1000-token floor rejects oracle-like summaries.
- **Consequences:** a length gate, not a correctness gate. Per `docs/_archive/agent_handoff_2026-08-09.md`,
  33 of 40 over-long traces compacted and 7 were dropped.

### FT-02-D5 — Record every LLM output distinctly (A5)

- **Status:** accepted (2026-08) — user standing instruction.
- **Context:** debugging and reproducibility require the reasoning phase, the visible
  output, and the tool call to be separable.
- **Decision:** `AttemptLog` carries `text`, `reasoning`, `tool_call`, and `rounds`
  (each a `RoundLog`); the sampler appends one `AttemptLog` per attempt to the sampling log.
- **Consequences:** any new rollout/compaction path must carry the same three fields.

## Open questions

- **Q1.** **`json` and `number` teacher coverage is zero.** Per
  `docs/_archive/agent_handoff_2026-08-09.md` A3, `json` was 0/113 and `number` 0/71. The sampler can
  emit traces in exactly one format per row, so the student cannot learn a format with no
  teacher success. This is the P0 defect this pipeline stage carries.
- **Q2.** **Teacher success is temperature-sensitive.** Default `temperature=1.0`
  (`train_and_eval/teacher.py::TeacherClient.__init__`) yields ~23% success; the handoff
  recommends 0.3–0.6. There is no default that encodes that recommendation. `[unknown]`
  whether the recommendation was adopted.
- **Q3.** **`compact_trace` is not a declared tool.** The compactor is prompted to emit a
  `compact_trace` JSON envelope (`_COMPACT_PROMPT`) without that tool being declared to the
  provider. `[unknown]` whether native tool-call enforcement was intended.
- **Q4.** **`_last_tool_call_block` uses a greedy `\{.*\}` regex**
  (`train_and_eval/train/rejection_sample.py::_last_tool_call_block`); with multiple JSON
  blocks it may splice more than the answer call. `[unknown]` impact.
- **Q5.** **Resume semantics.** The sampler opens the output in append mode and re-reads it as
  "existing traces" (`Sampler.__init__`); `[unknown]` whether duplicate `row_id`s across a
  resume are intended.
- **Q6.** **Box copies are stale.** `docs/_archive/agent_handoff_2026-08-09.md` states `/root/cadqa-bench/`
  must be synced from `train_and_eval/` before running; there is no sync script in the repo.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- Re-sample `json` and `number` with a format-targeted quota and a coverage gate in the
  sampler.
- A teacher-quality report written as a dated experiment record under `docs/experiments/`.
