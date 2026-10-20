# LLM training-engineering audit

**Status:** active, 2026-10-10; status pass 2026-10-19. Point-in-time review of the Phase 3
fine-tuning/evaluation docs under `docs/train-and-eval/`. Findings only: no design was changed by the
review, and no code was touched. Base tree is local `main` at `d214850` (the docs work is unpushed relative
to `origin/main`). The `Findings summary` table is the current status; the finding prose is the
point-in-time review.

## What this audits

The training/evaluation documentation set: `docs/train-and-eval/datasets.md`,
`docs/train-and-eval/fine-tuning/{README,requirements,training,data,system,decisions}.md`, the eight
`docs/train-and-eval/fine-tuning/pipeline/*.md` step docs, and
`docs/train-and-eval/evaluation/{plan,decisions,harness,baselines}.md`.

**Verdict.** The research framing is strong (hypotheses, priority order, contamination awareness, decision
log). The **training engineering is thin**: the docs are rich on *what to believe* and *what to cite*, and
thin on *what actually runs*. Several load-bearing training mechanics (supervised-target construction,
sequence/truncation policy, checkpoint selection, optimizer schedule, forgetting control, RL stack
feasibility) are either unspecified or rest on an unverified upstream assumption. The single largest gap is
that the dataset the entire stack is built around has no owner and no generation plan.

**Method.** Full read of the docs above. Evidence is `file:line`. Severities:

- **Blocking** — invalidates a reported number or prevents the run.
- **High** — materially degrades signal or claim validity.
- **Medium** — correctness, robustness, or internal-consistency gap.

## Findings summary

**Status authority (2026-10-19).** The `Status` column below is the current state. The finding prose is
the point-in-time review at `d214850` and is intentionally not rewritten; where prose and status disagree,
the status column wins. Resolutions are recorded under the finding and in the status addendum.

**Status key (2026-10-19).** `Closed` = the finding no longer applies. `Doc-closed` = the docs specify the
resolution; the named implementation/data/config remains. `Spec-closed / code-open` = the acceptance
test/spec exists; no code. `Open` = no resolution yet; the next action is named. `Open (P2)` = deliberately
deferred, but still unverified.

| ID | Sev (at review) | Status (2026-10-19) | Finding / resolution | Evidence |
|---|---|---|---|---|
| LE-1 | Blocking | Doc-closed — dataset freeze pending | `learn_the_cadqa_task` ownership + regeneration plan moved to `docs/dataset/`; regenerated release not yet frozen | `data.md:30-35`, `dataset/README.md` |
| LE-2 | Blocking | Spec-closed / code-open | Test plan written (5-row full-DAG E2E + per-stage integration); no test code yet | `testing.md` |
| LE-3 | Blocking | Doc-closed — config values pending | Cadence/checkpoint fixed: 64-row periodic only for epochs ≥250 steps, ≤3/phase; final phase-2 checkpoint is the thesis number | `evaluation/plan.md` §6, `04-sft.md` |
| LE-4 | Blocking | Spec-closed / code-open | `messages` is the supervised target; tool-bearing masking fixture specified; no converter/test yet | `system.md` §7, `testing.md` |
| LE-5 | Blocking | Spec-closed / code-open | 16,384-token admission, reject-not-truncate, packing off; no fixture/test yet | `04-sft.md` |
| LE-6 | High | Closed | Tier-gated inclusion replaces the no-op ordering; ladder limited to release hops `{2,3,4,5}` | `data.md` §4 |
| LE-7 | High | Doc-closed — gate implementation pending | Per-combination minima (`m_cover=1`, `m_train=8`), first-run `coverage_limited`, and a post-mix coverage gate are specified | `data.md` §3/§6, `system.md` §7, `02-teacher-sampling.md` |
| LE-8 | High | Closed | Preservation is training support/monitoring, not a thesis target | `training.md`, `decisions.md` |
| LE-9 | High | Doc-closed — freeze before final test | Analysis plan written: 3 seeds, paired McNemar/bootstrap, Holm within H2/H3, MDE table, pre-registration block | `evaluation/plan.md` §5.2 |
| LE-10 | High | Open — family split artifact | No family-level BenchCAD `code_gen`/`qa_code` split artifact or overlap command | `data.md`, `evaluation/plan.md` |
| LE-11 | High | Open (P2) — RL smoke test | vLLM 0.22 vs LFM2.5 ≥0.23 and GRPO weight-sync/parser agreement are unverified | `requirements.md` Q4, `05-rl-readiness-gate.md` |
| LE-12 | High | Closed | Optimizer/LR/schedule/effective batch inherited from `liquid-finetune`; resolved config recorded | `training.md` §5.4 |
| LE-13 | Medium | Doc-closed — pilot pending | 8k average trace and 16k admission encoded; p50/p90/cost need a ~50-row pilot | `data.md`, `training.md` |
| LE-14 | Medium | Closed | Permissive is a preference, not the built default; commercial/AGPL rows disclosed | `data.md` §5 |
| LE-15 | Medium | Closed | `messages` is authoritative; `reasoning_text`/`tool_call_text` are asserted derived views | `system.md` §7 |
| LE-16 | Medium | Doc-closed — control run pending | `answer_sft_rows` export exists; the H2 Answer-only arm now points to it | `docs/dataset/pipeline/07-exports-harbor-sft.md` D4, `evaluation/plan.md` |
| LE-17 | Medium | Closed | FT-D11 is accepted; docs and status agree | `decisions.md` |
| LE-18 | Medium | Doc-closed — gate implementation pending | `pass@1` + CI, unbiased `pass@k` only for `k<n`, screen/confirm, chance correction | `05-rl-readiness-gate.md` |

