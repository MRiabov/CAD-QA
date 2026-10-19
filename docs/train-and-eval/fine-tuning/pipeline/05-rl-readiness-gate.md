# 05 — RL-readiness gate (RL deferred)

## Purpose

After SFT, measure per-prompt reachability with the **RL-readiness gate** (P0). It decides whether RL is
indicated and produces the RFT/RL pool. **RL is deferred**: conditional on the RL-readiness gate, P2 until a tier is
measured learnable (FT-D13; FT-D8 superseded).

## Definition

The RL-readiness gate is an **inference** workload (rollouts), not training — size it in decode/prefill throughput and
rollout latency, not SFT sequences/s.

- **Population:** the train rows (`01`) in the run's mix.
- **Rollouts:** per row, a **rollout count** `n` of completions sampled at the **rollout temperature** (not
  the 0.1 deployment default), each graded by the one scorer (`../../evaluation/plan.md` §4).
- **Primary metric — `pass@1` (per-attempt success):** `c/n` for `c` passes in `n` rollouts, reported
  with a 95% CI (Wilson or Jeffreys). This is the quantity RL cares about; **do not label `c/n` as
  `pass@k`.**
- **Chance correction for bounded answer spaces.** Each row carries a per-row chance probability
  `p_chance`: `1/K` for `candidate_label` with `K` rendered candidates, `1/2` for `boolean`, `1/K` for a
  fixed enum, and `0` for open-ended/numeric/coordinate/JSON formats where a random guess is not
  meaningful. Report both raw `pass@1` and the chance-corrected rate
  `(Σc − Σn·p_chance) / (Σn·(1 − p_chance))`, with the same cluster bootstrap CI. **A single pass on a
  6–7-option row is not evidence of capability**: under `Binomial(n, p_chance)` it is consistent with
  guessing, so reachability/tiering requires the chance null to be rejected (one-sided), not just `c>0`.
  The raw 0/1 reward stays uncorrected; correction is for measurement and tier assignment.
- **Reachability:** `reach@n = (c > 0)` — whether any rollout passed. It is a screening signal, not a rate.
- **`pass@k` (optional, reported separately):** if a "solves within `k` attempts" number is wanted, use the
  unbiased estimator `1 − C(n−c, k)/C(n, k)` with `n ≫ k` (e.g. `n=32` for `k=8`) and state `n` and `k`.
  `k=n` saturates at 1 whenever `c>0` and is never reported.
- **Tiers (per row), provisional then confirmed:** screen at `n=8`; confirm at `n=16`, and `n=32` for
  rows near a boundary or entering RL/a reported tier. Use the CI, not the point estimate:
  - `mastered`: confirmed, CI lower bound ≥ 0.80 (suggested).
  - `learnable`: confirmed `0 < c < n` and not mastered; `rl-eligible` when the CI overlaps 0.25–0.75.
  - `unreachable`: only after `0/32` (or `0/64`); `0/8` is `not observed`, not unreachable.
  - `uncertain`: CI spans a boundary → oversample or exclude from RL, and record it.
  The tiers are **measured**, not derived from `difficulty_bucket`/Reasoning hop count — those are
  *priors* to stratify by and validate, not the definition.
- **Noise control:** an `n=8` screen is provisional; never report a tier from it. Apply BH/FDR across
  confirmed rows/tiers before making a tier-level claim, and always report the raw `c/n` counts.
- **Defaults:** `n=8` screen, 16 confirm, 32/64 for zeros and borderline rows; rollout temperature ≈ 1.0.
  (At a 0.25 pass rate, the all-fail rate is ~10% at `n=8` and ~1% at `n=16` — this is why the screen is
  provisional.)
- **Outputs:** `pass@1` + CI per row and per stratum (Reasoning hop count, `difficulty_bucket`, Answer
  format, task family); the **learnable/RL-eligible** pool (RL/RFT); the **not-observed/unreachable**
  list (Bridge / re-distillation); **mastered** rows (evaluation-only).

