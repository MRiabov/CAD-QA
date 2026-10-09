# 05 — sampling gate (RL deferred)

## Purpose

After SFT, measure per-prompt reachability with a **pass@k gate** (P0). The gate decides whether RL is
indicated and produces the RFT/RL pool. **RL is deferred**: conditional on the gate, P2 until a tier is
measured learnable (FT-D13; FT-D8 superseded).

## Definition

- **Population:** the train rows (`01`) in the run's mix.
- **Rollouts:** per row, `k` completions sampled at the **rollout temperature** `T` (not the 0.1
  deployment default), each graded by the one scorer (`../../evaluation/plan.md` §4).
- **Pass rate:** `r = passes / k`, per row.
- **Tiers (per row):** `mastered` (`r = k`), `learnable` (`0 < r < k`), `unreachable` (`r = 0`). The
  tiers are **measured**, not derived from `difficulty_bucket`/Reasoning hop count — those are *priors* to
  stratify by and validate, not the definition.
- **Defaults:** `k = 8` to screen, `k = 16` to confirm any row or tier we will RL on or report; `T ≈ 1.0`.
  (`k` follows the all-pass/all-fail bound: at `r = 0.25`, `(1-r)^k ≈ 10%` at `k = 8`, `≈ 1%` at `k = 16`.)
- **Outputs:** pass@k per row and per stratum (Reasoning hop count, `difficulty_bucket`, Answer format,
  task family); the **learnable** pool (RL/RFT); the **unreachable** list (Bridge / re-distillation);
  **mastered** rows (evaluation-only).

## RL (deferred, conditional)

- **GRPO with dynamic sampling** (drop all-pass/all-fail groups), pass-rate-band scheduling, sandboxed
  rollouts, full rollout logging (FT-D9).
- **Reward = the one scorer** (`../../evaluation/plan.md` §4), audited before any RL run (FT-D14).
- **RFT** (rejection-sampling SFT on self-generated correct agent training traces) is the cheaper
  consolidation and may replace RL at this scale.

## Stop / advance

- any `learnable` row → RL **or** RFT is indicated;
- no `learnable` row → stop at SFT/RFT, RL not indicated (FT-D13);
- `unreachable` rows → Bridge / re-distillation at the next SFT run, or record.

## Inputs / outputs

- **In:** the merged LLM model (04) + decoded rows (01).
- **Out:** pass@k per tier; the learnable pool; optionally an RL adapter; RFT data.

## Verification

```bash
# gate to build (FT-D12); offline reward grading exists:
uv run pytest train_and_eval/eval/test_tool_calls.py -k reward -q
```

## Questions for the owner

- **OD-1.** Gate the **full train split** (≈8k rollouts at `k = 8`, minutes on the small test GPU;
  recommended) or a **stratified sample** of `N` per hop/bucket?
- **OD-2.** RL-eligible band: **~0.25–0.75** (max reward variance; recommended) or any `0 < r < k`?
- **OD-3.** Confirm the gate temperature `T ≈ 1.0` (rollout), separate from the 0.1 accuracy runs?
- **OD-4.** Is the gate **binding** (no RL unless a `learnable` tier) or **advisory** (record it, proceed to
  RFT regardless)?
- **OD-5.** RFT vs GRPO at this scale — decided by the gate, not on paper (`../system.md` Q3).
