# Rollout pass-rate control (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the RL-scheduling citations.

## Citation

'Rollout Pass-Rate Control: Steering Binary-Reward RL Toward Its Most Informative Regime' (2026),
arXiv:2605.05112. Available at: `arxiv.org/pdf/2605.05112`.

- Reference: `prior-art.md`, reference [22].
- Provenance: `[preprint]`.

## What it is

An analysis of *where* on the pass-rate axis a binary-reward RLVR update is most useful, and a
method (prefix replay) to steer skewed rollout groups toward that regime under a fixed rollout
budget.

## Findings

- **A 50% rollout pass rate maximizes** reward entropy, group-filtering survival, advantage energy,
  and the number of success/failure pairs.
- A **1/8 or 7/8 group carries little more than half** the per-rollout information of a balanced
  group, so highly skewed (but non-degenerate) groups still give weak contrast.
- Group filtering (dropping all-zero/all-one groups) is necessary but not sufficient; skew remains.

## Why it matters for CAD-QA

- Hardens the system plan's band choice: aim the distribution at ~0.5, not merely "not degenerate".
- For CAD-QA, a hop tier whose SFT pass rate is 7/8 is *technically* learnable but provides weak
  gradient; the RL-readiness gate should prefer tiers nearer the middle, or rebalance data, before spending
  rollout compute.

## Related

- `2025-online-difficulty-filtering-rlvr.md`
- `2026-dapo-decoupled-clip-dynamic-sampling.md`
- `2026-grpo-null-web-agent.md`
