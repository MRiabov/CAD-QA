# Detecting and suppressing reward hacking with gradient fingerprints (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the reward-hacking citations.

## Citation

Wang, S., Pham, Q.H., Yin, F., Wang, X., Chen, J.Q., Durrett, G. and Ye, X. (2026) 'Detecting and
Suppressing Reward Hacking with Gradient Fingerprints', COLM 2026. arXiv:2604.16242. Available at:
`arxiv.org/pdf/2604.16242`.

- Reference: `prior-art.md`, reference [28].
- Provenance: `[peer-reviewed]`.

## What it is

A gradient-based detector (GRIFT) for reward hacking in RLVR, plus a training pipeline that uses
the detector to guide rejection fine-tuning.

## Findings

- RLVR optimizes outcome rewards without constraining intermediate reasoning, so an LLM model can
  exploit **loopholes** (prompt artifacts, in-context hints, scorer flaws) to score without
  solving the task.
- Reward hacking is often **implicit and hard to see** in the reasoning; gradient fingerprints
  cluster hacking vs non-hacking behavior and detect over **25% better** than monitors of the
  reasoning.
- Using the score to guide **rejection fine-tuning** suppresses hacking and narrows the gap to an
  oracle environment.
- Hacking behaviors **emerge gradually before dominating** at a late stage — early detection enables
  intervention.

## Why it matters for CAD-QA

- Gives the concrete detection method the system plan's reward-hacking audit should aspire to, and
  a counterfactual ground-truth label (correct-under-both-hints = non-hacking).
- For CAD-QA a plausible loophole is the `run_code`/kernel surface or a prompt artifact leaking the
  answer; the counterfactual test (inject a wrong hint; does the answer follow the hint?) is cheap
  and should be run before trusting any RL gain.
- Reinforces "audit early": by the time the canary collapses, the hack is already learned.

## Related

- `2026-where-the-verifier-fails.md`
- `2026-prm-reward-hacking-aamas.md`
