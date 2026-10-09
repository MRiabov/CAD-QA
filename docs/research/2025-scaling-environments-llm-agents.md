# Scaling environments for LLM agents: a survey (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the environment-scaling
framing.

## Citation

'Scaling Environments for LLM Agents in the Era of Learning from Interaction: A Survey' (2025),
arXiv:2511.09586. Available at: `arxiv.org/html/2511.09586v1`. (Author list not captured at survey
time.)

- Reference: `prior-art.md`, reference [30].
- Provenance: `[preprint]`.

## What it is

A survey that reframes agentic RL around the **environment** as the central object. It defines the
anatomy of an environment (generation, execution, feedback), gives a taxonomy of design choices,
and maps the landscape of environment designs.

## Findings

- **Scaling environments scales intelligence.** RL needs verifiable interactive experience at a
  scale that hand-built benchmarks cannot supply, so "environments became the central object."
- Benchmarks are built for **evaluation** (dozens to hundreds of tasks with scorers) — nowhere near
  enough to train RL, which is "hungry for environments" and burns tasks quickly.
- **Environment supply is the bottleneck.** An environment has two roles: an evaluation container
  and, if it can be manufactured at scale, a **training-experience generator**.
- Environment scaling covers the generation/execution/feedback stages and the
  difficulty/coverage/diversity of tasks.

## Why it matters for CAD-QA

- It is the high-level justification for treating the **CAD-QA task environment + scorer** (a task
  generator, the exact-match reward, the `run_code`/kernel tool surface) as the primary asset —
  not the SFT mix.
- It reframes the CAD-QA task dataset: a **generator of CAD-QA tasks with verifiable
  answers**, from which both RL rollouts and (filtered) SFT cold-start data are drawn — not a fixed
  pile of teacher-distilled examples.
- It warns that a fixed task set saturates; coverage/difficulty diversity is what sustains RL.

## Related

- `2025-rlve-adaptive-verifiable-environments.md`
- `2026-endless-terminals-warm-start.md`
- `2026-grpo-null-web-agent.md`
