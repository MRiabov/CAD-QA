# Dataset generation

**Status:** active, 2026-10-07.

This directory documents the CAD-QA benchmark-generation pipeline: the code that turns
normalized CadQuery programs into verifiable QA rows. It is the
`dataset_generation` package (today `dataset/`). The dataset-generation pipeline is
**immutable**: these docs describe what the code does; they do not justify refactors
(`plans/oct-7/restructure-docs.md`).

## Reading order

1. `requirements.md` — intended-vs-verified summary: one row per pipeline stage.
2. `pipeline/00-overview.md` — the DAG and the **pipeline-stage IO contract**. Read this before any
   step doc; it is the single authority for artifact and field names between steps.
3. `pipeline/01-source-ingestion.md` … `07-exports-harbor-sft.md` — one doc per pipeline stage.
4. `answer-formats.md` — intended answer formats, current coverage, and the history of the formats that were cut.
5. `decisions.md` — local decisions for the dataset unit, in ADR format.

## What lives where

| Question | Doc |
|---|---|
| What must each pipeline stage do, and does it? | `requirements.md` |
| What flows between stages (artifact/field names)? | `pipeline/00-overview.md` |
| How does a pipeline stage behave, in words? | the step doc |
| Why a dataset-specific choice was made | `decisions.md` and the step doc's local decisions |
| Which answer formats exist, which are generated, and why some were cut? | `answer-formats.md` |
| What the project is for | `../PRD.md` |
| What a term means | `../glossary.md` |
| Where the project actually is | `../development-context.md` |

## Pipeline at a glance

```text
A1 source ingestion -> A2 CadQuery program operation trace -> A3 ontology graph
  -> A4 query synthesis + resolver -> A5 prompt rendering (inside materialization)
  -> A6 materialize / validate / release -> A7 Harbor / SFT / evaluation exports
```

The one-command entry point for a small end-to-end run is:

```bash
rtk uv run cadqa experiment smoke \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/experiment_smoke
```

The step-by-step commands are in `../experiment_execution_runbook.md`.

## The freeze and doc/code conflicts

- The dataset-generation code is immutable. Where a doc and the code disagree, the doc
  records the actual behaviour and the discrepancy is captured as a local decision or open
  question — it is not silently fixed here.
- `specs/` is superseded and is being split into these docs
  (`plans/oct-7/restructure-docs.md`). Treat `specs/dataset-spec.md`,
  `specs/benchmark-task-spec.md`, `specs/multi-hop-qa-task-spec.md`,
  `specs/generation_policy.md`, and `specs/schema.md` as input material, not current
  specs.
- `../implementation_status.md` is a raw status log and is retired; it is input material
  for these docs, not a spec.

## Scope boundary

This pipeline ends at the rows/public/private artifacts and their exports. Training and
evaluation of models live under `docs/train-and-eval/fine-tuning/`; the evaluation harness and baselines
live under `docs/train-and-eval/evaluation/`. The coupling is the dataset file plus the answer contract,
nothing else.

## Extra deliverables - P2

- A generated per-pipeline-stage runnable script folder mirroring the step numbers (the
  restructure plan's "code-experimentation folder" idea), so each doc step has an
  executable counterpart.
