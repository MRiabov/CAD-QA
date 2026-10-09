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
  [pipeline/05-rl-readiness-gate.md](pipeline/05-rl-readiness-gate.md).

## FT-D2 — Teacher is DeepSeek v4.1 via OpenRouter

- **Status:** accepted (2026-08); teacher bumped to v4.1 (2026-10-09).
- **Context:** agent training traces are produced by a stronger LLM model.
- **Decision:** the teacher is `deepseek/deepseek-v4.1-flash` (pinned to the DeepSeek provider),
  called through OpenRouter; reasoning arrives in `message.reasoning`. It replaces the retired v4
  preview.
- **Consequences:** teacher cost and rate limits bound sampling; v4.1 is materially stronger, so the
  recorded ~23% success rate (v4 preview) no longer applies. Detail:
  [pipeline/02-teacher-sampling.md](pipeline/02-teacher-sampling.md).

## FT-D3 — Native gemma tool-call format, not an OpenAI JSON envelope

- **Status:** accepted (2026-08) — the pivotal decision.
- **Context:** the base LLM model is pretrained to emit
  `<|tool_call>call:<name>{args}<tool_call|>`; the first SFT taught a foreign JSON envelope
  and the base LLM model rambled and rarely emitted a parseable call.
- **Decision:** both agent training traces and the eval harness use the native format, including
  literal `<|tool_call|>` / `<|tool_response|>` tokens.
- **Consequences:** held-out accuracy went from 16.7% to 50% (12-row, non-native → native).
  Detail: [pipeline/03-preparation.md](pipeline/03-preparation.md),
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

## FT-D5 — Primary harness is `numpy`; `cadquery` is deferred to the RL Training stage

- **Status:** accepted (2026-08).
- **Context:** the PRD's primary setting has no access to CadQuery; a compute tool must
  not trivialize the task.
- **Decision:** the primary harness gives Python + NumPy (`run_code`); CadQuery execution is
  reserved for the RL Training stage and is not implemented yet; `no_tools` is the pure-reasoning
  bound.
- **Consequences:** `cadquery` mode is not implemented in the code. Detail:
  [pipeline/06-harness-modes.md](pipeline/06-harness-modes.md).

## FT-D6 — Reward is Query verifier-derived exact match

- **Status:** accepted (2026-08).
- **Context:** the reward must reproduce the Query verifier, not an LLM model's judgement; in the
  no-access-to-CadQuery setting the gold is a precomputed answer.
- **Decision:** GRPO scores completions against the decoded `gold_answer` using the per-format
  matcher, with a tool-call-aware path that reuses `tool_call_matches`.
