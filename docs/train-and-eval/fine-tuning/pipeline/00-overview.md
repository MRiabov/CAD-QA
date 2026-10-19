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
                  → sample/mix (tier-gated inclusion)
      │
      ▼  Liquid `messages` SFT set + manifest
[04 SFT]  phase 1 (general thirds + easy) → phase 2 (task + preserve)
      │
      ▼  LoRA adapter
[05 RL-readiness gate] / [06 evaluation]  run the adapter on **HF Transformers** — the reference runtime (FT-D23)
      │
      └─(on demand)▶ [07 merge + serve]  merged LLM model / GGUF / vLLM endpoint (FT-D20, FT-D21)
```

File numbers are doc indices, **not** execution order. The RL-readiness gate (05) and evaluation (06) run the **adapter
on HF Transformers** — the reference runtime (FT-D23) — so they need no merge. Merge + serve (07) is
**on demand**, only when a served/non-Transformers runtime is used (FT-D20, FT-D21).

## Pipeline-stage IO contract

Single source of truth for artifact and field names. Step docs restate behaviour but must match this
table.

| Pipeline stage | In | Out | Owner |
|---|---|---|---|
| 01 rows-loader | CAD-QA dataset file (`rows.parquet`) | decoded CAD-QA dataset rows | `01-rows-loader.md` |
| 02 teacher-sampling | decoded rows | agent training traces (`learn_the_cadqa_task`) + sampling log | `02-teacher-sampling.md` |
| 03 preparation | traces + External datasets | `TrainingExample` set → Liquid `messages` SFT set + manifest | `03-preparation.md` |
| 04 SFT | Liquid `messages` set | LoRA adapter | `04-sft.md` |
| 07 merge + serve | LoRA adapter | merged LLM model → GGUF / vLLM-SGLang endpoint (on demand) | `07-serving.md` |
| 05 RL-readiness gate | LoRA adapter (HF Transformers reference) | `pass@1` + CI per tier (RL deferred, conditional on the RL-readiness gate) | `05-rl-readiness-gate.md` |
| 06 evaluation | LoRA adapter (HF Transformers reference) + evaluation datasets | scores per evaluation dataset | `06-harness-modes.md` |

## Datasets in play

There is more than one dataset; each has one role (glossary).

- **CAD-QA dataset file** — the immutable benchmark rows (`rows.parquet`) from `dataset_generation`;
  the input to the fine-tuning pipeline, read by 01. (The Dataset file.)
- **External dataset** — a dataset published outside CAD-QA (tool format, general tasks, priming),
  registered with a pinned revision; blended into a Mixed training dataset at 03.
- **`TrainingExample` set** — the typed training records produced by 03.
- **Mixed training dataset** — the `{dataset_role → weight}` blend we **train on**
  (`mixed_dataset_<composition>`); we almost always load a Mixed training dataset, not raw External
  datasets. Materialized to Liquid `messages` set for the run.
- **Liquid `messages` SFT set** — the on-disk training artifact (03 → 04).
- **Evaluation datasets** — the datasets that serve H1–H4, hard-excluded from training (06).

## Shared interfaces (single-sourced)

- **Format contract** (Liquid `messages` SFT set, native tool tokens) — `../training.md`.
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
| 05 | `05-rl-readiness-gate.md` |
| 06 | `06-harness-modes.md` |
| 07 | `07-serving.md` |

## Open questions

- **Q1.** The on-disk artifact is a Liquid `messages` SFT set; confirm `liquid-finetune`'s validator
  accepts our `submit_*` tool declarations unchanged, and that it accepts a Parquet path (container is
  Parquet-preferred; `../training.md` §4).
- **Q2.** Serving is a **separate inference runtime by design** (FT-D20). Liquid documents the runtimes
  (`docs.liquid.ai/deployment/*`): vLLM / SGLang (GPU), llama.cpp / GGUF (CPU/edge), Transformers
  (direct). Pick which GPU runtime serves our batched evaluation/rollouts — vLLM or SGLang
  (`../../../../plans/oct-8/trust-audit.md` Q3).
