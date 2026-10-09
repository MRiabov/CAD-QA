# Warm-start then RL on synthesized terminal tasks (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the environment-scaling
framing. Title held as cited by the environment-scaling survey [30]; exact paper metadata not
captured at survey time.

## Citation

'Endless Terminals' (2026), arXiv:2601.16443. Cited by the environment-scaling survey [30]
(`arxiv.org/html/2511.09586v1`).

- Reference: `prior-art.md`, reference [32].
- Provenance: `[preprint]`.

## What it is

A synthesized terminal-task RL setup, reported by the environment-scaling survey [30] as the
sharpest evidence on **why a warm-start matters** for small LLM models: RL on synthesized tasks is
compared with and without a prior SFT Training stage that teaches the scaffold.

## Findings

- **RL on synthesized tasks transfers to a human-curated benchmark substantially better when the
  LLM model is first SFT'd into the scaffold.** RL from a cold start barely moves a
  small LLM model.
- The job of the warm-start is narrow: get the small LLM model to reliably emit the scaffold's
  action/observation format and to acquire enough competence to produce *some* successful
  rollouts. It is a **readiness check, not an accuracy target** — SFT until format adherence and a
  nonzero rollout success rate, then stop.
- **Over-doing SFT ossifies the policy** and collapses the exploration RL needs; **under-doing it**
  leaves the policy at the floor with **no reward variance**, so RL has nothing to push on.

## Why it matters for CAD-QA

- This is the crisp justification for the system plan's thin SFT Training stage: run SFT only until the
  `submit_*` format holds and pass@k > 0 on the task, then switch to RL. It also warns against
  treating SFT accuracy as the target.
- It explains why a small CAD-QA LLM model needs a cold-start before Training stage 3, and why "just do more
  SFT" is the wrong move once the readiness check clears.
- It pairs with the RL-readiness gate (FT-D13) and the environment-first decision (FT-D15).

## Related

- `2025-scaling-environments-llm-agents.md`
- `2025-rlve-adaptive-verifiable-environments.md`
- `2026-learning-what-to-learn.md`
