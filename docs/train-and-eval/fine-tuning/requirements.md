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
| 05 RL-readiness gate | pass@k per Difficulty tier recorded; RL only where a tier is learnable (FT-D13) | No (`missing`) | RL-readiness gate to build |
| 06 evaluation | Same grading across LLM harness modes; one scorer; evaluation datasets wired | Partial | local harness `exists`; three scorers diverge (TA-A3) |
| 07 serving | Served checkpoint numerically equivalent to the merged LLM model | No | merge/export + parity to build (FT-D10) |

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

- **Q1.** Serving is a separate **inference runtime** by design (merged weights only, no optimizer;
  FT-D20). Liquid documents the runtimes (`docs.liquid.ai/deployment/*`); pick vLLM vs SGLang for our
  batched evaluation/rollouts (`../../../plans/oct-8/trust-audit.md` Q3).
- **Q2.** Where do the retained rows-loader and the new converter live once `train_and_eval/` is
  rewritten (FT-D12)?
- **Q3.** Run-manifest format and generator (TA-E3).

## Resolved questions

_(none yet)_
