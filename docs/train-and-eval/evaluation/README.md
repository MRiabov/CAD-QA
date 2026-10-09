# Evaluation

**Status:** active, 2026-10-07. Part of the docs restructure
(`plans/oct-7/restructure-docs.md`).

This directory documents how CAD-QA is evaluated: the harnesses that run an LLM model
over dataset rows, and the baselines those results are compared against. It is the
canonical home for the evaluation contract's mechanics; the evaluation contract's
intent (targets, metrics, definition of done) stays in `PRD.md`.

## Reading order

1. **`plan.md`** — the evaluation design: harness modes, the one-scorer rule, evaluation datasets, and
   the H3/H4 external-transfer suite.
2. **`harness.md`** — how an LLM model is run and scored. The three LLM harness modes
   (`numpy` primary, `no_tools`, `cadquery` P2) and Harbor. Read this first.
3. **`baselines.md`** — the baseline families, what is implemented, what was run,
   and what is stale.

## Scope

- In scope: the local small-LLM-model harness (`train_and_eval/eval/eval_bench.py`),
  the Harbor export and runner (`dataset/harbor.py`, `docs/_archive/harbor.md`), the grading
  and answer-parsing contract (`train_and_eval/grading/`), and the baseline families.
- Out of scope: dataset generation and the training pipeline. Their contracts live
  under `dataset/` and `train-and-eval/fine-tuning/`.

## Related canonical references

| What you need | Where |
|---|---|
| Evaluation contract (targets, metrics, definition of done) | `PRD.md#evaluation-contract` |
| Term meaning (`LLM harness mode`, `Harbor`, `verifier`, `answer format`) | `glossary.md` |
| Harbor export and run mechanics (older runbook, raw material) | `docs/_archive/harbor.md` |
| Where the project is today | `development-context.md` |
| Past experiment records | `docs/experiments/` |

## Status vocabulary

Status tags follow `docs-conventions.md#status-tags`: `verified` (a check ran and
passed) · `exists` (present, unchecked) · `missing` · `stale` ·
`[unverified — needs <env>]` · `[unknown]`. A status moves up only when a check
passes. `baselines.md` marks every family and run with exactly one tag.
