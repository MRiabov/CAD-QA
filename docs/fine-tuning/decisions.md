# Fine-tuning — local decisions

Unit-level decisions for the fine-tuning pipeline, in ADR format. Step-scoped decisions live
in each [`pipeline/`](pipeline/00-overview.md) step file; this file holds only decisions that
span steps. Statuses reflect the code and the 2026-08 records; `[unknown]` marks a decision
whose rationale was not recoverable.

## FT-D1 — Base LLM model is gemma-4-E2B-it

- **Status:** accepted (2026-08).
- **Context:** the PRD targets a small (2–4B) open LLM model that can be trained and served on a
  single GPU.
- **Decision:** train `unsloth/gemma-4-E2B-it` (~2.3B active / ~5.1B total).
- **Consequences:** the base LLM model is a code-execution (E2B) variant, which motivated the
  `run_code` compute tool. The GRPO docstring names `google/gemma-4-E2B-it`; the code loads
  the unsloth repo. Detail: [pipeline/04-sft.md](pipeline/04-sft.md),
  [pipeline/05-grpo.md](pipeline/05-grpo.md).

## FT-D2 — Teacher is deepseek-v4-flash via OpenRouter

- **Status:** accepted (2026-08).
- **Context:** agent training traces are produced by a stronger LLM model.
- **Decision:** the teacher is `deepseek/deepseek-v4-flash` (pinned to the DeepSeek provider),
  called through OpenRouter; reasoning arrives in `message.reasoning`.
- **Consequences:** teacher cost and rate limits bound sampling. Detail:
  [pipeline/02-teacher-sampling.md](pipeline/02-teacher-sampling.md).

## FT-D3 — Native gemma tool-call format, not an OpenAI JSON envelope

- **Status:** accepted (2026-08) — the pivotal decision.
- **Context:** the base LLM model is pretrained to emit
  `<|tool_call>call:<name>{args}<tool_call|>`; the first SFT taught a foreign JSON envelope
  and the base LLM model rambled and rarely emitted a parseable call.
- **Decision:** both agent training traces and the eval harness use the native format, including
  literal `<|tool_call|>` / `<|tool_response|>` tokens.
- **Consequences:** held-out accuracy went from 16.7% to 50% (12-row, non-native → native).
  Detail: [pipeline/03-trace-normalization.md](pipeline/03-trace-normalization.md), <!-- dont-say: allow -->
  [pipeline/06-harness-modes.md](pipeline/06-harness-modes.md).

## FT-D4 — One typed submit tool per answer format

- **Status:** accepted (2026-08).
- **Context:** answers must be machine-checkable and comparable to the gold.
- **Decision:** the tool contract in `train_and_eval/tool_calls.py` maps each `answer_format`
  to one `submit_*` tool with Pydantic-typed arguments; comparison is exact for strings and
  integers and `1e-3` relative for floats. `json` is specifically the CadQuery workplane tool.
- **Consequences:** the contract is shared by teacher, SFT data, and eval. The `boolean`
  format is not in the typed contract (see [pipeline/06-harness-modes.md](pipeline/06-harness-modes.md#open-questions)).
  Detail: [pipeline/00-overview.md](pipeline/00-overview.md#shared-tool-call-contract).

## FT-D5 — Primary harness is `numpy`; `cadquery` is deferred to the RL stage

- **Status:** accepted (2026-08).
- **Context:** the PRD's primary setting is closed-book (no CAD kernel); a compute tool must
  not trivialize the task.
- **Decision:** the primary harness gives Python + NumPy (`run_code`); CadQuery execution is
  reserved for the RL stage and is not implemented yet; `no_tools` is the pure-reasoning
  bound.
- **Consequences:** `cadquery` mode is not implemented in the code. Detail:
  [pipeline/06-harness-modes.md](pipeline/06-harness-modes.md).

## FT-D6 — Reward is Query verifier-derived exact match

- **Status:** accepted (2026-08).
- **Context:** the reward must reproduce the Query verifier, not an LLM model's judgement; in the
  closed-book setting the gold is a precomputed answer.
- **Decision:** GRPO scores completions against the decoded `gold_answer` using the per-format
  matcher, with a tool-call-aware path that reuses `tool_call_matches`.
- **Consequences:** the reward is sparse/binary, which is the recorded cause of the 2-hop
  collapse. Eval and reward use different parsers; see
  [pipeline/05-grpo.md](pipeline/05-grpo.md#open-questions).

## FT-D7 — `run_code` is a numpy-only accidental-misuse guard

- **Status:** accepted (2026-08).
- **Context:** LLM model-generated code runs server-side in the training pipeline.
- **Decision:** the sandbox allows NumPy/math, blocks a fixed deny-list of imports, strips
  file-IO and code-execution builtins, and enforces a timeout; it is explicitly **not** a
  security boundary.
- **Consequences:** `run_code` must not face untrusted input. Detail:
  [pipeline/06-harness-modes.md](pipeline/06-harness-modes.md).

## FT-D8 — Two-phase training plan: teacher SFT, then GRPO

- **Status:** accepted (2026-08) as a plan; only partly implemented.
- **Context:** SFT provides format/capability; GRPO is intended to improve reasoning.
- **Decision:** post-train with SFT on teacher traces, then GRPO with the exact-match reward
  and a hop curriculum.
- **Consequences:** the current GRPO script starts from the base LLM model, not the SFT adapter,
  so the implemented chain is not the decided chain. Detail:
  [pipeline/05-grpo.md](pipeline/05-grpo.md#open-questions).

## FT-D9 — Record every LLM call distinctly (A5)

- **Status:** accepted (2026-08) — user standing instruction.
- **Context:** debugging and reproducibility require separating internal reasoning, visible
  output, and tool calls.
- **Decision:** every teacher/compaction call is recorded in the sampling log with `text`,
  `reasoning`, `tool_call`, and per-round records; eval rows record `tool_call` and `rounds`.
- **Consequences:** any new rollout/compaction path must follow the same rule. Detail:
  [pipeline/02-teacher-sampling.md](pipeline/02-teacher-sampling.md),
  [pipeline/06-harness-modes.md](pipeline/06-harness-modes.md).

## FT-D10 — Hand-convert the merged checkpoint for vLLM

- **Status:** accepted (2026-08).
- **Context:** vLLM's Gemma4 architecture rejects the unsloth-saved checkpoint (key layout +
  missing shared-layer `k_norm`).
- **Decision:** convert by renaming key prefixes and duplicating shared-layer `k_norm`, rather
  than waiting for upstream support.
- **Consequences:** conversion correctness is unverified (no parity test). Detail:
  [pipeline/07-serving-vllm.md](pipeline/07-serving-vllm.md).

## Open questions

- Which of these decisions should become repo-wide `docs/adr/` entries? The plan reserves
  `docs/adr/` for decisions that span both pipelines (for example the base-pipeline choice,
  D11, is still open in `plans/oct-7/restructure-docs.md`).
- FT-D1, FT-D3, FT-D8 have unresolved sub-questions recorded in their step docs; a decision is
  not "done" while its consequences are unresolved.