**Remaining open items (not doc-closable without code/data/measurement):** LE-1 dataset freeze; LE-2/4/5
test code; LE-10 family split; LE-11 RL smoke test; LE-16 Answer-only control run. LE-7 and LE-9 are
doc-closed with implementation/freeze pending. Everything else is `Closed` or `Doc-closed` with its
remaining implementation step named.

A **second-pass review on 2026-10-20** adds LR-1–LR-12 (blocking split/format mismatch, RL gate measured on
SFT rows, confounded H2 arms, outcome-only trace verification, and the remaining verification/contamination
gaps). It is appended as `## Second-pass review (2026-10-20)`; read it before running any paid job.

## Blocking findings

### LE-1 — The central task dataset is unowned and out of scope

`learn_the_cadqa_task` is the lever for H2/H3/H4, but its generation is explicitly excluded from the data
plan (`data.md:30-35`), the producer is "TBD" (`datasets.md:135`), and the base-stack decision that the
whole design assumes is still `proposed` (`decisions.md:120`). The data doc concedes the primary mix
"is not runnable" until that plan exists (`data.md:234`). The only runnable artifact is the first run built
from the legacy pool — currently "~300" traces with **zero `json`/`number` coverage** (`data.md:247-248`),
i.e. the `submit_workplane` (`json`) tool is never demonstrated to the model. In effect the entire training
edifice (LFM2.5 lock-in, RL-readiness gate, scorer gates) is specified around a dataset that has neither an
owner nor a schedule.

**Status (2026-10-19):** doc-closed. Ownership and the regeneration plan moved to `docs/dataset/`; the
regenerated release still needs a frozen revision before the teacher pass.

### LE-2 — No end-to-end test of our own pipeline

Every pipeline stage is `missing`/unverified (`requirements.md:13-23`). The only "pass conditions" in the
training plan are Liquid's upstream cookbook reproductions (`smoltalk`, Home Assistant;
`training.md:111-128`), which exercise the toolchain and the GPU path but never touch CAD-QA rows, the
`TrainingExample` converter, or the `submit_*` rendering. There is no tiny immutable fixture (loader →
mock teacher → converter → SFT → eval) that any change must pass. The first genuine integration test of our
pipeline is therefore the paid run, and the repo's own rule — at least one E2E test per major feature —
is unmet.

**Status (2026-10-19):** spec-closed / code-open. `testing.md` defines the 5-row full-DAG E2E and
per-stage integration tests; no test code exists yet.

### LE-3 — Checkpoint selection and eval cadence are undefined

Evaluation is specified at "baseline / periodic / phase-end / final" (`plan.md:33-39`), but the docs never
define `save_steps`, `eval_steps`, or which checkpoint *is* the thesis number. `system.md:170` says "record
pass@k per tier for every checkpoint," which is not a selection rule. Selecting the best checkpoint on the
CAD-QA held-out is exactly the held-out contamination the docs forbid elsewhere; selecting by default is
arbitrary. H2's headline number depends on this and cannot be reproduced without it.

**Resolution (2026-10-19).** Cadence and checkpoint selection are encoded in `evaluation/plan.md` §6:
periodic eval is a **64-row** subset, only when `steps_per_epoch >= 250`, at most once per epoch and
**3× per phase**; `eval_steps = save_steps = steps_per_epoch` (resolved values go in the manifest). Full
validation (**1,159 rows**) runs once at each phase end and decides phase 1→2 advancement; the test split
(**708 rows**) runs once after phase 2. The thesis checkpoint is the **final phase-2 optimizer step**
(or phase-1 final step under the phase-2 fallback), never a best-on-validation/test checkpoint; the last
two checkpoints are kept for recovery only. This rejects the proposed 128-row/50-step cadence as too
frequent. Budget guard: 8-row pilot, periodic eval ≤10% of phase wall-clock, HF `sync` at batch 1 on
24 GB, no vLLM sidecar. Status: **doc-closed, resolved config values pending the first run.**

### LE-4 — The supervised target is unspecified, and the check cannot catch the bug

The `TrainingExample` schema keeps `reasoning_text` and `tool_call_text` as separate fields
(`system.md:241-246`) while `messages` is the training artifact — the converter's obligation to render
reasoning into the **loss-bearing** assistant turn is never stated. Separately, completion-only loss is
handled by "set `assistant_only_loss: true` … verify on the smoltalk reproduction" (`training.md:418-424`;
`04-sft.md:24-27`). But smoltalk is single-turn with **no tools and no tool-role turns**, so the
`render_tool_calls` masking path — the precise Aug-2026 failure mode named in `training.md:338-346` — is
never exercised by the plan's verification. This is the highest-risk training bug in the set and the
specified check does not reach it.

**Status (2026-10-19):** spec-closed / code-open. `system.md` §7 makes `messages` the sole supervised
target and `testing.md` specifies the tool-bearing token/label fixture; the converter and fixture are
not written yet.

### LE-5 — No sequence-length or truncation policy

`training.md:228` sizes activations against `SEQ=6144`, citing `pipeline/04-sft.md`, but the current step
doc contains no sequence length — the reference is stale. Teacher traces are multi-round (up to ~10
`run_code` round-trips; `training.md:268`), so they are materially longer than a single-turn 6144-token
example. There is no `max_seq_length`, no padding/packing rule, no over-length rejection, and no statement
of what happens when a trace exceeds the window. Naive right-truncation removes the final `submit_*` call —
the only supervised target — silently. This is a data-integrity hazard, not a tuning detail.

