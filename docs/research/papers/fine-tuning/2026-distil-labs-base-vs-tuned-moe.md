# distil labs: base vs fine-tuned rank in mid-size MoE LLM models (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

distil labs (2026) 'Does `Base-Model` Accuracy Predict Fine-Tuned Performance: A Mid-Size MoE
Benchmark', *distil labs blog*, 16 July. Available at:
`distillabs.ai/blog/does-base-model-accuracy-predict-fine-tuned-performance`.

Also: distil labs (2026) 'Does `Base Model` Accuracy Predict Fine-Tuned Performance?', *distil
labs*, 2 August. Available at:
`distillabs.ai/learn/does-base-model-accuracy-predict-fine-tuned-performance`.

- Reference: `prior-art.md`, reference [3].

## What it is

Four comparable mid-size mixture-of-experts LLM models fine-tuned with one recipe across seven
tasks (classification scored by accuracy, three function-calling tasks scored by staged tool
call, three QA tasks scored by a reference-free LLM judge). Teacher held constant.

## Findings

| LLM model | Base rank | Tunability rank | Fine-tuned rank |
|---|---|---|---|
| Nemotron-3-Nano-30B | 3.43 (worst) | 1.29 (best) | 1.00 (tied best) |
| Qwen3.6-35B | 2.14 | 2.00 | 1.00 (tied best) |
| gemma-4-26b | 1.43 (best) | 2.57 | 1.86 |
| gpt-oss-20b | 1.71 | 2.57 | 1.86 |

The LLM model with the **worst** zero-shot score was the most tunable and tied for best after
fine-tuning; the LLM model with the best base score finished behind. The two authors' reading:
base leaderboards are a poor guide to which base LLM model to fine-tune.

## Why it matters for CAD-QA

Repeats the small-LLM-model result at the mid-size MoE tier (the ordering nearly inverts), so it is
further evidence that our "effort without gain" is more likely recipe/data than base choice.
The author's practical advice: measure two candidates on your own data rather than reading
leaderboards.

## Related

- `2025-distil-labs-12-small-models-fine-tuning.md`
- `2026-distil-labs-15-small-models-fine-tuning.md`
