# CAD-QA documentation

**Status:** being restructured (2026-10-07). The conventions below are the target model;
the existing docs (`implementation_status.md`, handoffs, runbooks, this directory's older
files) are being migrated or retired. See `plans/oct-7/restructure-docs.md` for the plan and
`development-context.md` for the current state.

This directory is the canonical documentation for CAD-QA: a benchmark for reasoning over
procedural CAD programs (CadQuery), and a small-model fine-tuning effort on top of it.

## Reading order

1. **`docs-conventions.md`** — how docs are structured and written. Read first.
2. **`PRD.md`** — what the project is for: questions, claims, deliverables, evaluation.
3. **`glossary.md`** — the canonical vocabulary. If a term is unclear anywhere else, it is
   defined here.
4. **`development-context.md`** — where the project actually is today, and its history.
5. **`development-plan.md`** — the phased route to completion.
6. **`prior-art.md`** — mined open-source training/RL/data pipelines.
7. **`dataset/`** — the benchmark-generation pipeline, step by step.
8. **`fine-tuning/`** — the training and evaluation pipeline.
9. **`evaluation/`** — harnesses and baselines.

## Canonical references

| What you need | Where |
|---|---|
| How to write a doc | `docs-conventions.md` |
| Why the project exists | `PRD.md` |
| What a term means | `glossary.md` |
| What is true right now | `development-context.md` |
| What happens next | `development-plan.md` |
| How the dataset is built | `dataset/pipeline/00-overview.md` |
| How the model is trained | `fine-tuning/pipeline/00-overview.md` |
| How models are evaluated | `evaluation/harness.md` |
| Past experiments | `experiments/` |
| Decisions | `adr/` |

## Conventions in one line

Layered docs (WHY / WHAT / CONTRACT / STATUS), one home per fact, stable anchors never line
numbers, one concept per word, and a glossary that governs both docs and code.

## Archived material

The pre-restructure docs — the status log, handoffs, RL checkpoints, runbooks, analysis
reports, the paper draft, and the trace previews — now live under `_archive/`. They are
**raw material**, not current specs; the docs above supersede them. `implementation_status.md`
is retired.