**Status (2026-10-19):** spec-closed / code-open. `04-sft.md` sets the 16,384-token admission window,
reject-not-truncate, no right-truncation, and packing off; the fixture/test is not written yet.

## High findings

### LE-6 — The "curriculum" is a no-op, and the ladder is inconsistent

The docs repeatedly say to "order/interleave the `learn_the_cadqa_task` rows by hop count"
(`data.md:284`, `system.md:271-272`, `03-preparation.md:25`). Under TRL SFT with a shuffled single epoch,
ordering a static dataset has no effect; §4.1's advancement gate is **data inclusion**, not ordering, and
no sampler or per-hop phase is defined. The ladder as written is also unbuildable: synthesis floors at
`hop≥2`, so no release 0- or 1-hop families exist
(`docs/dataset/pipeline/04-query-synthesis-resolver.md:130-136`), and the release tiers are `{2,3,4,5}`.
A curriculum that is both a no-op and cannot be generated cannot be said to exist.

**Status (2026-10-19):** closed. `data.md` §4 now specifies **tier-gated inclusion, not within-run
ordering**, and limits the ladder to the release hops `{2,3,4,5}`.

### LE-7 — Coverage is treated as learnability

`data.md:262-264` treats "at least one agent training trace per combination" as sufficient, over a
combination space "on the order of hundreds." Across a 1,000–2,000-row first run that is ~2–10 examples per
combination — too few to establish the per-combination mapping unless transfer across combinations is
demonstrated. No per-combination minimum is computed. Worse,
the coverage gate lives at stage 02 (`02-teacher-sampling.md:21-25`) and is never re-checked after
`sample + mix` (`system.md:271-273`), so the step that actually determines what is trained can silently
destroy the coverage the gate certified.

**Status (2026-10-20):** doc-closed, gate implementation pending. `m_cover=1`, `m_train=8`, the
first-run `coverage_limited` exception, and the post-mix coverage gate are specified in `data.md` §3/§6,
`system.md` §7, and `02-teacher-sampling.md`.

### LE-8 — Capability preservation is assertion, not mechanism

`training.md:157-159` states plainly that "LoRA does not reliably prevent catastrophic forgetting," then
FT-D18 (`decisions.md:278-291`) removes the replay role and prescribes only "a diverse general mix." There
is no replay, no distillation loss, no KL anchor, and no regularization — by the docs' own cited evidence
this is the weakest available control, yet it is P0. The detection gate is a blanket "≤2 points" tolerance
on a 500–1,000-row guard (`plan.md:208-211`) with no power analysis; at that size the binomial standard
error is ~1.5 points, so the gate is dominated by noise and will "pass" a real regression.

**Resolution (2026-10-19, owner).** Capability preservation exists to support training and prevent
collapse of reasoning, and to monitor training — it is **not a target**. The general-task guard is
therefore a diagnostic/covariate, not a non-inferiority gate; the thesis reports a measured tradeoff
rather than claiming no capability loss, and no replay/KL mechanism is required. Finding closed.

### LE-9 — No statistics plan

There is no mention anywhere of confidence intervals, seed variance, significance testing, multiple-
comparison control, effect sizes, or a pre-registered primary endpoint. The H3/H4 arms
(`plan.md:162-190`) compare several training-data configurations at n≈958 rows and a noisy guard, and H4 is
a dose-response (`plan.md:176-182`); none of these is analyzable as specified. A "thesis number" without an
uncertainty statement and a comparison plan cannot support the headline claim.

**Status (2026-10-20):** doc-closed, freeze pending. `evaluation/plan.md` §5.2 specifies 3 seeds,
paired McNemar/bootstrap tests, Holm within the H2/H3 families, the MDE table/formula, and the
pre-registration block (endpoint, arms, hashes, tier, n, seeds, MDE, alpha, stopping).

### LE-10 — BenchCAD train/eval leakage is hand-waved

`data.md:195-199` and `plan.md:184-187` say to keep BenchCAD `code_gen` (training) disjoint from
`qa_code`/`edit_code` (transfer evaluation) at the family level, but `qa_code` and `code_gen` share the 106
part families, and no family-level split artifact, overlap check, or command is defined. Dedup is
"normalized hash only, no MinHash/LSH unless a measured collision appears" (`system.md:267-270`). H3 is the
peer-review gate, and its validity rests entirely on a disjointness rule that is asserted, not built.

**Status (2026-10-19):** open. No family-level `code_gen`/`qa_code` split artifact, overlap check, or
command exists; the alternative (drop `code_gen`) is stated but not decided.

### LE-11 — The RL stack is assumed, and it is the fragile part

`system.md:205-225` assumes TRL `GRPOTrainer` + vLLM rollouts "already covers the whole loop." LFM2.5 is a
**hybrid** (conv + attention) architecture, and the exact risk points — vLLM GRPO weight synchronization and
the `lfm2` tool-call parser agreement — are unaddressed. The only stage-05 verification is a stub
(`05-rl-readiness-gate.md:56-59`), and `requirements.md:57-59` already records a version conflict
(`liquid-finetune` pins `vllm==0.22.0`, LFM2 needs ≥0.23). **Checked 2026-10-19:** upstream `main` still
pins 0.22.0; the official LFM2.5 recipe says ≥0.23.0. SFT/HF eval are unaffected, and 0.22 may still load
LFM2.5 (same `Lfm2ForCausalLM` family), so this is **unverified, not proven broken** — smoke-test
async/GRPO on 0.22 before adding a separate environment. Compounding this, FT-D21 mandates one serving
engine per window while evaluation is Transformers and rollouts are vLLM — two runtimes, unaddressed. RL is
P2 and conditional, but it is presented as solved when it is a load-bearing unknown.

