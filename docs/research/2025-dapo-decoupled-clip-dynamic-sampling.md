# DAPO: decoupled clip and dynamic sampling (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the RL-design citations.

## Citation

Yu, Q. et al. (2025) 'DAPO: An Open-Source LLM Reinforcement Learning System at Scale',
arXiv:2503.14476. Available at: `arxiv.org/abs/2503.14476`.

- Reference: `prior-art.md`, reference [23].
- Provenance: `[preprint]`.

## What it is

A GRPO-family open-source RL system that modifies four parts of the surrounding recipe while
keeping the critic-free, group-normalized core.

## Findings

The four DAPO techniques, as commonly summarized:

- **Dynamic sampling** — drop all-correct / all-wrong groups (zero advantage) and resample to fill
  the batch, so every batch carries gradient signal.
- **Clip-Higher (asymmetric clipping)** — separate low/high clip bounds to keep exploration alive
  and fight entropy collapse.
- **Token-level loss aggregation** — divide by total tokens across the group so long completions are
  not underweighted.
- **Overlong reward shaping** — penalize runaway-length completions instead of letting them poison
  the signal.

## Why it matters for CAD-QA

- Gives the concrete mechanism for the system plan's Training stage 3: run GRPO *with dynamic sampling*, not
  vanilla GRPO, or degenerate groups (the recorded hop-2 collapse) consume the rollout budget.
- The entropy/overlong techniques address the "RL squeezes" entropy collapse noted in [7].
- These are configuration-level changes with a maintained open implementation, so they are cheap to
  adopt if RL is indicated.

## Related

- `2025-online-difficulty-filtering-rlvr.md`
- `2026-rollout-pass-rate-control.md`
- `2026-rl-squeezes-sft-expands.md`
