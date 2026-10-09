# Online difficulty filtering for reasoning-oriented RLVR (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the RL-scheduling citations.

## Citation

'Online Difficulty Filtering for Reasoning Oriented Reinforcement Learning' (2025), arXiv:2504.03380.
Available at: `arxiv.org/html/2504.03380v2`. (Author list not captured at survey time.)

- Reference: `prior-art.md`, reference [21].
- Provenance: `[preprint]`.

## What it is

A theoretical and empirical treatment of difficulty-aware prompt selection in GRPO-style
reinforcement learning with verifiable rewards (RLVR). It ties the **reward variance** of a
prompt's rollout group to the learnability of that prompt, and filters prompts into an
intermediate-difficulty band.

## Findings

- **Reward variance is a lower bound on the reverse KL divergence** between the initial policy and
  the optimal policy — so it is a principled proxy for how much a prompt can teach.
- Prompts with a very low or very high pass rate should be filtered; prompts with a pass rate
  around **0.5** maximize learnability. The paper's example band is **0.25 ≤ p(x) ≤ 0.75**.
- An asynchronous fixed-batch implementation replaces filtered prompts without shrinking the batch.

## Why it matters for CAD-QA

- Gives the number behind the system plan's pass-rate band (refs [21][22]): keep the learnable
  middle, drop the saturated and the unreachable.
- Also justifies the data doc's per-then "learnable band" framing: a difficulty tier is not a
  training instruction but a measured region of the pass-rate curve.
- Suggests recording pass-rate histograms per hop, not just mean accuracy.

## Related

- `2026-rollout-pass-rate-control.md`
- `2026-dapo-decoupled-clip-dynamic-sampling.md`
- `2026-grpo-null-web-agent.md`
