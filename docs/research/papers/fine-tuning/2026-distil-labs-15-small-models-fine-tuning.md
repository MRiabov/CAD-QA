# distil labs: 15 small LLM models across 9 fine-tuning tasks (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

distil labs (2026) 'What Small `Language Model` Is Best for Fine-Tuning', *distil labs blog*,
16 March. Available at: `distillabs.ai/blog/what-small-language-model-is-best-for-fine-tuning`.

- Reference: `prior-art.md`, reference [2].

## What it is

The follow-up to the 12-LLM-model benchmark: 15 small open LLM models across 9 tasks
(classification, information extraction, document understanding, open-book QA, closed-book <!-- dont-say: allow: external task taxonomy -->
QA, tool calling), same training recipe, compared against the teacher.

## Findings

- Most tunable: the Liquid LFM2 family sweeps the top three — LFM2-350M #1 (average rank
  2.11), LFM2-1.2B #2 (3.44), LFM2.5-1.2B-Instruct #3 (4.89); then Llama-3.2-1B-Instruct
  (6.00), Llama-3.2-3B-Instruct (6.56), Qwen3-0.6B (6.89).
- Best fine-tuned: the Qwen3 family takes 4 of the top 6 — Qwen3-8B #1 (2.33),
  Qwen3-4B-Instruct-2507 #2 (3.33); Llama takes the next places.
- Reported guidance: Qwen3-4B-Instruct-2507 for strong accuracy at a smaller footprint;
  LFM2-350M/LFM2-1.2B for maximum tuning gain; Qwen3-0.6B or Llama-3.2-1B under 2B.

## Why it matters for CAD-QA

This is the study that first put the Liquid LFM2 family at the top of *tunability* among small
LLM models, and it repeats the 12-LLM-model finding that the most tunable LLM model is not the
best base. Directly supports recording LFM2.5 as a fine-tuning candidate.

## Related

- `2025-distil-labs-12-small-models-fine-tuning.md`
- `2026-distil-labs-base-vs-tuned-moe.md`
