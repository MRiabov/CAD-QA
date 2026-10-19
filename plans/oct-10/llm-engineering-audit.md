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
| LE-7 | High | Open — minimum + post-mix gate | Mix report exists, but no per-combination minimum is computed and coverage is not re-checked after `sample + mix` | `data.md`, `system.md` §7 |
| LE-8 | High | Closed | Preservation is training support/monitoring, not a thesis target | `training.md`, `decisions.md` |
| LE-9 | High | Open — analysis plan | Per-arm CIs exist; seed variance, power/MDE, multiplicity, and a written pre-registration are still missing | `evaluation/plan.md` Qs |
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
test code; LE-7 per-combination minimum and post-mix gate; LE-9 analysis plan; LE-10 family split; LE-11
RL smoke test; LE-16 Answer-only control run. Everything else is `Closed` or `Doc-closed` with its
remaining implementation step named.

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

**Status (2026-10-19):** open. The mix report records per-hop/per-format counts, but no per-combination
minimum is computed and coverage is not re-gated after `sample + mix`.

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

**Status (2026-10-19):** open. Per-arm/paired CIs and chance-corrected rates exist; seed variance,
power/MDE, multiplicity, and a written pre-registration do not.

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
   *(Ownership done; freeze and minimum open — LE-1/LE-7.)*
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
   H2/H3 number is quoted. *(Open — LE-9.)*
7. **A recorded optimizer recipe** — the inherited optimizer/LR/schedule/batch, with resolved values and
   the effective-batch invariant in the manifest. *(Done — LE-12.)*

## Remaining next steps

- Freeze the regenerated dataset revision (LE-1) and compute the per-combination minimum + post-mix gate
  (LE-7).
- Implement the E2E/integration tests, converter, and tool-bearing masking/truncation fixture (LE-2/LE-4/LE-5).
- Write the analysis plan: seeds, variance, power/MDE, multiplicity, and a pre-registered primary comparison
  (LE-9).
- Build the BenchCAD family-disjoint split artifact/overlap check (LE-10).
- Run the scripted LFM2.5 + vLLM + TRL GRPO weight-sync/parser smoke test before any RL spend (LE-11).
- Produce the Answer-only control run from `answer_sft_rows` (LE-16).
- Record the resolved `eval_steps`/`save_steps` and the 50-row token/cost pilot in the first run manifest
  (LE-3/LE-13).

## Status addendum (2026-10-19)

Doc-level resolutions landed after the review commit (`d214850`): LE-1 (`2dd2a29`), LE-2/LE-4/LE-5 test
plan (`8ea133a`), LE-3 (cadence/checkpoint rule, `9b5931f`), LE-13/14/15 (`e5f3a71`), LE-17 (`3121830`),
LE-6 wording/claims plus LE-7 mix-report wording (LE-7 minimum still open), LE-8 (preservation supports
training/monitoring; it is not a target), LE-12 (optimizer/LR/schedule inherited from `liquid-finetune`;
resolved config recorded), and LE-18 (`pass@1` + CI; `pass@k` only for `k<n`; screen/confirm separated).
LE-4 and LE-5 now have a specified check and an explicit sequence/truncation policy, but no converter,
fixture, or test exists yet — they are **spec-closed and code-open**. The summary table is the current
status; the findings above intentionally remain the point-in-time review.
