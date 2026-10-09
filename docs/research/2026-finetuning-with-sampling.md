# Finetuning with sampling: SFT learns better than you think (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the RL-alternative citations.

## Citation

'Finetuning with Sampling: SFT Learns Better Than You Think' (2026), arXiv:2610.02140. Available at:
`arxiv.org/html/2610.02140`. (Author list not captured at survey time.)

- Reference: `prior-art.md`, reference [25].
- Provenance: `[preprint]`.

## What it is

A comparison of SFT with sampling (rejection sampling / best-of-n supervised fine-tuning) against
on-policy methods such as reinforcement learning and self-distillation, on new-task generalization
and prior-capability retention.

## Findings

- **SFT with sampling can outperform on-policy counterparts (RL, self-distillation)** on new-task
  generalization **and** on retaining prior capability.
- This reframes the SFT/RL split: the on-policy advantage is not automatic, and a sampling-based
  SFT step can capture much of the benefit at lower cost and lower hacking risk.

## Why it matters for CAD-QA

- It is the strongest argument that **Stage 2 (sampling gate + rejection-sampling fine-tuning) may
  be the whole answer for a single-GPU thesis**, with Stage 3 (GRPO) optional rather than assumed.
- It pairs with the stage-specific data finding [8]: use SFT to acquire/consolidate from the
  LLM model's own correct samples, and reserve RL for what remains unreachable.
- It also aligns with the LoRA-preserves-pretraining result [19]: a sampling SFT step on LoRA is
  cheap and retention-safe.

## Related

- `2026-grpo-null-web-agent.md`
- `2026-learning-what-to-learn.md`
- `2026-sft-vs-rl-tool-calling.md`
