# Privileged on-policy self-distillation harms thinking LLM models (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Kaur, S., Ri, N., He, Y., Fowl, L.H. and Arora, S. (2026) 'Rethinking On-Policy
Self-Distillation for Thinking Models', *ICML 2026 Workshop on Foundation Models and
Generative AI (FoGen)*. Available at: `openreview.net/forum?id=VhCJItwQHn`.

- Reference: `prior-art.md`, reference [9].

## What it is

A study of self-distillation, where an LLM model acts as its own teacher augmented with privileged
information (for example a reference solution). The authors test whether this helps or hurts
*thinking* LLM models that rely on test-time reasoning.

## Findings

- Privileged-context self-distillation degrades thinking LLM models: up to a **17% relative
  drop in avg@16** across five Qwen3 and OLMo thinking LLM models on AIME24, AIME25, and HMMT25.
- The degradation scales with how much privileged context the student sees, and is worst at
  long rollout budgets — where thinking LLM models otherwise gain most.
- Diagnosis: privileged context lowers "fork rates" (positions where multiple continuations
  stay plausible), suppressing self-correction, reverification, backtracking, and hedging.
- Vanilla on-policy distillation improves thinking LLM models, but privileged on-policy
  distillation reverses those gains.

## Why it matters for CAD-QA

A caution for copying full teacher reasoning data into SFT: the teacher's reasoning can suppress
the student's own self-correction at high-entropy positions. Relevant because CAD-QA's teacher
sampling records full reasoning and the SFT signal may be imitation-heavy; the token-level
signal around correction/verification is the part to protect.

## Related

- `2026-rl-squeezes-sft-expands.md`
- `2026-learning-what-to-learn.md`