**Status (2026-10-19):** open (P2). The 0.22-vs-0.23 question is unverified, not proven broken; a
scripted LFM2.5 + vLLM + TRL GRPO weight-sync/parser smoke test is the gate before any RL spend.

### LE-12 — No optimizer, schedule, or effective batch

There are zero mentions of a warmup, LR scheduler, AdamW settings, or effective batch size in the entire
set. Stage 8 says "override only `model_name` and the dataset path" (`training.md:212`), and
`training.md:409` openly notes that the `liquid-finetune` snippet's `lr=2e-5` contradicts the LoRA rate
`2e-4` given in §3. At 1k–10k examples, LR and schedule are the primary controls over both learning and the
forgetting the docs are worried about; deferring them all to "cookbook defaults" for a first-time author is
the wrong axis to leave unmeasured.

**Resolution (2026-10-19, owner).** `liquid-finetune`'s `DEFAULT_SFT`/`DEFAULT_LORA` supply optimizer
(AdamW), LR, scheduler, warmup, and batch/accumulation; the plan inherits them and overrides only
`model_name`/dataset path. The snippet's `2e-5` was the full-FT rate copied onto a LoRA run — it is
removed, and the LoRA rate is inherited (`2e-4` in the documented recipe). Effective batch is the
invariant `micro_batch × grad_accum × world_size`, not a per-GPU env var: hold it constant across GPU
classes or record the GPU class as a hyperparameter; the resolved config goes in the manifest. Muon is a
P2 ablation, not a first-run default: its LR scale is not comparable to AdamW, and Muon+LoRA is not a
validated/supported path in this stack. Finding closed.

## Medium findings

### LE-13 — The budget understates multi-turn traces

The "10k examples ≈ 10–30M tokens" estimate (`data.md:260`) implies ~1–3k tokens/example, but a multi-turn
agent trace with repeated `run_code` results at the window named in `training.md:228` is far longer. The
VRAM table (`training.md:220-230`) sizes for 6144 without a long-trace tail. The teacher-cost model
(`training.md:254-278`) is careful about per-attempt pricing but budgets nothing for re-sampling after the
next contract/template rewrite — and Phase 3 is a rewrite by definition (FT-D3/FT-D12).

**Resolution (2026-10-19, partial).** `e5f3a71` relabeled the single-turn estimate, added long-tail VRAM
headroom, and budgeted one re-sampling pass; the later sequence policy sets the 16,384-token admission
window. The working assumption is now an **8k average trace** (~80M tokens per epoch for 10k rows;
~8–16M for the first run). Remaining: those figures are estimates — run a ~50-row pilot and record
p50/p90 tokens and cost per accepted trace, including every teacher call (the compactor is an extra
call), before fixing the budget. Status: **doc-closed, numeric validation pending.**

### LE-14 — "Permissive default" is not what is built

`data.md:344-350` states permissive, fully open sources are the default. Both specified mixes nonetheless
draw `run_the_tool_call_loop` from AGPL/commercial-trace corpora (`data.md:280-291`), including the first
run. The licensing rationale is sound, but the "default" description does not match the recipe and will
mislead a reader about redistribution exposure.

**Status (2026-10-19):** closed. `data.md` §5 now says permissive is a **preference**, not the built
default, and names the AGPL/commercial rows in the mix.

### LE-15 — Dual source of truth in the record

`TrainingExample` carries both `messages` and the separate `reasoning_text`/`tool_call_text` fields
(`system.md:241-246`). The converter contract never states which is authoritative or when they may diverge,
so the two can drift and the SFT target becomes ambiguous. One field should be derivable from, or
asserted-equal to, the other.

**Status (2026-10-19):** closed. `system.md` §7 makes `messages` authoritative and the two text fields
derived, audit-only views asserted equal to the assistant turn.

### LE-16 — The H2 control arm is not buildable as written

The "Answer-only" arm is "CAD-QA answers, no reasoning" (`plan.md:168`), but `learn_the_cadqa_task`'s
contract is reasoning-bearing traces (`data.md:365-366`). There is no generation config that yields
answers without reasoning, so the control that isolates reasoning content from supervision format cannot be
produced from the dataset as specified.

**Status (2026-10-19):** doc-closed. `dataset/pipeline/07-exports-harbor-sft.md` D4 already provides an
`answer_sft_rows` export; the H2 arm now points to it. Producing the control run remains.

### LE-17 — Decision statuses lag the design

FT-D11, the base-stack decision the entire pipeline assumes, is still `proposed — most likely, not yet
accepted` (`decisions.md:120`), while every Phase-3 doc is written as if it is settled. `requirements.md`
confirms there is "no live box" and that determinism/seeds are unimplemented (`requirements.md:31,40-41`).
Readers cannot tell which choices are commitments and which are hypotheses.

**Status (2026-10-19):** closed. FT-D11 is accepted (2026-10-10); the Phase-3 docs and the decision log
now agree.

### LE-18 — `pass@k` is used loosely and without uncertainty

