# Fine-tuning — requirements (intended vs verified)

**Status:** active, 2026-10-09. Rewritten to the Phase 3 design (`training.md`, `data.md`, `system.md`);
the 2026-08 gemma pipeline is superseded (FT-D11, FT-D12).

## How to read this

Each row states the **intended** requirement for a pipeline stage, whether it is **verified**, and the
evidence. The Phase 3 code is not written yet, so every pipeline stage is `missing` or
`[unverified — needs <env>]`; the retained loader/tool contract is carried forward as an interface and
re-implemented, not reused verbatim (FT-D12).

## Intended vs verified by pipeline stage

| Pipeline stage | Intended requirement | Verified? | Evidence |
|---|---|---|---|
| 01 rows-loader | A dataset file maps to decoded CAD-QA dataset rows with the correct `[answer contract]` and decoded gold for every format | No (`missing`) | Phase 3 loader to write (re-implemented from the retained loader/tool contract; FT-D12) |
| 02 teacher-sampling | Kept agent training traces carry a tool call the Query verifier accepts; coverage complete across the task space (Answer format × hop × relation family × measurement scope) | No | to be ported to the `deepseek-v4.1-flash` teacher (FT-D2) |
| 03 preparation | `TrainingExample` → Liquid `messages` SFT set; every SFT corpus is rejection-sampled by us or execution-verified (FT-D17) | No (`missing`) | converter to write (`system.md` §7) |
| 04 SFT | Two-phase SFT raises held-out accuracy over the base without over-generation | No | `liquid-finetune` recipe to run (FT-D16) |
| 05 RL-readiness gate | sampled `pass@1` + CI per **measured** tier recorded (not derived from `difficulty_bucket`/hop); RL only where a tier is learnable (FT-D13) | No (`missing`) | RL-readiness gate to build |
| 06 evaluation | Same grading across LLM harness modes; one scorer; evaluation datasets wired | Partial | local harness `exists` (the live grader; Harbor deferred P2, D-E9); one-scorer reconciliation pending (TA-A3, D-E8) |
| 07 serving | The training output is the LoRA adapter; evaluation runs on HF Transformers (the reference runtime) so there is no serving-parity check; merge/export is on demand | No | adapter-first + on-demand merge/export to build (FT-D23) |

## Cross-cutting requirements

| Requirement | Intended | Verified? | Evidence |
|---|---|---|---|
| Every LLM call records reasoning + output + tool call distinctly (A5) | Yes | By design, unrun | FT-D9 |
| No silent data loss (rejected rows, failed runs recorded) | Yes | Partial | sampling log + per-row results |
| Determinism (seeds, dataset revision, exact command) | Yes | No | run manifest pending (TA-E3) |
| The evaluator is the reward (one scorer) | Yes | No | three implementations (TA-A3) |
| No LLM model in the trusted grading path | Yes | By design, unrun | DD-03 |

## Environment

- **Python:** 3.12 (`uv.lock`); package manager `uv`.
- **GPU:** training and evaluation require CUDA. No live box exists at this commit.
- **Credentials:** `OPENROUTER_API_KEY` (teacher); HF access for the dataset artifacts.
- **Phase 3 stack:** LFM2.5 + `liquid-finetune` (FT-D11). The 2026-08 unsloth/gemma pins (`runs/`,
  untracked) are superseded and were never reproducible from tracked files.

## What "done" would require

1. An immutable dataset file with tagged revisions and a group-safe held-out split.
2. A `TrainingExample` → Liquid `messages` converter; a mix that is rejection-sampled or
   execution-verified (FT-D17).
3. The two-phase SFT measured against the base on the held-out slice.
4. The RL-readiness gate recorded; RL/RFT decided from it (FT-D13).
5. One scorer, agreed across evaluation and reward; a run manifest per reported number.

## Open questions

- **Q4.** Reconcile the `liquid-finetune` CUDA pin (`vllm==0.22.0`) with the serving need (LFM2.5
  native `Lfm2ForCausalLM` ≥0.23) — one tracked environment or two (`pipeline/07-serving.md` Q2;
  `../../../plans/oct-8/trust-audit.md` Q3). **Current state (2026-10-19):** upstream `main` still pins
  `vllm==0.22.0` (`pyproject.toml`/`uv.lock`); the LFM2.5 vLLM recipe states ≥0.23.0. SFT and evaluation
  use HF Transformers and are unaffected. The 0.22-vs-0.23 gap is **unverified, not proven broken** —
  LFM2.5 uses the same `Lfm2ForCausalLM` family, so 0.22 may load it even though 0.23 is the official
  recipe. Plan: smoke-test LFM2.5 on the pinned 0.22 for async eval/GRPO; if it fails, use a separate
  `vllm>=0.23` environment. Do not override the training pin blindly.

## Resolved questions

- **Q1.** *(2026-10-09)* **vLLM is the default GPU runtime** (native LFM2.5 from ≥0.23; the current
  `liquid-finetune` lock pins 0.22, so the 0.22 smoke test in Q4 gates async eval/GRPO; matches the
  LEAP/TRL rollouts); **SGLang** only if the DSpark speculator is adopted (FT-D22 Q4). Serving is a separate
  inference runtime that loads the **adapter** (base + adapter), not a merged LLM model, and never the
  optimizer (FT-D20, FT-D23); evaluation runs on **HF Transformers** (the reference runtime), so it
  needs no serving-parity check.
- **Q2.** *(2026-10-20)* **The Phase 3 code lives under `train_and_eval/pipeline/`.** Each pipeline stage
  is a module or package there named to mirror its step doc; a stage that exceeds the 800-line policy
  becomes a stage package (for example `train_and_eval/pipeline/01_rows_loader/`, matching
  `01-rows-loader.md`) rather than a new top-level package. The 1,200-line ceiling still applies.
  Numeric-prefixed folders are code-layout names; importable module names remain legal Python
  identifiers. The retained rows-loader and typed tool contract stay in `train_and_eval/` until
  re-implemented against the Phase 3 typed contract (FT-D12).
- **Q3.** *(2026-10-20)* **One append-only `run_manifest.json` per run, generated by
  `train_and_eval/pipeline/manifest.py`.** The manifest is a Pydantic `RunManifest` (version 1) with a
  `stages[]` list. Each pipeline stage appends its record — dataset/artifact references plus SHA-256,
  row counts, seeds, exact command, git SHA, and the resolved config; 03 adds the mix report, 04 the
  `liquid-finetune` revision and resolved training config, and 05/06 the eval cadence. The generator is
  runnable as `python -m train_and_eval.pipeline.manifest`. The pre-registered analysis block is frozen,
  hashed, and never rewritten by a later stage. The field list remains owned by `training.md` §4 step 7
  and `evaluation/plan.md` §5.2; this decision fixes the artifact shape, append-only rule, and generator
  entry point (TA-E3, determinism).
