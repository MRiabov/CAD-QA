# Pre-training indicators and fine-tuning outcomes (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations. Provenance: `[preprint]` (arXiv).

## Citation

Zeng, H., Hui, K., Zhuang, H., Qin, Z., Yue, Z., Zamani, H. and Alon, D. (2025) 'Can
Pre-training Indicators Reliably Predict Fine-tuning Outcomes of LLMs?', arXiv preprint
arXiv:2504.12491. Available at: `arxiv.org/abs/2504.12491`.

- Reference: `prior-art.md`, reference [15].

## What it is

A study of whether cheap pre-training signals can predict how an LLM model will perform **after
supervised fine-tuning**, at a fixed LLM model size. The authors build 50 1B-parameter LLM variants
with systematically varied pre-training configurations and SFT them on diverse tasks.

## Findings

- Conventional perplexity is a **misleading** indicator of downstream fine-tuning outcome.
- They formulate selection as a pairwise classification (which of two LLM models will be better
  after SFT) and introduce unsupervised and supervised proxy metrics derived from pre-training.
- The proxy metrics reduce the relative performance-prediction error rate by over 50%.

## Why it matters for CAD-QA

Another academic warning against picking a base LLM model by a pre-training metric or
leaderboard. It also offers a concrete cheap-selection method (proxy metrics) if we want to rank
candidates before spending GPU time.

## Related

- `2024-selecting-llm-to-finetune-rectified-scaling-law.md`
- `2022-where-to-start-intermediate-models.md`