The RL-readiness gate samples a rollout count and reports a pass rate (`05-rl-readiness-gate.md:21-23`);
that is an empirical pass@n, not the unbiased pass@k estimator, and no confidence interval or screening-vs-
confirming correction is applied. With the all-fail bound quoted at ~10% for count 8, per-row tier
assignments will flip between runs; the gate's downstream RL/RFT decision inherits that noise unquantified.

**Resolution (2026-10-19).** The gate's primary metric is now `pass@1 = c/n` with a 95% Wilson/Jeffreys
CI, not `c/n` relabeled as `pass@k`. `pass@k` is reported only with the unbiased estimator
`1 − C(n−c,k)/C(n,k)` and `n ≫ k`; `k=n` is never reported. `n=8` is a provisional screen; tiers require
`n=16/32` confirmation, `0/8` is `not observed` rather than `unreachable`, and BH/FDR applies across
confirmed tiers. **Chance correction:** bounded answers (`candidate_label`, `boolean`, fixed enums) report
a `p_chance`-corrected rate and tier assignment tests `c ~ Binomial(n, p_chance)`; one lucky guess on a
6–7-option row is not reachable evidence. Per-row tests are underpowered, so the RL go/no-go uses the
**pooled tier-level** corrected rate; 8 is a screen, and categorical rows confirm at 32/64 with the
documented α=0.05 `c` thresholds. Status: **doc-closed, gate implementation pending.**

## What "adequate" would minimally require

1. **An owned generator** for `learn_the_cadqa_task`, with a coverage gate that runs **after** `sample + mix`
   and a computed per-combination minimum — or an explicit decision to accept a coverage-limited first run.
   *(Ownership + minimum done; dataset freeze open — LE-1; gate implementation pending — LE-7.)*
2. **A 5-row E2E fixture** (mock teacher, real loader and converter) committed as a test, asserting
   tool-call masking (reasoning supervised, tool responses masked) and non-truncated targets.
   *(Specified; code open — LE-2/LE-4/LE-5.)*
3. **An explicit sequence policy:** `max_seq_length`, packing/padding, and an over-length rule that never
   drops the final `submit_*` call. *(Specified; code open — LE-5.)*
4. **A named checkpoint-selection rule** and a concrete eval/save cadence, chosen so the thesis number is
   not selected on its own held-out set. *(Done — LE-3.)*
5. **A specialization-tradeoff monitor** — paired CIs and reported deltas on the general-task guard;
   diagnostic, not a non-inferiority gate. *(Done — LE-8.)*
6. **An analysis plan** — per-arm CIs, seed variance, and a pre-registered primary comparison — before any
   H2/H3 number is quoted. *(Done — LE-9; freeze at first run.)*
7. **A recorded optimizer recipe** — the inherited optimizer/LR/schedule/batch, with resolved values and
   the effective-batch invariant in the manifest. *(Done — LE-12.)*

## Remaining next steps

- Freeze the regenerated dataset revision (LE-1) and implement the per-combination/post-mix coverage gate
  (LE-7).
- Implement the E2E/integration tests, converter, and tool-bearing masking/truncation fixture (LE-2/LE-4/LE-5).
- Freeze the pre-registration block (endpoint, hashes, tier, n, seeds, MDE) before the final test (LE-9).
- Build the BenchCAD family-disjoint split artifact/overlap check (LE-10).
- Run the scripted LFM2.5 + vLLM + TRL GRPO weight-sync/parser smoke test before any RL spend (LE-11).
- Produce the Answer-only control run from `answer_sft_rows` (LE-16).
- Record the resolved `eval_steps`/`save_steps` and the 50-row token/cost pilot in the first run manifest
  (LE-3/LE-13).

## Status addendum (2026-10-19)

Doc-level resolutions landed after the review commit (`d214850`): LE-1 (`2dd2a29`), LE-2/LE-4/LE-5 test
plan (`8ea133a`), LE-3 (cadence/checkpoint rule, `9b5931f`), LE-13/14/15 (`e5f3a71`), LE-17 (`3121830`),
LE-6 wording/claims plus LE-7 coverage minima/post-mix gate and LE-9 analysis plan (2026-10-20), LE-8
(preservation supports training/monitoring; it is not a target), LE-12 (optimizer/LR/schedule inherited
from `liquid-finetune`; resolved config recorded), and LE-18 (`pass@1` + CI; `pass@k` only for `k<n`;
screen/confirm separated). LE-4 and LE-5 now have a specified check and an explicit sequence/truncation
policy, but no converter, fixture, or test exists yet — they are **spec-closed and code-open**. The
summary table is the current status; the findings above intentionally remain the point-in-time review.

## Second-pass review (2026-10-20)

**Scope.** Re-read the full `docs/train-and-eval/` set (21 docs) against the regenerated dataset record
(`docs/experiments/2026-10-19-cadqa-regen-1300.md`) and the dataset split decision (`docs/dataset/decisions.md`
DD-12). This pass asks a narrower question than LE-1–18: **after the doc closures, what would a first-time
fine-tuner still get wrong?** Findings are ordered by whether they invalidate a reported number or only
degrade it. A finding that extends an open LE says so.

**Verdict.** The docs now specify the *shape* of a careful pipeline, but several load-bearing quantities are
still fictional or unverified: the dataset the plan is written against does not match the regenerated
release, the RL gate measures the SFT training rows, the H2/H3 arms are confounded, and the "verified" data
roles are not verifiable as written. These are not polish items; each changes what the thesis number means.

