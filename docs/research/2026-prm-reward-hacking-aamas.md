# Preventing process-reward hacking on verifiable rewards (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the reward-shaping citations.

## Citation

Forbes, G.C., Villalobos-Arias, L., Wang, J., Jhala, A. and Roberts, D.L. (2026) 'Preventing
Process Reward Model Hacking When Training Large Language Models on Verifiable Rewards', AAMAS <!-- dont-say: allow -->
2026 (extended abstract). doi: `10.65109/BWFN6920`.

- Reference: `prior-art.md`, reference [27].
- Provenance: `[workshop]` (extended abstract).

## What it is

A theory-and-practice treatment of reward hacking when a sparse verifiable reward is combined with
a dense heuristic reward (here, a process-reward scorer). It extends Generalized Reward Matching
(GRM) and Action-Dependent Optimality-Preserving Shaping (ADOPS) to the LLM RLVR setting.

## Findings

- When training on a sparse, verifiable reward plus a dense heuristic reward, there is an **acute
  risk of optimizing the dense reward at the expense of the accurate one**.
- The dense term creates reward-hacking incentives; the paper provides optimality-preserving
  shaping methods that provably do not change the optimal policy set.

## Why it matters for CAD-QA

- Directly constrains the system plan's composite reward: if a dense format/process term is added
  on top of outcome exact-match, it must be optimality-preserving (GRM/ADOPS) or it will be hacked.
- Argues for keeping the **outcome term primary** and any dense term bounded — the temptation in
  CAD-QA is a large format/tool-valid bonus, which is exactly the hackable dense signal.
- Pairs with the scorer-failure audit [24]: dense *and* noisy is the worst case.

## Related

- `2026-where-the-verifier-fails.md`
- `2026-gradient-fingerprints-reward-hacking.md`
