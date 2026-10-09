# distil labs: 12 small LLM models across 8 fine-tuning tasks (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

distil labs (2025) 'We Benchmarked 12 Small Language Models Across 8 Tasks to Find the Best
Base LLM Model for Fine-Tuning', *distil labs blog*, 10 December. Available at:
`distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks-to-find-the-best-base-model-for-fine-tuning`.

- Reference: `prior-art.md`, reference [1].

## What it is

A controlled fine-tuning benchmark: 12 small open LLM models, 8 tasks (classification,
information extraction, open-book QA, closed-book QA), each trained with the same recipe and <!-- dont-say: allow: external task taxonomy -->
compared against the teacher that generated the synthetic data.

## Models

- Qwen3: 8B, 4B-Instruct-2507, 1.7B, 0.6B (thinking disabled).
- Llama: 3.1-8B-Instruct, 3.2-3B-Instruct, 3.2-1B-Instruct.
- SmolLM2: 1.7B-Instruct, 135M-Instruct.
- gemma: gemma-3-1b-it, gemma-3-270m-it.

## Findings

- Best fine-tuned: Qwen3-4B-Instruct-2507 #1 (average rank 2.25), Qwen3-8B #2 (2.75); the
  Qwen3 family takes 4 of the top 6.
- Most tunable (biggest base→tuned gain): Llama-3.2-1B-Instruct #1 (3.44), Llama-3.2-3B #2
  (4.67). Tunability inverts the size hierarchy.
- Best base (zero-shot): Qwen3-8B #1 (1.75).
- A fine-tuned Qwen3-4B matches or exceeds its GPT-OSS-120B teacher on 7 of 8 tasks; on
  SQuAD 2.0 it beats the teacher by 19 points.

## Why it matters for CAD-QA

Three different winners for three questions (best base, best tuned, most tunable) from one
experiment. Base rank does not predict fine-tuned rank, so a base-LLM-model swap is a poor
first lever; pick the base on deployment constraints and let training close the gap.

## Related

- `2026-distil-labs-15-small-models-fine-tuning.md`
- `2026-distil-labs-base-vs-tuned-moe.md`