| ID | Sev | Finding | Evidence |
|---|---|---|---|
| LR-1 | Blocking | The plan's split sizes, format coverage, and power analysis do not match the actual regenerated release. | `evaluation/plan.md` §5.2/§6; `docs/experiments/2026-10-19-cadqa-regen-1300.md` |
| LR-2 | Blocking | The RL-readiness gate is measured on the SFT training rows, so it measures memorization, not reachability. | `pipeline/05-rl-readiness-gate.md:14`; `pipeline/02-teacher-sampling.md:15-18` |
| LR-3 | Blocking | The H2/H3 arms change general data, task data, format data, and volume at once; H2's stated hypothesis does not match its primary arm. | `evaluation/plan.md:166-175`; `training.md:78-80` |
| LR-4 | Blocking | Teacher rejection sampling verifies only the final answer; wrong intermediate reasoning/tool calls enter SFT (and RFT). | `pipeline/02-teacher-sampling.md:22`; `system.md:135-137` |
| LR-5 | High | The "verified" external data roles are not verifiable as written: tool-loop traces need their own tool environments, and the format corpus is generic function calling, not our `submit_*` schema. | `datasets.md:39-43`; `data.md:55,68-71,471-472` |
| LR-6 | High | Contamination is not closed for the source corpus (cadevolve), BenchCAD families, or the general eval guard. | `data.md:186-188`; `datasets.md:120`; `docs/dataset/decisions.md:138-148`; extends LE-10 |
| LR-7 | High | Mix weights are row-based, not token-based; task traces are much longer, so the declared 30/50% is not the token or compute share. | `data.md:219-222`; `system.md:292` |
| LR-8 | High | The 5-row E2E fixture cannot cover the 8 required Answer formats or pass the coverage gate. | `testing.md:70-72,123,126` |
| LR-9 | High | `Bridge` and the teacher protocol are undefined, yet both are on the critical path. | `system.md:91-97`; `pipeline/02-teacher-sampling.md` (whole); `05:77-83` |
| LR-10 | Medium-High | SFT/RFT use only success traces and the primary endpoint is exact match, so nothing measures recovery or reasoning. | `pipeline/02-teacher-sampling.md:22`; `05:69-72`; `evaluation/plan.md:215-230` |
| LR-11 | Medium | The benchmark's "no CadQuery access" claim rests on a guard the docs call "not a security boundary." | `evaluation/plan.md:73-75`; `harness.md:89-96`; D-E3 |
| LR-12 | Medium | RL is a sketch: no GRPO group size, KL/clip, rollout budget, or multi-turn reward aggregation. | `system.md:118-122`; `05:66-72`; extends LE-11 |

**Encoding status (2026-10-20).** LR-2's split design is now encoded: `data.md` §5 defines the three-way
pools (`sft_train` / `rl_train` / `eval`, target ~70/15/15), `05-rl-readiness-gate.md` measures the gate
on `rl_train` and reports the memorization gap, `system.md` §7 adds `DataPool`, and `testing.md` asserts
pool disjointness. LR-1 is partially encoded: the docs now name the 70/15/15 target and the current
54/205 release's non-compliance, but the actual frozen split/re-split remains open.

### LR-1 — The plan is written against a dataset that does not exist

`evaluation/plan.md` fixes the phase-end validation at **1,159 rows**, the final test at **708 rows**, a
**64-row** periodic subset, and a **`n >= 500`** hard tier (`plan.md:215-218,251-252,276-284`). The
regenerated release actually produced **train 9,741 / validation 54 / test 205** and only **three** answer
formats (`candidate_label`, `coordinate`, `text`) — not the eight the loader and test fixture require
(`docs/experiments/2026-10-19-cadqa-regen-1300.md:96-101`). It also **fails** the benchmark release gates:
distinct model coverage 980/1,000, prompt-family balance 10.43% > 10%, answer entropy 7.50 < 8.0
(structurally infeasible at this format mix), cross-feature coverage 488/500, and 42/59 intended families
(`...regen-1300.md:127-145`).

Consequences: the periodic 64-row subset cannot be drawn from a 54-row validation split; the phase-end
"full validation" is 54 rows; the final test is 205 rows, so the unpaired MDE is roughly **14 pp**, not
7.5 pp; the plan's own `n >= 500` tier rule cannot be satisfied; and the 5 missing answer formats cannot be
covered by `m_cover=1`. The H2 thesis number would be computed on an underpowered, non-benchmark release.
The docs currently say only that the dataset "is to be regenerated" (`data.md:33-35`); they do not record
that the regenerated release exists and is incompatible with the plan.

**Fix.** Either freeze a split with a real test set (>=500 hard-tier test rows) and all required answer
formats, or pre-register a smaller, honest claim and a larger MDE. Replace every hardcoded 1,159/708/64/500
number with values read from the frozen `split_manifest.json`, and add a test that the plan and the manifest
agree. Do not run the H2 test on a 205-row split and call it the thesis number.

### LR-2 — The RL-readiness gate measures the rows SFT trained on

`05-rl-readiness-gate.md:14` defines the population as "the train rows (`01`) in the run's mix." But the
`learn_the_cadqa_task` SFT data is teacher traces sampled from those same rows
(`02-teacher-sampling.md:15-18`). After SFT, `pass@1` on those rows measures how well the policy memorized
the teacher's traces, not whether the tier is learnable. The gate can therefore report "mastered" for a
memorized row (and stop RL), or "learnable" from partial memorization; neither is the reachability signal
the system doc claims (`system.md:99-116`). This is inconsistent with the data advancement gate, which
correctly uses a **held-out** pass rate (`data.md:327-348`).

