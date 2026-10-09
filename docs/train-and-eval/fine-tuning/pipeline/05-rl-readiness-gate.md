# 05 — RL-readiness gate (RL deferred)

## Purpose

After SFT, measure per-prompt reachability with the **RL-readiness gate** (P0). It decides whether RL is
indicated and produces the RFT/RL pool. **RL is deferred**: conditional on the RL-readiness gate, P2 until a tier is
measured learnable (FT-D13; FT-D8 superseded).

## Definition

The RL-readiness gate is an **inference** workload (rollouts), not training — size it in decode/prefill throughput and
rollout latency, not SFT sequences/s.

- **Population:** the train rows (`01`) in the run's mix.
- **Rollouts:** per row, a **rollout count** of completions sampled at the **rollout temperature** (not
  the 0.1 deployment default), each graded by the one scorer (`../../evaluation/plan.md` §4).
- **Pass rate:** passes / rollout count, per row.
- **Tiers (per row):** `mastered` (pass rate 1), `learnable` (0 < pass rate < 1), `unreachable`
  (pass rate 0). The tiers are **measured**, not derived from `difficulty_bucket`/Reasoning hop count —
  those are *priors* to stratify by and validate, not the definition.
- **Defaults:** a rollout count of 8 to screen, 16 to confirm any row or tier we will RL on or report;
  rollout temperature ≈ 1.0. (The rollout count follows the all-pass/all-fail bound: at a 0.25 pass
  rate, the all-fail rate is ~10% at a rollout count of 8 and ~1% at 16.)
- **Outputs:** pass@k per row and per stratum (Reasoning hop count, `difficulty_bucket`, Answer format,
  task family); the **learnable** pool (RL/RFT); the **unreachable** list (Bridge / re-distillation);
  **mastered** rows (evaluation-only).

## RL (deferred, conditional)

- **GRPO with dynamic sampling** (drop all-pass/all-fail groups), RL-eligible pass-rate scheduling, sandboxed
  rollouts, full rollout logging (FT-D9).
- **Reward = the one scorer** (`../../evaluation/plan.md` §4), audited before any RL run (FT-D14).
- **RFT** (rejection-sampling SFT on the tuned policy's **own** correct agent training traces, graded by
  the Query verifier — self-distillation / STaR) is the cheaper consolidation and may replace RL at this
  scale. It is **not** teacher distillation: 02's rejection sampling keeps the **teacher's** accepted
  traces; RFT keeps the **policy's**. Both need accepted generations to exist at all.

## Stop / advance

- any `learnable` row → RL **or** RFT is indicated;
- no `learnable` row → stop at SFT/RFT, RL not indicated (FT-D13);
- `unreachable` rows → Bridge / re-distillation at the next SFT run, or record.

## Inputs / outputs

- **In:** the merged LLM model (04) + decoded rows (01).
- **Out:** pass@k per tier; the learnable pool; optionally an RL adapter; RFT data.

## Verification

```bash
# RL-readiness gate to build (FT-D12); offline reward grading exists:
uv run pytest train_and_eval/eval/test_tool_calls.py -k reward -q
```

## Questions for the owner

- **OD-1.** Screen the **full train split** (≈958 rows × rollout count 8 ⇒ **≈7.7k rollouts total**) or a
  **stratified sample** with a fixed sample size per hop/bucket? Each rollout is one episode — several
  LLM calls in the agentic harness — so the RL-readiness gate is a **throughput job**: order 10⁷ output tokens, i.e.
  **hours on a small single GPU** and infeasible on CPU. **Measure** seconds-per-rollout on a small pilot
  (e.g. 50 rows) first, then size the run; do not assume minutes (the old gemma run was ~10 tok/s,
  launch-bound — a serving-config trap, not the checkpoint).
- **OD-2.** RL-eligible pass rate: **~0.25–0.75** (max reward variance; recommended) or any non-zero,
  non-unity pass rate?
- **OD-3.** Confirm the rollout temperature ≈ 1.0 (rollout), separate from the 0.1 accuracy runs.
  **Provisional** — verify against the RL exploration/sampling literature (research refs [21]–[23], [25])
  as a **P2** task; it only sets the reachability estimate, not any reported accuracy.
- **OD-4.** When **no** tier is `learnable`: is the RL-readiness gate **binding** (stop and report SFT-only, FT-D13) or
  do we fall back to more **teacher re-distillation / Bridge**? Self-RFT cannot proceed here — it needs the
  policy's own correct completions, which do not exist at a zero pass rate.
- **OD-5.** RFT vs GRPO at this scale — decided by the RL-readiness gate, not on paper (`../system.md` Q3).
