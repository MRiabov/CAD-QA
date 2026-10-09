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
  the unsloth repo. Superseded for Phase 3 by FT-D11. Detail: [pipeline/04-sft.md](pipeline/04-sft.md),
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

## FT-D11 — Start Phase 3 on the Liquid AI LFM2.5 stack

- **Status:** proposed (2026-10-08) — most likely, not yet accepted.
- **Context:** Phase 3 needs a base LLM model and a fine-tuning stack. The prior-art survey
  ([`../../prior-art.md`](../../prior-art.md)) records LFM2.5 and `Liquid4All/liquid-finetune`
  as the lowest-setup candidate: one first-party repo covers SFT/DPO/KTO/VLM/GRPO, QAT, GGUF
  export, and llama.cpp serving, and the models are small and advertised as fine-tunable on
  narrow tasks. The one known open concern is the data (the agent training trace set and prompt
  clarity), not the stack.
- **Decision:** start Phase 3 on Liquid AI LFM2.5 LLM models (LFM2.5-1.2B or -2.6B as first
  candidates) using the `liquid-finetune` stack, rather than assembling a pipeline around
  gemma-4-E2B (FT-D1) or another base LLM model.
- **Consequences:**
  - Fastest path to a first measured run; no toolchain assembly.
  - LFM2 is a non-transformer hybrid, so the current unsloth/gemma toolchain does not transfer.
  - **Lock-in / redo risk.** Adopting `liquid-finetune` and the LFM chat/tool-call format ties
    the training pipeline to Liquid. Testing another small LLM model later (Qwen3-4B,
    Llama-3.2-3B, Phi-4-mini, Gemma 4) means redoing the training from scratch **including the
    training code**: the trainer, data formatting, and tool-call rendering are stack-specific,
    so it is not a checkpoint swap. Mitigate by keeping the `Dataset file`, the prompt/answer
    contract, and the evaluation harness stack-neutral, and by recording a run manifest per
    result, so a base swap rewrites only the trainer behind those contracts; accept the re-run
    cost as small at these sizes.
  - Supersedes FT-D1 for Phase 3; FT-D1 remains the 2026-08 base.
  - **Addendum (2026-10-08).** `liquid-finetune` ships **GRPO as well as SFT**
    (`training_type: grpo`, TRL v1 `GRPOTrainer`, vLLM rollouts, a `rewards/` Python-callable
    registry, and an optional OpenEnv multiturn block), so the Phase 3 stack covers the whole
    post-training loop without a second RL framework. See
    `plans/oct-8/fine-tuning-system-plan.md`.
- Detail: [`../../prior-art.md`](../../prior-art.md) (LFM2.5 finding), research notes
  `../../research/2026-distil-labs-15-small-models-fine-tuning.md` and
  `../../research/2026-distil-labs-tool-calling-families.md`.

## FT-D12 — The Phase 3 rewrite retains only the loader and the typed tool contract

- **Status:** proposed (2026-10-08) — owner-stated direction; the exact boundary is not confirmed.
- **Context:** Phase 3 replaces the gemma-4 recipe (FT-D11). Most of `train_and_eval/` is
  stack-specific — the teacher client, rejection sampling, agent training trace normalization,
  SFT, GRPO, evaluation, and serving conversion — and is expected to be deleted rather than
  ported. Only the pieces that encode CAD-QA semantics independently of any trainer are worth
  carrying forward.
- **Decision:** Retain the **decoded CAD-QA dataset row loader**
  (`train_and_eval/rows_loader.py`, including the `[answer contract]` suffix) and the **typed
  tool and answer contract** (`train_and_eval/tool_calls.py`: `FORMAT_TO_TOOL`, the Pydantic
  argument models, `tool_call_matches`, and the `ToolName`/`HarnessMode` enums). Presume the
  rest of `train_and_eval/` is replaced by the Phase 3 data pipeline and the `liquid-finetune`
  stack.
