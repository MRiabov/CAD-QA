# Fine-tuning pipeline

**Status:** active, 2026-10-09. Rewritten to the Phase 3 design (LFM2.5 + `liquid-finetune`); the
2026-08 gemma pipeline is superseded (FT-D11, FT-D12). The design and rationale live in `training.md`
(how we train), `data.md` (which data, in what order), `system.md` (the post-training loop), and
`../evaluation/plan.md` (harness + scorer).

This directory documents how CAD-QA turns an immutable **dataset file** plus **External datasets** into
a trained small LLM model: teacher **rejection sampling** → **preparation** (mixing + conversion to
Liquid `messages`) → **two-phase SFT** → a **sampling gate** and optional **RL** → **evaluation** →
**serving**.

## Start here

1. [requirements.md](requirements.md) — intended-vs-verified summary, environment.
2. [pipeline/00-overview.md](pipeline/00-overview.md) — the DAG and the IO contract
   (the single source of truth for artifact and field names).
3. [decisions.md](decisions.md) — the FT-D* decisions (ADR).
4. The design docs: [training.md](training.md) (how we train), [data.md](data.md) (which data, in what
   order), [system.md](system.md) (the post-training loop + data preparation).

## Pipeline-stage index

| Step | Doc | Status |
|---|---|---|
| 01 | [01-rows-loader.md](pipeline/01-rows-loader.md) | `missing` (re-implemented for Phase 3) |
| 02 | [02-teacher-sampling.md](pipeline/02-teacher-sampling.md) | `[unverified — needs OPENROUTER_API_KEY + network]` |
| 03 | [03-preparation.md](pipeline/03-preparation.md) | `missing` (converter to write) |
| 04 | [04-sft.md](pipeline/04-sft.md) | `[unverified — needs GPU + liquid-finetune]` |
| 05 | [05-grpo.md](pipeline/05-grpo.md) | pass@k gate P0; RL deferred/conditional (FT-D13) |
| 06 | [06-harness-modes.md](pipeline/06-harness-modes.md) | `exists`; `cadquery` mode `missing` |
| 07 | [07-serving.md](pipeline/07-serving.md) | `missing` (merge/export to build) |

## Code ↔ doc map

- `train_and_eval/rows_loader.py` → 01 (retained)
- teacher client + rejection sampling → 02 (to be ported to the LFM2.5 stack)
- `TrainingExample` + converter → 03 (`system.md` §7)
- `liquid-finetune` SFT configs → 04 (`training.md` §4)
- sampling gate + GRPO → 05 (`system.md` §2–§3)
- `train_and_eval/eval/`, `train_and_eval/grading/` → 06 (`../evaluation/plan.md`)
- merge + export → 07 (to be scripted)

## Terms

Use the canonical vocabulary in `../../glossary.md`. Three overloaded terms mean different records:
an **agent training trace** is an agent-facing reasoning + tool-call record (this pipeline's SFT signal);
a **CadQuery program operation trace** is a CadQuery program decomposed into measured operations; an
**answer candidate set trace** is a row's candidate-narrowing record.

## Note on raw material

`../../_archive/agent_handoff_2026-08-09.md`, `../../_archive/rl_progress_2026-08-09.md`,
`../../_archive/rl_checkpoint_2026-08-08.md`, `../../_archive/rl_checkpoint_2026-08-09_2.md`,
`../../_archive/rl_state_2026-08-09_1140.md`, `../../_archive/rl_runbook.md`, and
`../../_archive/text_finetune_runbook.md` are **raw material** for these docs, not current specs. They are superseded
by this directory.
