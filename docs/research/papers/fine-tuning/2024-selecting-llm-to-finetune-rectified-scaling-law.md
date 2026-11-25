# Selecting an LLM model to fine-tune via a rectified scaling law (2024)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations. Provenance: `[peer-reviewed]` (ICML 2024).

## Citation

Lin, H., Huang, B., Ye, H., Chen, Q., Wang, Z., Li, S., Ma, J., Wan, X., Zou, J. and Liang, Y.
(2024) 'Selecting Large `Language Model` to Fine-tune via Rectified Scaling Law', *Proceedings of
the 41st International Conference on Machine Learning (ICML)*. arXiv preprint arXiv:2402.02314.
Available at: `arxiv.org/abs/2402.02314`.

- Reference: `prior-art.md`, reference [13].

## What it is

An academic study of **which base LLM model to fine-tune**. The authors frame selection as a
resource-constrained prediction of full-fine-tuning performance, and run experiments on 30 LLM
models from 100M to 7B parameters.

## Findings

- Intuitive selection methods — LLM model size, zero-shot performance, or fine-tuned performance on
  a small subset — all fail to predict full-fine-tuning performance; the correlation with the
  ground truth is low and can even be negative.
- They find a previously unobserved "pre-power phase" in fine-tuning loss at low data budgets,
  and fit a rectified fine-tuning scaling law across both phases.
- Their "Accept then Stop" selection algorithm picks a near-optimal LLM model with orders of
  magnitude less compute than full fine-tuning of every candidate.

## Why it matters for CAD-QA

The peer-reviewed basis for the practitioner claim that base rank does not predict fine-tuned
rank. It directly supports measuring candidates on our own data instead of choosing a
base LLM model from a leaderboard.

## Related

- `2022-where-to-start-intermediate-models.md`
- `2025-pretraining-indicators-finetuning-outcomes.md`
