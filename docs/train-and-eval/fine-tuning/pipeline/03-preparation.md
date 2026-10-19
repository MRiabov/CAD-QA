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
completion-only loss is a trainer concern to **verify**, not a bespoke pipeline to build. Use the
installed `liquid-finetune` template unmodified; do not vendor, patch, or override it
(`04-sft.md` §Template rule).

Traces above the 16,384-token admission window are rejected here and counted — never right-truncated
(`04-sft.md` §Sequence and truncation policy).

Preparation stages (`../system.md` §7): registry → ingest/normalize → quality gate → dedup/contamination →
sample/mix. The **sample/mix** step applies per-role quotas and includes hop tiers only through the
measured advancement gate (`../data.md` §4.1), not by ordering a static dataset.

## Verification

```bash
# the converter is to be written (FT-D12); it emits Liquid messages from a TrainingExample set
uv run python -m <converter> --in <training_examples.jsonl> --out <sft.parquet>
```

## Open questions

_(none)_

## Resolved questions

- **Q1.** *(2026-10-09)* Preparation consumes **only the 02 agent training traces + External datasets**; the
  raw CAD-QA task rows are **not** an input — we SFT on traces, and the phase-1 low-hop slice is a slice of
  the traces. The rows are already consumed at 01/02.
- **Q2.** *(2026-10-09)* Dedup/contamination stays **simple**: the mix blends **orthogonal** datasets
  (distinct distillation origins/teacher paths), so cross-dataset duplicates are unlikely — use exact/near-dup
  (normalized hash) within the mix plus the hard CAD-QA held-out blocklist (`../data.md` §5). No MinHash/LSH
  unless a measured collision appears.
