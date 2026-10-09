# SFT or RL for tool-calling agents: a controlled study across data, method, and scale (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Laskar, M.T.R., Fu, X.-Y. and Shashi Bhushan, T.N. (2026) 'SFT or RL for Tool-Calling Agents? A
Controlled Study Across Data, Method, and Scale', arXiv preprint arXiv:2609.17848. Available at:
`arxiv.org/abs/2609.17848`.

- Reference: `prior-art.md`, reference [19].
- Provenance: `[preprint]`.

## What it is

A controlled comparison of three post-training strategies — SFT with LoRA, GRPO, and SFT followed
by GRPO — across six Qwen3 sizes (0.6B to 32B), on three public tool-calling training corpora
(`xLAM/APIGen 60k`, `ToolACE`, `Glaive-FC-v2`) plus a uniform mixture of the three. Evaluated
in-distribution and under cross-dataset transfer.

## Findings

- **SFT with LoRA is the strongest in-distribution method**, best in 15 of 18 settings; GRPO is
  best in 2 and SFT-then-GRPO in 1. SFT never falls below zero-shot; GRPO and SFT-then-GRPO each
  do in some settings.
- **Cross-dataset transfer is the one place RL helps, and only slightly.** Among 54 cross-dataset
  settings, GRPO is best in 29, SFT in 19, SFT-then-GRPO in 6 — but GRPO's average gain over SFT
  is under one point.
- **Training-corpus choice matters as much as the method**, moving in-distribution accuracy by up
  to 55 points.
- **A uniform mixture is the best deployment default**, close to the best in-distribution
  specialist and best on transfer.
- **LoRA beats full fine-tuning** at 4B on all three corpora (88.0 vs 80.4 on `xLAM`; 30.4 vs 22.8
  on `ToolACE`; 47.6 vs 44.1 on `Glaive`), read by the authors as LoRA better preserving
  pretrained tool-use ability.
- Corpus scale and shape after near-duplicate removal: `xLAM` 56,443 examples (0% multi-turn,
  54.2% parallel calls); `ToolACE` 9,715 (4.5% multi-turn, 17.2% parallel); `Glaive` 46,204
  (92.6% multi-turn, 0% parallel; 58.5% of rows removed as near-duplicates).

## Why it matters for CAD-QA

- Directly supports the plan's **SFT + LoRA default** (`fine-tuning-architecture-plan.md`, H1) and
  its decision to **defer GRPO/RL to P2**: combining SFT and GRPO gives no consistent benefit under
  a matched budget, which matches the recorded CAD-QA GRPO collapse and refs [7]/[8].
- "Corpus choice matters as much as the method" validates treating the data pipeline as the main
  lever, and **mixing corpora** rather than betting on one format set (`mix-format`).
- "LoRA beats full fine-tuning" supports the **LoRA-bf16 default** and not full fine-tuning.
- Gives concrete per-corpus statistics (multi-turn rate, parallel-call rate, near-duplicate rate)
  that we should record for our own candidate corpora.

## Related

- `2026-rl-squeezes-sft-expands.md`
- `2026-learning-what-to-learn.md`
- `2026-slm-agentic-tool-calling.md`
- `2025-small-models-big-tasks-function-calling.md`
