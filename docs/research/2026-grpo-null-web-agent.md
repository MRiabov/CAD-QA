# A learning-rate-gated failure of GRPO in a small web agent (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the RL-design citations.

## Citation

'A Learning-Rate-Gated Failure of GRPO in a Small Language and Vision-Language Model Web Agent: A <!-- dont-say: allow -->
Controlled Null and Its Mechanism' (2026), arXiv:2607.12640. Available at:
`arxiv.org/html/2607.12640v1`. (Author list not captured at survey time.)

- Reference: `prior-art.md`, reference [20].
- Provenance: `[preprint]`.

## What it is

A controlled comparison of GRPO against the same small LLM model's supervised start, with a
matched positive control, on a web-agent task. It establishes a reinforcement-learning **null**
and then explains it at the level of individual weight groups.

## Findings

- **GRPO adds no credible gain on tasks the agent has already mastered.** The report's headline:
  it is not that the recipe is broken, it is that there is nothing left to learn on mastered
  tasks — the reward is already saturated.
- **The same recipe gains 22 points where the reward is reachable by sampling.** The positive
  control shows the null is a property of the task, not of the training recipe.
- The mechanism is **learning-rate-gated**: the update fails to move the weights that would need to
  change, while sharpening choices the supervised LLM model could already make.

## Why it matters for CAD-QA

- This is the clearest statement of why the recorded CAD-QA **GRPO hop-2 collapse** happened:
  on a tier the SFT policy already clears (or can never clear), a group-relative advantage has no
  signal. It is not bad luck.
- It converts our RL plan into a **conditional** one: RL only on tiers that are *reachable but not
  mastered*. Hence the pass@k sampling gate (`fine-tuning-system-plan.md` §3).
- It corroborates the controlled tool-calling result [19] that SFT-then-GRPO is rarely worth it
  under a matched budget.

## Related

- `2026-learning-what-to-learn.md` (Training-stage-specific data, pass@k predicts RL potential)
- `2025-bread-branched-rollouts.md` (SFT+RL failure when traces are too hard)
- `2026-sft-vs-rl-tool-calling.md`