## RL (deferred, conditional)

- **GRPO with dynamic sampling** (drop all-pass/all-fail groups), RL-eligible pass-rate scheduling, sandboxed
  rollouts, full rollout logging (FT-D9).
- **Reward = the one scorer** (`../../evaluation/plan.md` §4), audited before any RL run (FT-D14).
- **RFT** (rejection-sampling SFT on the tuned policy's **own** correct agent training traces, graded by
  the Query verifier — self-distillation / STaR) is the cheaper consolidation and may replace RL at this
  scale. It is **not** teacher distillation: 02's rejection sampling keeps the **teacher's** accepted
  traces; RFT keeps the **policy's**. Both need accepted generations to exist at all.

## Stop / advance

- any confirmed `learnable` row → RL **or** RFT is indicated; a screen-only `learnable` row is not enough;
- **no** confirmed `learnable` row → the **fallback ladder**, in order: (1) **oversample** (a row at zero
  passes at `n=8` may pass at 16/32; `0/8` is not `unreachable`) and keep any accepted completion as RFT
  data; (2)
  **hint-conditioned rollouts** — a teacher, or a student that passed an easier tier, rolls out with the
  private `clue_map` / Gold query predicates as hints, then anneal the hints toward un-hinted RFT (the P2
  hint-based direction, `../system.md` Training stage 3); (3) if neither yields accepted completions,
  **record and exclude** the tier (FT-D13).
- RL is **not** indicated when no tier is confirmed `learnable`; the fallback is data generation, not RL.

## Inputs / outputs

- **In:** the LoRA adapter (04) run on **HF Transformers** (the reference runtime, FT-D23) + decoded rows (01)
  with a per-row `p_chance` (or the candidate count needed to derive it).
- **Out:** `pass@1` + CI and the chance-corrected rate per tier; the learnable/RL-eligible pool;
  optionally an RL adapter; RFT data.

## Verification

```bash
# RL-readiness gate to build (FT-D12); offline reward grading exists:
uv run pytest train_and_eval/eval/test_tool_calls.py -k reward -q
```

## Questions for the owner

- **OD-1.** Screen the **full training split** (`N_train × rollout count 8`; the first run is ~1–2k rows
  ⇒ ≈8–16k rollouts; the superseded 958-row slice gave ≈7.7k, and a 10k scale-up would give ≈80k) or a
  **stratified sample** with a fixed sample size per hop/bucket? Each rollout is one episode — several
  LLM calls in the agentic harness — so the RL-readiness gate is a **throughput job**: order
  10⁷–10⁸ output tokens depending on `N_release` and the sample, i.e. **hours to days on a small single
  GPU** and infeasible on CPU. **Measure** seconds-per-rollout on a small pilot
  (e.g. 50 rows) first, then size the run; do not assume minutes (the old gemma run was ~10 tok/s,
  launch-bound — a serving-config trap, not the checkpoint).
- **OD-2.** RL-eligible pass rate: **~0.25–0.75** (max reward variance; recommended) or any non-zero,
  non-unity pass rate?
- **OD-3.** Confirm the rollout temperature ≈ 1.0 (rollout), separate from the 0.1 accuracy runs.
  **Provisional** — verify against the RL exploration/sampling literature (research refs [21]–[23], [25])
  as a **P2** task; it only sets the reachability estimate, not any reported accuracy.
- **OD-4.** When **no** tier is `learnable`: is the fallback **hint-conditioned teacher/student rollouts**
  (then anneal the hints), with **oversampling** as the cheap first try — or a hard stop with SFT-only
  reporting (FT-D13)? Plain self-RFT cannot proceed (no accepted completions at a zero pass rate). The
  owner leans to hint-conditioned rollouts; confirm.
- **OD-5.** RFT vs GRPO at this scale — decided by the RL-readiness gate, not on paper (`../system.md` Q3).