- **Consequences:** the reward is sparse/binary, which is the recorded cause of the 2-hop
  collapse. Eval and reward use different parsers; see
  [pipeline/05-rl-readiness-gate.md](pipeline/05-rl-readiness-gate.md#open-questions).

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
  [pipeline/05-rl-readiness-gate.md](pipeline/05-rl-readiness-gate.md#open-questions).

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
  [pipeline/07-serving.md](pipeline/07-serving.md).

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
    `system.md`.
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
  - The stack-neutral contract in `system.md` §7 is exactly the
    retained part; the rest of that pipeline is new code.
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
    `dataset/` stays immutable (DD-01); `train_and_eval/` does not.
- Detail: FT-D11; `plans/oct-7/restructure-docs.md` (Code-change policy);
  `system.md`.

  **Update (2026-10-09).** The old `train_and_eval/` implementation is **deleted wholesale**; the loader
  and the typed tool/answer contract are carried as **shared interfaces, re-implemented** for the Phase 3
  stack — their 2026-08 defects (for example the optimistic split filter, the missing `boolean` submit
  tool) do **not** carry.

## FT-D13 — The post-training system is staged, not raw SFT-then-GRPO

- **Status:** proposed (2026-10-08) — research-backed; not yet accepted.
- **Context:** FT-D8 decided "teacher SFT, then GRPO", but the recorded GRPO hop-2 collapse
  (FT-D6) and the 2026 evidence (`../../prior-art.md` §"Building a proper SFT→RL system") show a
  raw second GRPO Training stage is expected to be weak or null: group-relative advantage is zero on
  tiers the SFT policy already clears or can never clear ([20]), SFT→RL can fail outright when
  training traces are too hard or rewards too sparse ([26]), and a dense reward term is hacked
  unless the shaping is optimality-preserving ([27]).
- **Decision:** replace the raw two-phase plan with the staged system in
  `system.md`: **Training stage 0** one-scorer + off-oracle scorer audit →
  **Training stage 1** difficulty-aligned SFT with a Bridge for hard training traces → **Training stage 2** a
  RL-readiness gate that also yields rejection-sampling SFT data → **Training stage 3** GRPO with
  dynamic sampling only on reachable-but-unmastered tiers, sandboxed, with full rollout logging →
  optional **Training stage 4** on-policy distillation. RL is **conditional on a measured learnable tier**,
  not a default.
- **Consequences:** the thesis may end at an SFT/RFT result if no tier is learnable; that is a
  recorded finding, not a failure (`../../PRD.md` definition of done, item 3). GRPO is cheap to
  attempt (FT-D11 addendum) but only after Training stage 2 says it is indicated. Supersedes FT-D8's
  ordering. Detail: `system.md` §2–§3.

## FT-D14 — The scorer is the reward, and is audited before RL

- **Status:** proposed (2026-10-08).
- **Context:** in RLVR the scorer is the objective, not a metric. CAD-QA has **three** divergent
  scoring implementations (TA-A3), and scorer audits find self-agreement as low as 53.8% and
  two configurations of the same library disagreeing on 49.9% of pairs ([24]).
- **Decision:** the one-scorer reconciliation (TA-A3) and the off-oracle wrong-answer/formatting
  fixtures (TA-A2) are **P0 gates for any RL run**, single-sourced with evaluation, teacher
  rejection sampling, and reward. Numeric/coordinate Answer formats get an explicit
  metamorphic (equivalent-answer) test before a `1e-3` relative rule is trusted.
- **Consequences:** adds a hard dependency from any RL Training stage to the evaluation doc's P0 items;
  a dense reward term may only be added with optimality-preserving shaping ([27]). Detail:
  `system.md` §4; `../evaluation/plan.md` §4.

## FT-D15 — The scaling lever is the environment, not the SFT corpus

- **Status:** proposed (2026-10-08) — research-backed; not yet accepted.
- **Context:** 2025–2026 evidence ([30]–[32]) shows agent capability scales with the **number and
  quality of verifiable environments** and RL over them, not with SFT volume; a fixed task set
  saturates, static data gives a vanishing signal when tasks are too easy or too hard, and SFT is a
  **warm-start readiness check** whose over-use ossifies the policy and collapses exploration.
- **Decision:** invest first in the **CAD-QA task environment + scorer** — a task generator over
  the immutable dataset rows (prompt + scalar gold, configurable hop/difficulty), the single verified
  exact-match scorer, and the `run_code`/kernel tool interface — and treat the external SFT mix
  (`emit_our_tool_call_format`, `run_the_tool_call_loop`, `preserve_general_math_and_code_reasoning`,
  `expose_general_python_code`, `expose_cadquery_programs`) as
  **support**: a thin format cold-start and general-task diversity.
  Teacher-distilled `learn_the_cadqa_task` traces are a cold-start at most, not the primary data.
- **Consequences:** effort shifts from corpus collection to **environment/scorer engineering**;
  the RL-readiness gate (FT-D13) is the switch from SFT to RL; external data stays bounded and
  selectively sourced (subset pulls); the CAD-QA task dataset becomes an environment (tasks +
  reward) as well as a dataset. Detail: `system.md` §0, §3;
  `../../prior-art.md` refs [30]–[32].

## FT-D16 — The training pipeline is two phases: elicit, then preserve

- **Status:** accepted (2026-10-09) — owner decision.
- **Context:** training had a single mixed SFT run with a staged option (FT-D13's Training stage 1);
  the intended shape is domain-then-task with an explicit objective shift.
- **Decision:** SFT runs as **phase 1 (refocus on coding)** — the base already trains on code, so
  coding/Python is not new, only unfocused; phase 1 also carries a simple slice of our tasks (e.g.
  hop 0) and a little text-to-CadQuery — then **phase 2 (CAD-QA task + preserve)** introducing CAD and
  `learn_the_cadqa_task` at scale, shifting from eliciting reasoning to preserving it. A
  **phase-2-only fallback** applies if phase 1 shows no measured phase-end gain.
- **Consequences:** sequential training carries higher forgetting risk (the 2026 controlled study
  found one SFT Training stage strongest); each phase must earn its place on the phase-end
  evaluation. Detail: `system.md` §2;
  `data.md` §4.

## FT-D17 — SFT data is verified, not just generated

- **Status:** accepted (2026-10-09).
- **Context:** the `expose_cadquery_programs` role listed `ricemonster/NeurIPS11092` (170k text→CadQuery
  pairs generated by Gemini 2.0 Flash, 2025) as an Adopt. Third-party *generated* corpora are not
  verification-filtered, so they teach the generating LLM model's errors; and Gemini 2.0 Flash is old,
  against the data doc's freshness policy.
- **Decision:** every SFT corpus is either **rejection-sampled by us** (teacher `deepseek-v4.1-flash`,
  FT-D2 — keep only traces the Query verifier accepts) or **execution-verified** before it enters a mix.
  Unverified third-party generation is P2/caution: execution-filter it or drop it. Prefer
  execution-verified sources (`BenchCAD` `code_gen`, isolated from the transfer evaluation) or our own
  corpus for `expose_cadquery_programs`.
- **Consequences:** `ricemonster/NeurIPS11092` is demoted from Adopt to P2/caution; verified teacher
  traces remain the safe signal. Detail: `data.md` §2.6, §7.

## FT-D18 — There is no dedicated replay role at SFT

- **Status:** accepted (2026-10-09) — owner decision.
- **Context:** `preserve_prior_capabilities` was the anti-forgetting role, but its concept is a replay
  buffer: at SFT there is no prior checkpoint (or prior rollouts) to replay from, so there is nothing to
  anchor to. Its candidate datasets were also thin (a base instruct mixture we do not have, a permissive
  substitute, or a slice of the evaluation set).
- **Decision:** drop `preserve_prior_capabilities` as a dataset role. Prior ability is anchored by the
  **diverse general-task mix** (general code + math + CAD; the majority of the first run and half the
  primary mix), not a dedicated replay role. A real replay buffer is a later RL/distillation concept,
  not an SFT role.
- **Consequences:** the training roles are six; the first-run mix becomes
  `mixed_dataset_general_and_easy_cadqa` (70% general tasks + 30% low-hop `learn_the_cadqa_task`,
  rejection-sampled). Detail: `data.md` §2.4, §3.

## FT-D19 — The general mix is three equal thirds; the primary drops emit; the H4 ablation is general-only

- **Status:** accepted (2026-10-09) — owner decision.
- **Context:** "70% general code/CAD tasks" was ill-defined, and `emit_our_tool_call_format` was listed
  for the second phase where the format is already carried by `learn_the_cadqa_task`.
- **Decision:** the general share is split into equal thirds — **coding agent**, **3D math**,
  **text2CAD + edits**. The first run is 70% general / 30% low-hop `learn_the_cadqa_task`; the primary
  is 50/50, with **no separate `emit_our_tool_call_format`** (the format comes with the task). The H4
  ablation is the **general-only** arm (the same mix without `learn_the_cadqa_task`).
- **Consequences:** the mix is defined by data category, not a single "general" blob; BenchCAD `code_gen`
  feeds the text2CAD third while BenchCAD `qa_code` is the H3 transfer target (keep them disjoint).
  Detail: `data.md` §3; `../evaluation/plan.md` §5.1.

## FT-D20 — Serving is a separate inference runtime

- **Status:** accepted (2026-10-09) — owner.
- **Context:** the "one tracked environment, or split SFT and serving" question conflated *packages* with
  *runtime*.
- **Decision:** serving is a **separate inference runtime** by design: it loads the **adapter or a merged
  LLM model** (weights only; FT-D23) and never the training optimizer / updating weights or gradients.
  Training and serving are split as processes regardless of packaging.
- **Consequences:** the remaining question is only packaging — whether one recipe (`liquid-finetune`)
  produces the served artifact or serving needs its own pins (GGUF/llama.cpp, vLLM). Detail:
  `pipeline/00-overview.md` Q2.

## FT-D21 — One GPU serving engine per rented window

- **Status:** accepted (2026-10-09) — owner direction.
- **Context:** evaluation and RL rollouts both need a serving engine, and the owner rents GPU by the
  hour. Running several engines at once fragments device memory and leaves the rented GPU idle.
- **Decision:** on a rented GPU, run **one** serving engine at a time — **vLLM** (native LFM2.5; the
  engine `liquid-finetune`/TRL already use for rollouts). Use **llama.cpp / GGUF on CPU** for
  local/edge, not on the rented box. Sequence a window as train → merge → serve → evaluate with the
  engine loaded once and reused; prepare data and configs ahead of time so nothing waits on the GPU; do not run
  training and serving concurrently on one 24 GB card. Prefer **Modal** (pay-per-second) for short
  jobs so no GPU sits idle.
- **Consequences:** two GPU engines at once only as a deliberate A/B (for example quantized vs bf16),
  and even then llama.cpp can run on CPU to avoid contending for the device. Detail:
  `pipeline/07-serving.md`.

## FT-D22 — No MTP/draft training; speculative decoding is serving-only

- **Status:** accepted (2026-10-09) — owner question, resolved.
- **Context:** LFM2.5 is next-token-prediction and has **no built-in MTP head**. Liquid ships a
  **separate** ~300M DSpark draft checkpoint
  (`LiquidAI/LFM2.5-{1.2B-Instruct,2.6B,8B-A1B}-DSpark`; safetensors + GGUF), day-one in llama.cpp and
  SGLang. `liquid-finetune`/LEAP is a TRL wrapper (SFT/DPO/GRPO + `evals:` + GGUF export) and has **no**
  speculator path.
- **Decision:** training **never** touches a draft/MTP head — no MTP training objective, no MTP heads to
  attach, no speculator to fit. Speculative decoding is an **optional, serving-only** latency
  optimization, not part of training, the merge, or any reported number. Default: no speculation (keep
  vLLM, FT-D21).
- **Consequences:**
  - Speculation is **lossless** (greedy output identical to the target; verified tokens preserve the
    sampling distribution), so it cannot change pass@k or exact-match and is irrelevant to H1–H4.
  - The shipped DSpark draft targets the **base** LLM model; after LoRA SFT + merge the target drifts and
    acceptance falls, so any speedup is re-measured post-SFT, not assumed.
  - DSpark runs for LFM2.5 on **SGLang** (PR #31041) and **llama.cpp** (GGUF/CPU); vLLM's `dspark` method
    exists but only for Qwen3/Qwen3-Omni, Gemma4, K3, and DeepSeek-V4 drafters — **not** the LFM drafter —
    so adopting it would move the serving runtime to SGLang. Adopt only if evaluation **or rollout** throughput measurably matters
    (rollouts are inference too — but see Q4: our RL default is vLLM).
  - Other classical-by-2026 optimizations are already in the recipe (LoRA-bf16, grad checkpointing +
    accumulation, packing, FlashAttention) or not applicable at 2.6B dense (MoE sharding); QLoRA stays a
    fallback (FT-D11). Detail: `pipeline/07-serving.md`, `training.md` §5.
  - The public fine-tuning stack (`liquid-finetune`/LEAP) has **no DSpark/speculator support**
    (checked 2026-10-09), so we could not train a drafter matched to our fine-tuned LLM model with it anyway.
- Detail: `../../research/2026-lfm2.5-dspark.md`.

## FT-D23 — Release the adapter; Transformers is the reference runtime

- **Status:** accepted (2026-10-09) — owner.
- **Context:** FT-D10/FT-D12 treat a merged checkpoint as the output and the thing to serve. Liquid's own
  docs disagree: LEAP Finetune exports Hugging Face **or GGUF**; its eval backends are HF Transformers
  (default, `sync`) and vLLM (`sidecar`/`reserved`); `liquid-export-gguf` takes a **PEFT adapter** directly;
  and vLLM serves LoRA adapters (`--enable-lora --lora-modules`, per-request `LoRARequest`) with no merge.
  Merge is only required for GGUF **K-quant** export ("merge the adapter into the base LLM model first, then
  export").
- **Decision:** the training output is the **LoRA adapter** (base + adapter), **not** a merged LLM model.
  **Evaluation runs on HF Transformers** — the same reference runtime Liquid uses — so the thesis number
  has **no serving-parity question**. **Merge/export is on demand** (standalone checkpoint, GGUF K-quant, a
  deployment that cannot take an adapter); vLLM serves the adapter directly.
- **Consequences:**
  - FT-D10's hand-conversion to vLLM is **obsolete for LFM2.5** (native `Lfm2ForCausalLM` ≥0.23, LoRA
    supported); it applied to gemma.
  - FT-D20's "loads the merged weights" is relaxed: a served engine may load base + adapter (still
    weights-only, no optimizer).
  - TA-C1 parity applies **only to numbers/rewards produced by a non-Transformers runtime** (vLLM); a
    Transformers number needs no parity check. Detail: `pipeline/07-serving.md`.

## Open questions

- **Q1.** The base-pipeline choice (D11 in `plans/oct-7/restructure-docs.md`) is recorded as FT-D11,
  still proposed; promote it to accepted once the first Phase 3 run completes.
- **Q2.** FT-D1, FT-D3, FT-D8 have unresolved sub-questions recorded in their step docs; a decision is
  not "done" while its consequences are unresolved.
- **Q3.** `data.md` §8 records two feature-wide decisions ("commercial agent training trace policy",
  "`preserve_general_math_and_code_reasoning` earns a place") with no FT-D label, because `data.md` is
  a design doc, not a step doc. Should they become FT-D entries here (the feature-wide decision home),
  or stay in `data.md`? `[open]`
- **Q4.** DSpark during **rollout-heavy** serving (the RL-readiness gate, GRPO). Rollouts are inference, so a
  lossless speculator would help the decode-bound rollout-count × prompts workload; but our RL default is
  `liquid-finetune` GRPO on **vLLM**, and DSpark for LFM2.5 is **SGLang/llama.cpp** (vLLM's `dspark` does
  not cover the LFM drafter), so it needs the **verl + SGLang** escalation (`../system.md` §6). The draft also targets the **base** and is never
  updated, so acceptance decays as the RL policy drifts. Resolve: does verl + SGLang + DSpark actually
  run our rollouts, and what is the acceptance/speedup on the SFT policy and over an RL run? `[open]`