- **Consequences:**
  - `tool_calls.py` is only **partly** retained: the typed definitions, the answer-format→tool
    mapping, and the matcher are stack-neutral; the gemma-native rendering and parsing helpers
    (`render_call_tokens`, `render_tool_response`, `render_trace_steps`, `extract_tool_call`)
    are base-specific and are re-authored for the new base LLM model's tokens (see the format
    churn recorded in `../../development-context.md`).
  - The stack-neutral contract in `plans/oct-8/fine-tuning-system-plan.md` §7 is exactly the
    retained surface; the rest of that pipeline is new code.
  - **Boundary (partly resolved).** `train_and_eval/grading/` is the **evaluation contract**
    (parse + exact-match + metrics + baselines) and is a keep candidate; it is not training code.
    It currently decides with `parse_answer` + `==` (`grading/grade.py::exact_match`) while the
    training/reward path uses `tool_call_matches`, so the two must be reconciled before any
    number is quoted (trust-audit **TA-A3**). Note `grading/parse.py` already handles the
    `boolean` Answer format, which the typed submit-tool contract does not — the grader is *more*
    complete than the contract there.
  - **Still unconfirmed.** `run_code_sandbox.py` plus `eval/`, and the CLI/orchestrator (`cli.py`,
    `experiment.py`, `harbor.py`), are not classified. The sandbox belongs to the `run_code` tool,
    so it likely stays; confirm before deletion.
  - Deletion is destructive and is done on a branch, with the audit as the justification.
    `dataset/` stays frozen (DD-01); `train_and_eval/` does not.
- Detail: FT-D11; `plans/oct-7/restructure-docs.md` (Code-change policy);
  `plans/oct-8/fine-tuning-system-plan.md`.

## FT-D13 — The post-training system is staged, not raw SFT-then-GRPO

- **Status:** proposed (2026-10-08) — research-backed; not yet accepted.
- **Context:** FT-D8 decided "teacher SFT, then GRPO", but the recorded GRPO hop-2 collapse
  (FT-D6) and the 2026 evidence (`../../prior-art.md` §"Building a proper SFT→RL system") show a
  raw second GRPO stage is expected to be weak or null: group-relative advantage is zero on
  tiers the SFT policy already clears or can never clear ([20]), SFT→RL can fail outright when
  training traces are too hard or rewards too sparse ([26]), and a dense reward term is hacked
  unless the shaping is optimality-preserving ([27]).
- **Decision:** replace the raw two-phase plan with the staged system in
  `plans/oct-8/fine-tuning-system-plan.md`: **Stage 0** one-scorer + off-oracle scorer audit →
  **Stage 1** difficulty-aligned SFT with a Bridge for hard training traces → **Stage 2** a
  pass@k sampling gate that also yields rejection-sampling SFT data → **Stage 3** GRPO with
  dynamic sampling only on reachable-but-unmastered tiers, sandboxed, with full rollout logging →
  optional **Stage 4** on-policy distillation. RL is **conditional on a measured learnable tier**,
  not a default.
- **Consequences:** the thesis may end at an SFT/RFT result if no tier is learnable; that is a
  recorded finding, not a failure (`../../PRD.md` definition of done, item 3). GRPO is cheap to
  attempt (FT-D11 addendum) but only after Stage 2 says it is indicated. Supersedes FT-D8's
  ordering. Detail: `plans/oct-8/fine-tuning-system-plan.md` §2–§3.

## FT-D14 — The scorer is the reward, and is audited before RL

- **Status:** proposed (2026-10-08).
- **Context:** in RLVR the scorer is the objective, not a metric. CAD-QA has **three** divergent
  scoring implementations (TA-A3), and scorer audits find self-agreement as low as 53.8% and
  two configurations of the same library disagreeing on 49.9% of pairs ([24]).
- **Decision:** the one-scorer reconciliation (TA-A3) and the off-oracle wrong-answer/formatting
  fixtures (TA-A2) are **P0 gates for any RL run**, single-sourced with evaluation, teacher
  rejection sampling, and reward. Numeric/coordinate Answer formats get an explicit
  metamorphic (equivalent-answer) test before a `1e-3` relative rule is trusted.
- **Consequences:** adds a hard dependency from any RL stage to the evaluation doc's P0 items;
  a dense reward term may only be added with optimality-preserving shaping ([27]). Detail:
  `plans/oct-8/fine-tuning-system-plan.md` §4; `plans/oct-8/evaluation-plan.md` §4.

## Open questions

- The base-pipeline choice (D11 in `plans/oct-7/restructure-docs.md`) is recorded as FT-D11,
  still proposed; promote it to accepted once the first Phase 3 canary runs.
- FT-D1, FT-D3, FT-D8 have unresolved sub-questions recorded in their step docs; a decision is
  not "done" while its consequences are unresolved.
