# 05 — sampling gate and RL

## Purpose

After SFT, measure per-tier reachability and run RL **only where it is learnable** (`../system.md` §2–§3).

## Sampling gate (P0)

Sample k rollouts per prompt with the tuned policy and compute the pass rate per Difficulty tier:

- **mastered** (all k pass): no RL signal; use for evaluation.
- **learnable** (`0 < pass < k`, ideally ~0.25–0.75): the RL-training set.
- **unreachable** (zero pass): no RL signal; add via Bridge / re-distillation or record it.

## RL (conditional, P1)

- **GRPO with dynamic sampling** (drop all-pass/all-fail groups), pass-rate-band scheduling, sandboxed
  rollouts, full rollout logging (FT-D9).
- **Reward = the one scorer** (`../../evaluation/plan.md` §4), audited before any RL run (FT-D14).
- **RFT** (rejection-sampling SFT on self-generated correct traces) is the cheaper consolidation and may
  replace RL at this scale.

## Inputs / outputs

- **In:** the merged LLM model (04) + decoded rows (01).
- **Out:** pass@k per tier; optionally an RL adapter; RFT data.

## Verification

```bash
# reward grading (offline), then a smoke step once the LFM2.5 stack is wired
uv run pytest train_and_eval/eval/test_tool_calls.py -k reward -q
```

## Open questions

- **Q1.** What k for the gate, and how are tiers defined from the Reasoning hop count (`../system.md` Q1)?
- **Q2.** RFT vs GRPO at this scale — decided by the gate, not on paper (`../system.md` Q3).
