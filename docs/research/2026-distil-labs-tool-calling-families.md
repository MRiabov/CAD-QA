# distil labs: Qwen vs Llama vs Gemma vs Liquid for tool calling (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

distil labs (2026) 'Qwen vs Llama vs Gemma for Tool Calling', *distil labs learn*, 2 August.
Available at: `distillabs.ai/learn/qwen-vs-llama-vs-gemma-for-tool-calling`.

- Reference: `prior-art.md`, reference [4].

## What it is

A family comparison for tool calling: which small open LLM models are eligible as students,
their base versus tuned scores, and which family to pick. Teacher for the measured numbers was
`openai.gpt-oss-120b`.

## Eligibility (a hard gate)

- Qwen: Qwen3 (0.6B–8B), Qwen3.5 (0.8B–9B) — none excluded.
- Llama: Llama 3.2 1B/3B, Llama 3.1 8B — none excluded.
- Gemma: Gemma 4 E2B/E4B and FunctionGemma 270M — **all Gemma 3 sizes excluded**.
- Liquid: LFM2, LFM2.5 — none excluded.
- SmolLM2: none (135M and 1.7B excluded).

## Base vs tuned (same tasks)

| LLM model | Task | Base | Tuned | Teacher |
|---|---|---|---|---|
| FunctionGemma 270M | Shell (Gorilla) | 9.90% | 96.04% | 97.03% |
| FunctionGemma 270M | Smart home | 38.82% | 96.71% | 92.11% |
| FunctionGemma 270M | Voice assistant | 23.35% | 90.86% | 96.95% |
| LFM2.5-350M | Shell (Gorilla) | 61.4% | 98.0% | 97.03% |
| LFM2.5-350M | Smart home | 63.2% | 96.7% | 92.11% |
| LFM2.5-350M | Voice assistant | 34.5% | 95.9% | 96.95% |

Base scores spread 9.9%–63.2% across families; tuned scores converge into a 90–98% band.
Reported summary: "the starting point is a family property; the finishing point mostly isn't."

## Family guidance

- Choose **Qwen** for one base covering classification, QA, and tool calling, with the best
  all-round fine-tuned record and strongest un-tuned tool calling.
- Choose **Llama** when seed data is thin and training must close the gap (most tunable).
- Choose **Gemma** only as FunctionGemma or Gemma 4 (native function-call special tokens).
- Consider **Liquid** — LFM2.5-350M posted the highest tuned scores at that size.

## Why it matters for CAD-QA

Fine-tuning moves accuracy far more than family choice, and eligibility is a hard gate: Gemma 3
(our current family line) is excluded from tool calling at every size, while Gemma 4 and the
purpose-built FunctionGemma qualify. Relevant to the base-selection question in Phase 3.

## Related

- `2026-ertas-on-device-tool-calling.md`
- `2026-distil-labs-15-small-models-fine-tuning.md`
