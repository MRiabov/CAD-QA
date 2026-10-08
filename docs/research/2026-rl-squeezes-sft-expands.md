# RL squeezes, SFT expands: a comparative study of reasoning LLMs (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Matsutani, K., Takashiro, S., Minegishi, G., Kojima, T., Iwasawa, Y. and Matsuo, Y. (2026) 'RL
Squeezes, SFT Expands: A Comparative Study of Reasoning LLMs', *International Conference on
Learning Representations (ICLR)*. arXiv preprint arXiv:2509.21128. Available at:
`arxiv.org/abs/2509.21128`.

- Reference: `prior-art.md`, reference [7].

## What it is

An analysis of how SFT and RL-with-verifiable-rewards shape the *reasoning process*, not just
accuracy. The authors build a reasoning-graph framework and study 1.5B, 7B, and 14B LLM models
on mathematical and code tasks.

## Findings

- **SFT expands** the reasoning graph: higher robustness, better reachability efficiency, low
  modularity — the LLM model can explore a wider solution space.
- **RL squeezes** the graph into a few high-degree hubs: efficient traversal but reduced
  robustness and reachability.
- The best practice of two-stage **SFT→RL** is explained by these complementary effects:
  SFT first establishes a broad policy, then RL sharpens it.
- Global efficiency and algebraic connectivity correlate positively with pass@1/pass@k;
  modularity correlates negatively.

## Why it matters for CAD-QA

Directly relevant to CAD-QA's recorded GRPO collapse (2-token completions, near-zero entropy),
which matches the "RL squeezes" failure mode. It argues for keeping the SFT→RL order (recorded
as FT-D8 but not implemented as a chain) and monitoring entropy/entropy-collapse rather than
running RL from the base policy.

## Related

- `2026-learning-what-to-learn.md`
- `2026-privileged-on-policy-distillation.md`
