# Development plan

**Status:** active, 2026-10-07. Based on the plan `plans/oct-7/restructure-docs.md`. This is the
project-level plan (what to build and in what order); the restructure plan is about how the
docs are organised. A live, owner-facing checklist lives in `_audit/owner-audit-todo.md`.

## Goal

Complete the project: an immutable, verified benchmark; refreshed baselines; a small LLM model that
beats its base and the baselines without collapsing reasoning (H2, P0); a measured transfer to
BenchCAD (H3, P1); and, as a P2 stretch, a tuned model that beats its teacher on the same harness.

## How work proceeds

- Phases run in order. Each has a pass condition; **no GPU budget is spent before the audit is
  green.**
- Every task carries a priority: **P0** thesis-critical, **P1** thesis-important, **P2**
  venue extras (may never execute).
- Every result names its environment pin, seed, dataset revision, and exact command.
- Every LLM model call records reasoning, output, and tool call distinctly.

## Phase 0 — Trust audit (no GPU) [P0]

Establish what the code actually does, so later numbers are trustworthy. The owner-facing
checklist is `_audit/owner-audit-todo.md` (group C); the program is `plans/oct-8/trust-audit.md`.

- Highest-risk items: the grader (`train_and_eval/grading/grade.py::grade_public_private`) versus
  the reward (`train_and_eval/...::reward_cadqa`); `run_code` sandbox isolation; vLLM versus
  transformers output parity; SFT prompt masking; the environment pins.
- Consolidate one runnable verification command per pipeline step (see
  `docs/dataset/requirements/PRD.md`, `train-and-eval/fine-tuning/requirements.md`).

**Pass condition:** every load-bearing component is `verified` or explicitly `blocked`.

## Phase 0a — Repo restructure (mechanical) [P1; fan-out P2]

**Done (2026-10-08).** `cad_qa/` is renamed to `dataset/` (generation only), and all
training/evaluation logic — `cad_qa/evaluation/` → `train_and_eval/grading/`, the eval CLI,
and the Harbor runner/grader — lives in `train_and_eval/`. The two packages are coupled only
by the rows IO contract. Folder fan-out CI is P2.

## Phase 0b — Prior-art code mining [P1]

Survey established open-source training/RL/data pipelines and pick a base to learn from or
build on. See `prior-art.md`. Pass condition: the base-pipeline decision is recorded (FT-D11) before
Phase 3 design.

## Phase 1 — Freeze the benchmark [P0]

- Freeze the dataset actually used for training (first run ~1–2k rows) with a group-safe held-out split.
  The regenerated ~10,000-row `benchmark-release` tier is a **contingency** for scale/public release, not
  a prerequisite for the first SFT; the 1,445-row release is superseded. (A public benchmark-release
  claim still follows the release requirements in `docs/dataset/requirements/PRD.md`.)
- Build and freeze the held-out test; assert no train/test row or CadQuery program overlap.
- Close the 0-hop/1-hop synthesis gap if needed; the working ladder is `{2,3,4,5}`, with generated
  6–10 tiers admissible only if the selection pilot supports them (evaluation plan §5.1).
- Fix `json`/`number` teacher coverage.
- Publish with tagged revision hashes.

**Pass condition:** immutable test set with group-safe splits; the `benchmark-release` report's failing
gates are recorded as known limitations.

## Phase 2 — Refresh baselines [P1; `no_tools`/`cadquery` P2]

Run cost-effective models on the primary `numpy` harness over the hard slice; log every
call; grade with the audited grader. Re-run or retire the stale shortcut baselines. See
`train-and-eval/evaluation/baselines.md`.

**Pass condition:** baseline tables reproducible; grader verified; outputs archived.

## Phase 3 — Reasoning-preserving fine-tuning [SFT P0; GRPO P1]

Design first (FT-D11 plus `train-and-eval/fine-tuning/pipeline/00-overview.md`):

- format via constrained decoding where possible;
- prompt-masked SFT, bounded epochs, if SFT is used;
- on-policy reasoning (student rejection sampling and/or GRPO) with shaped reward, release-hop
  `{2,3,4,5}` tier gating, entropy monitoring, and checkpoints.

Pilot on the lowest release tier (hop 2) before scaling. **Pass condition:** full held-out-test number;
improvement over base and baselines; H3 transfer reported.

## Phase 4 — Evaluation and analysis [core P0; `no_tools`/`cadquery` P2]

base / SFT / RL on the primary `numpy` harness, by hop and answer format; learning curve;
reasoning length; transfer to a second dataset; error taxonomy.

## Phase 5 — Write [thesis P0; venue-grade paper P2]

Fill the manuscript with real numbers, tables, and figures; verify citations; add the audit
as the thesis validation appendix.

## Phase 6 — Clean code [P2]

Rename code identifiers to match the glossary. `uv run python tools/check_dont_say.py
--identifiers` reports the name collisions, and `tools/dont_say_identifiers_baseline.txt`
holds the accepted count (**5,339** across 64 files — mostly `type`, `clause`, `source`,
`node`, `selector`) to ratchet to zero. Deferred: it is a large mechanical rename, much of it
inside the immutable `dataset/`.

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

None yet.
