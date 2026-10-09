# Fine-tuning pipeline — overview

**Status:** active, 2026-10-09. Rewritten to the Phase 3 design (`../training.md`, `../data.md`, `../system.md`,
`../../evaluation/plan.md`); the 2026-08 gemma pipeline is superseded (FT-D11, FT-D12).

## Purpose

Define the ordered pipeline stages that turn an immutable **dataset file** plus **External datasets**
into a trained small LLM model and its evaluation, and the single contract for the artifacts and fields
that pass between stages.

## Pipeline-stage map (DAG order)

```text
dataset file (immutable CAD-QA rows)
      │
      ▼
[01 rows-loader]  decoded CAD-QA dataset rows
      │
      ▼
[02 teacher-sampling]  agent training traces (`learn_the_cadqa_task`, rejection-sampled)
      │
      ▼
[03 preparation]  registry → ingest/normalize (`TrainingExample`) → quality → dedup/contamination
                  → sample/mix (the progressive curriculum)
      │
      ▼  Liquid `messages` SFT JSONL + manifest
[04 SFT]  phase 1 (general thirds + easy) → phase 2 (task + preserve)
      │
      ▼  adapter → merged LLM model
[05 sampling gate]  pass@k per tier (P0); RL deferred, conditional on the gate (FT-D13)
      │
      ▼
[06 evaluation]  LLM harness modes + the one scorer + the evaluation datasets
      │
      ▼
[07 serving]  merge + GGUF/llama.cpp export; vLLM parity
```

## Pipeline-stage IO contract

Single source of truth for artifact and field names. Step docs restate behaviour but must match this
table.

| Pipeline stage | In | Out | Owner |
|---|---|---|---|
| 01 rows-loader | dataset file (`rows.parquet`/`.jsonl`) | decoded CAD-QA dataset rows | `01-rows-loader.md` |
| 02 teacher-sampling | decoded rows | agent training traces (`learn_the_cadqa_task`) + sampling log | `02-teacher-sampling.md` |
| 03 preparation | traces + External datasets | `TrainingExample` set → Liquid `messages` SFT JSONL + manifest | `../system.md` §7 |
| 04 SFT | Liquid `messages` JSONL | LoRA adapter → merged LLM model | `../training.md` §4 |
| 05 sampling gate | merged LLM model | pass@k per tier (RL deferred, conditional on the gate) | `../system.md` §2–§3 |
| 06 evaluation | trained LLM model + evaluation datasets | scores per evaluation dataset | `../../evaluation/plan.md` |
| 07 serving | merged LLM model | GGUF / vLLM checkpoint | `07-serving-vllm.md` |

## Datasets in play

There is more than one dataset; each has one role (glossary).

- **CAD-QA dataset file** — the immutable benchmark rows (`rows.parquet` / `rows.jsonl`) from
  `dataset_generation`; the input to the fine-tuning pipeline, read by 01. (The Dataset file.)
- **External dataset** — a dataset published outside CAD-QA (tool format, general tasks, priming),
  registered with a pinned revision; ingested by 03.
- **`TrainingExample` set** — the typed training records produced by 03.
- **Mixed training dataset** — the materialized `{dataset_role → weight}` blend for a run (03).
- **Liquid `messages` SFT JSONL** — the on-disk training artifact (03 → 04).
- **Evaluation datasets** — the datasets that serve H1–H4, hard-excluded from training (06).

## Shared interfaces (single-sourced)

- **Format contract** (Liquid `messages` SFT JSONL, native tool tokens) — `../training.md`.
- **`TrainingExample` + converter** — `../system.md` §7.
- **Evaluation datasets + the one scorer** — `../../evaluation/plan.md`.
- **H1–H4** — `../training.md` §1 and `../../evaluation/plan.md` §5.1.

## Step docs

| Step | Doc |
|---|---|
| 00 | this file |
| 01 | `01-rows-loader.md` |
| 02 | `02-teacher-sampling.md` |
| 03 | `03-preparation.md` |
| 04 | `04-sft.md` |
| 05 | `05-grpo.md` |
| 06 | `06-harness-modes.md` |
| 07 | `07-serving-vllm.md` |

## Open questions

- **Q1.** The on-disk artifact is Liquid's `messages` SFT JSONL; confirm `liquid-finetune`'s validator
  accepts our `submit_*` tool declarations unchanged (`../training.md` Q2).
- **Q2.** Does the data campaign stay in one tracked environment, or split SFT and serving
  (`../../../../plans/oct-8/trust-audit.md` Q3)?
