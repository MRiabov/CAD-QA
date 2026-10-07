# Development plan

**Status:** active, 2026-10-07. Source: `plans/oct-7/restructure-docs.md`. This is the
project-level plan (what to build and in what order); the restructure plan is about how the
docs are organised. A live, owner-facing checklist lives in `_audit/owner-audit-todo.md`.

## Goal

Complete the project: a frozen, verified benchmark; refreshed baselines; a small model that
beats its base and the baselines without collapsing reasoning; results and a finished
paper/thesis.

## How work proceeds

- Phases run in order. Each has a gate; **no GPU budget is spent before the audit is
  green.**
- Every task carries a priority: **P0** thesis-critical, **P1** thesis-important, **P2**
  venue extras (may never execute).
- Every result names its environment pin, seed, dataset revision, and exact command.
- Every model call records reasoning, output, and tool call distinctly.

## Phase 0 — Trust audit (no GPU) [P0]

Establish what the code actually does, so later numbers are trustworthy. The owner-facing
checklist is `_audit/owner-audit-todo.md` (group C).

- Highest-risk items: the grader (`cad_qa/evaluation/grade.py::grade_public_private`) versus
  the reward (`fine_tuning/...::reward_cadqa`); `run_code` sandbox isolation; vLLM versus
  transformers output parity; SFT prompt masking; the environment pins.
- Consolidate one runnable verification command per pipeline step (see
  `dataset/requirements.md`, `fine-tuning/requirements.md`).

**Gate:** every load-bearing component is `verified` or explicitly `blocked`.

## Phase 0a — Repo restructure (mechanical) [P1; fan-out P2]

Split the code into `dataset_generation/` (today `cad_qa/`, frozen) and `fine_tuning/`
(today `train_and_eval/`), coupled only by the rows IO contract. Do this before the audit
settles citations. Folder fan-out CI is P2.

## Phase 0b — Prior-art code mining [P1]

Survey established open-source training/RL/data pipelines and pick a base to learn from or
build on. See `prior-art.md`. Gate: the base-pipeline decision (ADR) is recorded before
Phase 3 design.

## Phase 1 — Freeze the benchmark [P0; the ≥10k tier is P2]

- Decide dataset scope: freeze the 1,445-row curriculum plus a new group-safe held-out test,
  or regenerate the ≥10,000-row `benchmark-release` tier.
- Build and freeze the held-out test; assert no train/test row or source overlap.
- Close the 0-hop/1-hop synthesis gap if curriculum training needs it.
- Fix `json`/`number` teacher coverage.
- Publish with tagged revision hashes.

**Gate:** frozen test set with group-safe splits; the `benchmark-release` report's failing
gates are recorded as known limitations.

## Phase 2 — Refresh baselines [P1; `no_tools`/`cadquery` P2]

Run cost-effective models on the primary `numpy` harness over the hard slice; log every
call; grade with the audited grader. Re-run or retire the stale shortcut baselines. See
`evaluation/baselines.md`.

**Gate:** baseline tables reproducible; grader verified; outputs archived.

## Phase 3 — Reasoning-preserving fine-tuning [SFT P0; GRPO P1]

Design first (an ADR plus `fine-tuning/pipeline/00-overview.md`):

- format via constrained decoding where possible;
- prompt-masked SFT, bounded epochs, if SFT is used;
- on-policy reasoning (student rejection sampling and/or GRPO) with shaped reward, a
  `0→1→2→3→5` curriculum, entropy monitoring, and checkpoints.

Canary on 1-hop before scaling. **Gate:** full held-out-test number; improvement over base
and baselines; entropy and length reported, not collapsed.

## Phase 4 — Evaluation and analysis [core P0; `no_tools`/`cadquery` P2]

base / SFT / RL on the primary `numpy` harness, by hop and answer format; learning curve;
reasoning length; transfer to a second dataset; error taxonomy.

## Phase 5 — Write [thesis P0; venue-grade paper P2]

Fill the manuscript with real numbers, tables, and figures; verify citations; add the audit
as the thesis validation appendix.

## Cross-cutting rules

- **Reproducibility.** Move the environment pins out of the gitignored `runs/` into tracked
  files; emit a run manifest (env, seed, dataset revision, command, checksums) per result.
- **LLM logging.** Reasoning, output, and tool call recorded distinctly, everywhere.
- **No silent data loss.** Rejected rows and failed runs are recorded.
- **Monitoring.** GPU/API jobs checked every ~3–5 minutes; artifacts preserved before
  teardown.

## Open questions

See `_audit/owner-audit-todo.md`. This doc adopts decisions as they resolve.

## Resolved questions

_(none yet)_
