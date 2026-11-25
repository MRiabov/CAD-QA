# Where the reward scorer fails: a category-level audit of RLVR reward signals (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the reward-audit citations.

## Citation

Xin, E. (2026) 'Where the Verifier Fails: A Category-Level Audit of Reward Signals in RLVR', <!-- dont-say: allow -->
arXiv:2609.01354. Available at: `arxiv.org/abs/2609.01354`.

- Reference: `prior-art.md`, reference [24].
- Provenance: `[preprint]`.

## What it is

A metamorphic audit of the reward scorer rather than the LLM model, across four widely used answer
scorers and 307,420 verdicts. It generates certified-equivalent answer variants (rewrites that
preserve meaning by construction), so any rejection is a provable false negative needing no human
adjudication.

## Findings

- **Self-validation on identical inputs ranges from 53.8% to 95.2%** — a 41.3-point spread. The
  published reliability figure describes one implementation, not the task.
- **Two configurations of the same library disagree on 49.9% of pairs.**
- Verifiers with similar aggregate error fail for **opposite reasons**; a reference numeric cascade
  accepts off-by-one answers as a step function of magnitude (0% below 10^4, 100% at or above)
  because its relative tolerance is scale-invariant.

## Why it matters for CAD-QA

- This is the clearest justification for making the **one-scorer reconciliation (TA-A3) a P0 check
  before RL**, not cleanup: in RLVR the scorer *is* the objective.
- CAD-QA's `number` and `coordinate` Answer formats are exactly the scale-sensitive numeric case
  the paper flags; the `1e-3` relative float rule needs an explicit metamorphic test.
- The three divergent CAD-QA scorers are this risk already materialized; the audit method
  (equivalent-answer variants) is the fixture TA-A2 should build.

## Related

- `2026-gradient-fingerprints-reward-hacking.md`
- `2026-prm-reward-hacking-aamas.md`
- `../train-and-eval/fine-tuning/decisions.md` (FT-D6)
