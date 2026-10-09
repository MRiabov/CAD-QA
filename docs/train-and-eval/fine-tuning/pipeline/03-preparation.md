# 03 — preparation (normalization, mixing, conversion)

## Purpose

Turn accepted **agent training traces** (02) and the **External datasets** into a typed `TrainingExample`
set, then render it to **Liquid's `messages` SFT set** — the on-disk training artifact.

## Inputs / outputs

- **In:** agent training traces (02), External datasets (`../data.md` §2).
- **Out:** the `TrainingExample` set (`../system.md` §7) → **Liquid `messages` SFT set** + **manifest**.
- **Fields** (`../system.md` §7): `id`, `dataset_role`, `messages`, `source_id`, `source_revision`,
  `license`, `reasoning_text`, `tool_call_text`, `tools`, `answer_format`, `reasoning_hop_count`,
  `split`, `provenance`. Reasoning, visible output, and tool calls stay distinct (A5).

## Requirement

The assistant turn must use LFM2.5's native tool tokens (`<|tool_call_start|>`/`<|tool_call_end|>`,
**Pythonic by default**); base-specific rendering is re-derived, never reused (FT-D3, FT-D11). The
converter does **not** hand-render the chat template — `liquid-finetune` applies it, and
completion-only loss is a trainer concern to **verify**, not a bespoke pipeline to build.

Preparation stages (`../system.md` §7): registry → ingest/normalize → quality gate → dedup/contamination →
sample/mix. The **sample/mix** step applies per-role quotas and orders the `learn_the_cadqa_task` rows
by Reasoning hop count (the progressive curriculum, `../data.md` §4).

## Verification

```bash
# the converter is to be written (FT-D12); it emits Liquid messages from a TrainingExample set
uv run python -m <converter> --in <training_examples.jsonl> --out <sft.parquet>
```

## Open questions

- **Q1.** Whether preparation needs the raw CAD-QA task rows at all, or only the 02 traces (the phase-1
  low-hop slice is a slice of the traces, not of the rows) — confirm against the mix (`../data.md` §4).
- **Q2.** Contamination/dedup mechanics (MinHash/LSH, benchmark blocklist) at the scale of the mix.