**Fix.** Hold out an `rl_train` pool per hop/family that was not used for SFT; measure the gate and run
RL/RFT on that pool. Keep `eval` separate for the thesis number. Report both "seen" (`sft_train` sample) and
"unseen" (`rl_train`) pass@1; the difference is the memorization gap.

**Resolution (2026-10-20, doc).** Encoded as FT-D24 / D-E10 and the three-way `sft_train` / `rl_train` /
`eval` split (`data.md` §5); the gate population is `rl_train`, the gate reports the memorization gap, and
the split is asserted in `testing.md`. The actual frozen split remains to be produced.

### LR-3 — The H2/H3 arms are confounded, and H2's hypothesis does not match its arm

H2 is stated as "an external reasoning-distillation + agent training trace mix raises CAD-QA held-out
accuracy beyond format-only and answer-only" (`training.md:78-80`). The primary arm is "CAD-QA reasoning |
release-hop tiers of `learn_the_cadqa_task`" (`plan.md:166-175`), i.e. our task traces only, with no external
reasoning mix. Meanwhile "Format-only" is `emit_our_tool_call_format` + the general tasks, and "Answer-only"
is `answer_sft_rows` with no reasoning. The three arms differ in **general data, task data, format data,
row count, and token count** at the same time, and only H4 specifies matched compute
(`plan.md:192-198`). A difference between them cannot be attributed to reasoning.

**Fix.** Hold the general mix constant across arms; vary only the CAD-QA/reasoning component; match total
tokens or optimizer steps; define the primary treatment as the full primary mix vs Format-only (or add a
"General + CAD-QA reasoning" arm). Pre-register the exact rows and token counts per arm, not only the arm
names.

### LR-4 — Teacher traces are accepted on the final answer only

`02-teacher-sampling.md:22` keeps a trace if it "must contain a tool call `tool_call_matches` accepts
against the row's gold." In a multi-turn trace (up to 10 `run_code` round-trips, `04-sft.md:61`), the
intermediate `run_code` outputs and reasoning are not checked. A teacher can run wrong code, read a wrong
intermediate value, and still land on the gold answer by a later guess or correction; that trace enters
SFT as if it were a correct reasoning path. Step-level verification is explicitly P2 (`system.md:135-137`).
The same problem applies to RFT, which keeps the policy's own correct rollouts (`05:69-72`).

For an SFT imitation target this is a data-quality issue; for RFT/GRPO it is a reward-hacking vector. It
also undercuts the "reasoning" claim: the corpus is **outcome-filtered**, not process-verified.

**Fix.** Before SFT admission, re-execute every `run_code` call and compare the observed result with the
trace; reject traces whose final answer does not follow from the recorded tool results. At minimum, label
the corpus `outcome_filtered` and do not describe it as verified reasoning. For RFT, require the process
check before the trace becomes a target.

### LR-5 — The external data roles are not "verified" as the table claims

`datasets.md:39-43` assigns each role an adopted environment. Two rows do not hold up:

- `run_the_tool_call_loop` says "re-run the tool calls; check the final answer" in "our tool sandbox
  (`run_code`; Modal Sandbox)." The adopted corpora (`OpenThoughts-Agent`, Fable, Open-SWE) call their own
  tools (shell, file edit, browser, etc.), not our `run_code`. You cannot re-run those calls in our sandbox,
  and the datasets do not ship their tool environments. `data.md:68-71` says verification adopts the
  upstream environment, which is absent here. The role is therefore **unverified**, not execution-verified.
- `emit_our_tool_call_format` is described as teaching our `submit_*` calls (`data.md:55`), but the adopted
  corpora are ToolACE/xLAM/Hermes with arbitrary functions. `datasets.md:39` says "generic calls
  re-targeted," but no mapping is defined, and `data.md:471-472` (Q3) admits the open question. H1's
  Format-only arm may therefore never teach our tool names or arguments.

**Fix.** For tool loops, either pick corpora whose environments ship and adopt them, or verify only the
final answer and mark the role as schema-only. For the format role, define the re-targeting mapping (or
synthesize a `submit_*` corpus from CAD-QA rows) and add a test that Format-only emits our tools.

### LR-6 — Contamination is not closed for the source corpus or the general guard

`data.md:186-188` says `expose_cadquery_programs` must not leak the CAD-QA held-out programs **or their
generating corpus**. `datasets.md:120` then lists `kulibinai/cadevolve` (2M CadQuery programs) as a
candidate, and the regenerated dataset is built from `current_cadevolve...` sources
(`docs/experiments/2026-10-19-cadqa-regen-1300.md:12-19`). The group-safe split (DD-12) groups CAD-QA rows,
not external corpora, so it does not prevent an external training row from sharing a source program or
family with an evaluation row. BenchCAD `code_gen`/`qa_code` has the same problem and is still open
(LE-10). Separately, the general math/code guard is not decontaminated against OpenThoughts/OpenR1/
Bespoke, so a "no regression" result can be contamination rather than retention.

**Fix.** Exclude every source program used by any CAD-QA split (not just held-out) from external training,
or drop cadevolve. Build the family-level BenchCAD split artifact. Add a test that no external training row
shares a source hash, program hash, or protected family with any evaluation row, and decontaminate the
general eval against every training corpus.

### LR-7 — Mix weights are row-based, not token-based

