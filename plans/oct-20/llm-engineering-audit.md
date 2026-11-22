# LLM training-engineering audit — second pass
<!-- dont-say: allow-file: dated record; findings are quoted and not rewritten -->

**Status:** active, 2026-10-20. Second-pass review of the Phase 3 fine-tuning/evaluation docs. The
first-pass review is [`../oct-10/llm-engineering-audit.md`](../oct-10/llm-engineering-audit.md)
(LE-1–LE-18); this file adds LR-1–LR-12 and their encoding status.

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
| LR-3 | Blocking → doc-closed | H2a is Reasoning vs Answer-only; Format-only is a P1 bundle; H2b/full factorial are P3. Original: the arms changed general data, task data, format data, and volume at once; H2's hypothesis did not match its arm. | `evaluation/plan.md` §5.1/§5.2; `training.md:78-80` |
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
pool disjointness. LR-1 is partially resolved: the split code is now row-weighted, and the 10k pool
re-exports as dataset split **8,498 train / 748 validation / 754 test** and pools **6,999 `sft_train` /
1,499 `rl_train` / 1,502 `eval`** (748 validation + 754 test), with a valid split audit. The remaining
LR-1 blockers are the **3/8 answer formats**, the **no-0/1-hop warmup gap** (dataset M10; hop 2 is only
457 `sft_train` rows), and the failed non-split benchmark gates, not the split sizes. LR-3 is doc-closed
for the primary claim: **H2a is Reasoning vs Answer-only** on the same general mix, task rows, and
token budget; Format-only is a secondary **bundle** control; H2b (external reasoning) and the full
factorial are **P3/optional**.

### LR-1 — The plan is written against a dataset that does not exist

`evaluation/plan.md` fixes the phase-end validation at **1,159 rows**, the final test at **708 rows**, a
**64-row** periodic subset, and a **`n >= 500`** hard tier (`plan.md:215-218,251-252,276-284`). The
regenerated release originally produced **train 9,741 / validation 54 / test 205** (pre-resplit) and only **three** answer
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

**Partial resolution (2026-10-20).** The split code now assigns row-weighted pools and derives the
dataset split: **8,498 train / 748 validation / 754 test**, with pools **6,999 `sft_train` / 1,499
`rl_train` / 1,502 `eval`** (748 validation + 754 test); `split_audit` is valid. A 64-row periodic subset
is now drawable, a ~750-row final test gives an unpaired MDE of ~7.3 pp, and the 54/205 split is stale.
The remaining blockers are the **3/8 answer formats** (the release has `candidate_label`, `coordinate`,
`text` only), the **no-0/1-hop warmup gap** (dataset M10), and the failed benchmark gates (answer entropy,
family coverage/balance, model coverage). The H2 test tier must pre-register pooled hop 3+4 (626 test
rows), because no single hop reaches 500.

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

**Fix.** Hold the general mix, task prompt set, and loss-bearing token budget constant across arms; vary
only the target content. Primary **H2a = Reasoning vs Answer-only**; secondary = vs Base and vs
Format-only (the latter is a **bundle**, not a reasoning isolation). H2b (external reasoning) and the
full factorial are **P3/optional** and not required for the thesis. Pre-register the exact rows and token
counts per arm, not only the arm names.

**Status (2026-10-20):** doc-closed for the primary claim; H2b/full factorial are P3.

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
3. Run H2a (Reasoning vs Answer-only) with the same general mix and token budget; H2b/full
   factorial are P3. (LR-3)
4. Generate a verified reasoning corpus rather than an outcome-filtered one. (LR-4, LR-9)
5. Verify the external tool-loop and format corpora. (LR-5)
6. Prove the external corpora do not overlap the benchmark. (LR-6)
7. Set the mix by token exposure. (LR-7)
8. Build a test fixture that covers the required formats. (LR-8)
9. Measure reasoning or recovery, not only exact match. (LR-10)
10. Enforce the no-CadQuery claim. (LR-11)
