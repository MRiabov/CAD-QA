# Where to start? Intermediate models as base LLM models (2022)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations. Provenance: `[preprint]` (arXiv).

## Citation

Choshen, L., Venezian, E., Don-Yehia, S., Slonim, N. and Katz, Y. (2022) 'Where to start?
Analyzing the potential value of intermediate models', arXiv preprint arXiv:2211.00107.
Available at: `arxiv.org/abs/2211.00107`.

- Reference: `prior-art.md`, reference [14].

## What it is

A systematic study of "intertraining": starting a new fine-tune from an already-fine-tuned
intermediate LLM model rather than the vanilla pretrained base. Broad range of English
classification tasks.

## Findings

- Some target datasets are **intertraining-sensitive** and gain a lot from the right starting
  point; others are indifferent to base selection.
- Some base LLM models are **high quality** and give consistent downstream improvements, but
  **most base models are inferior and degrade performance**.
- Base LLM models can be ranked by quality on a single representative task using **linear
  probing** (training only the classification head), i.e. cheaply and independently of the final
  target dataset.

## Why it matters for CAD-QA

Supports two of our needs: base selection does matter (most candidates hurt), and a cheap
linear-probe signal can rank candidates — the same diagnostic idea as NoReGeo's fixed-encoder
probe. It is a warning against assuming any small base will fine-tune well.

## Related

- `2024-selecting-llm-to-finetune-rectified-scaling-law.md`
- `2025-pretraining-indicators-finetuning-outcomes.md`