`data.md:219-222` defines the mixes as 70/30 and 50/50 by role, and `system.md:292` records "counts, token
totals, role weights." Nothing makes the weights token-weighted. Teacher traces are multi-turn and much
longer than general QA rows (the budget assumes an **8k average trace**, `data.md:263-265`), so a 50% task
row share can be most of the tokens and compute. The model is trained on tokens, not rows; the declared mix
is not the exposure the model sees.

**Fix.** Define the mix in tokens (or in supervised/loss-bearing tokens), report both row and token shares,
and set the role weights by tokens. Re-run the post-mix coverage gate on the token-weighted set.

### LR-8 — The 5-row E2E fixture cannot do what the test plan asks

`testing.md:70-72` requires a **5-row** fixture "covering at least one row per Answer format —
`candidate_label`, `coordinate`, `text`, `number`, `integer`, `boolean`, `bbox`, and `json`." That is eight
formats in five rows. `testing.md:123` then asserts "the 5 rows' Answer formats all appear (incl.
`submit_workplane`)," and `testing.md:126` requires the coverage gate to pass; a 5-row set cannot meet
`m_cover=1` across hundreds of combinations. The E2E test is arithmetically impossible as written.

**Fix.** Use at least 8 rows (one per format) for the format/masking E2E, or split the fixture into a
5-row smoke plus an 8-row format fixture. Run the coverage gate on a synthetic coverage fixture, not the
5-row one, and allow `coverage_limited` explicitly in the E2E.

### LR-9 — `Bridge` and the teacher protocol are undefined

`Bridge` is the designated fix for hard teacher traces that the student cannot imitate
(`system.md:91-97`), the fallback when no tier is learnable (`05:77-83`), and a dependency of the data
advancement gate (`data.md:337-348`). No doc defines the transformation, its acceptance check, or its
effect on the target distribution. Separately, `02-teacher-sampling.md` is 76 lines and does not specify
the teacher prompt/system message, the tool schema, the multi-turn loop, how `run_code` is executed and fed
back, compaction, max rounds, temperature, or how the teacher's tool calls are parsed and re-rendered into
LFM2.5 tokens; `02:75-76` leaves temperature and attempts open. This is the core data-generation path.

**Fix.** Specify the teacher request/response contract and the full loop, including the tool schema and
re-rendering, and add a 50-row pilot that records success, tokens, cost, and rejection reasons. Specify
Bridge as an algorithm (for example hint-prefix decomposition or step-wise decomposition) with an
acceptance test and an A/B; otherwise remove it from the critical path and report the hard tier as
unlearned.

### LR-10 — No failure/repair data, and no process metric

SFT admits only teacher successes (`02:22`); RFT admits only the policy's own successes (`05:69-72`). An
agentic policy's dominant failures are malformed tool calls, execution errors, and wrong intermediate
values; training only on successes leaves it unable to recover and pushes it off-distribution at inference.
At the same time, the primary H2 endpoint is exact match (`plan.md:215-230`), so a correct answer via a
lucky guess or wrong intermediate steps counts as success; chance correction covers only bounded formats.
Step-level verification is P2 (`system.md:135-137`). The docs call the task "reasoning" but measure only
answers.

**Fix.** Add a small, verified failure/repair set (teacher corrections of its own failed attempts, or
filtered failed rollouts with the corrected next step), or at least measure tool-error recovery. Add a
pre-registered process metric (tool-call validity, execution-error rate, final-answer-follows-tool-results
rate, reasoning length) beside exact match; do not claim "reasoning" from exact match alone.

### LR-11 — The no-CadQuery claim rests on a non-boundary

`plan.md:73-75` and `harness.md:89-96` describe `run_code` as an "accidental-misuse guard, not a security
boundary" (D-E3). The benchmark's central claim is that the model has **no access to a CAD kernel**; if
LLM-generated code can escape the subprocess, the claim is unverified. The trust audit TA-B1 is still open.
This is not only a security concern; it is a validity concern for every reported number.

**Fix.** For reported runs, harden the sandbox (container/namespace/seccomp, no network, no `ctypes`, no
file I/O) and run an adversarial escape test; or pre-register the weaker threat model and state that the
no-CadQuery claim is conditional on accidental-misuse only. Do not report it as an enforced boundary.

### LR-12 — RL is still a sketch

`system.md:118-122` says GRPO with dynamic sampling; `05:66-72` lists the pieces but not group size,
prompts per step, KL coefficient, clip range, rollout budget, reward aggregation across multi-turn
episodes, or how the one scorer handles intermediate turns. RL is conditional and P2, so this is not a
thesis blocker, but the docs present it as designed. This extends LE-11.

**Fix.** Add a GRPO config spec and a scripted LFM2.5 + vLLM + TRL smoke test before any RL spend; include
the multi-turn reward aggregation and the group-size/batch arithmetic.

### What a first-time fine-tuner still cannot do from these docs

1. Freeze a dataset with enough test rows and all Answer formats to test H2. (LR-1)
2. Measure reachability on data the model has not seen. (LR-2)
3. Run an H2 arm comparison that isolates reasoning. (LR-3)
4. Generate a verified reasoning corpus rather than an outcome-filtered one. (LR-4, LR-9)
5. Verify the external tool-loop and format corpora. (LR-5)
6. Prove the external corpora do not overlap the benchmark. (LR-6)
7. Set the mix by token exposure. (LR-7)
8. Build a test fixture that covers the required formats. (LR-8)
9. Measure reasoning or recovery, not only exact match. (LR-10)
10. Enforce the no-CadQuery claim. (LR-11)
