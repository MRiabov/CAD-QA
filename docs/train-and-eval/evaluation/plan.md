# Evaluation

**Status:** active, 2026-10-09. The evaluation companion to `../fine-tuning/training.md` (training)
and `../fine-tuning/data.md` (data). Evaluation is **not fine-tuning-specific** — the same harness,
scorer, and baselines score the base LLM model, the tuned LLM model, and the cost-effective external
models through the **same local tool-call harness** (Harbor is a deferred P2 path, D-E9).

**This doc owns — the shared evaluation base:** the LLM harness and its modes, the tool-call and
answer contract, the scorer, the evaluation-dataset procedure, grading reconciliation, judge independence,
baselines, and evaluation P0/P1/P2.

**Why it is its own doc.** The evaluation concern is *not* a sub-part of training. It is the shared
dependency that (a) scores the final thesis number, (b) generates the teacher traces through
rejection sampling (the data doc's `learn_the_cadqa_task`), and (c) would supply the reward if RL is run.
Training is the extra step that adds gradients and data on top of this base; evaluation adds none.
Single-sourcing the scorer is what makes the thesis number mean anything.

**Shared interfaces, single-sourced:**

- **Format contract** (Liquid `messages` SFT set, and the native tool-call tokens) — owned by
  `../fine-tuning/training.md`.
- **`TrainingExample` + converter** — owned by `../fine-tuning/system.md`.
- **Evaluation-dataset procedure** — owned here; the dataset rows are produced and held by the data doc.
- **H1/H2** — owned by the architecture doc; the mixes they test are defined by the data doc.

**Related docs.** `harness.md` and `baselines.md` (current
descriptive docs); `../fine-tuning/decisions.md`; `../../../plans/oct-8/trust-audit.md`
(Phase 0 audit units TA-A*, TA-C*); `../../PRD.md` (evaluation contract).

---

## 1. What "evaluation" means here

**Evaluation is the set of datasets that serve H1–H4.** Each is an **evaluation dataset** with a
dataset role (`../datasets.md`), composed across Difficulty tiers. Each is run
at four points in the training pipeline: **baseline** (the untrained instruct base LLM model — the
floor), **periodic** (during a phase, on a subset), **phase-end** (end of a phase, more extensive),
and **final** (after the last phase, the complete immutable thesis number). All are hard-excluded from
training (§6).

Run an LLM model over CAD-QA dataset rows and score **exact structured answers**
under a switchable compute mode; the primary mode gives no access to CadQuery. The evaluation harness is the whole chain:
LLM model → chat template → tool declarations → generation loop → tool execution → tool-call parser →
scorer. Training and evaluation differ only in what they do with the output: training adds a
gradient update; evaluation does not.

**Tools are shared with training.** The `submit_*` tools, the `run_code` compute tool, the
`[answer contract]` suffix, and the Answer format → tool mapping are the same interface the training
data uses. This is the sense in which "eval == training tool calls": the tool-call/harness layer is
common. The difference is at the objective (see the architecture doc, §1: SFT scores only to
*admit* an agent training trace and trains by imitation; RL would score as a reward).

**Two execution environments (D-E2).** The local harness speaks the native tool-call protocol and
grades with `tool_calls.py::tool_call_matches`; Harbor runs an external coding agent that writes
`/app/answer.json|txt` and grades with `grading/grade.py::grade_public_private`. They share the
CAD-QA dataset row contract and the exact-answer principle but **do not share a grader
implementation** — a recorded defect (see §4). **Harbor is deferred to P2** (D-E9): training and
evaluation share the local tool-call harness, and external baselines run through it too.

---

## 2. LLM harness modes

An LLM harness mode is which compute tools the LLM model gets. The `numpy` and `no_tools` modes give
no access to CadQuery: no kernel, no network. Detail and status: `harness.md`.

- **`numpy` (primary, P0).** Submit tools plus the sandboxed `run_code` (Python + NumPy + `math`).
  This mode gates the thesis claims.
- **`no_tools` (P2).** Submit tools only; arithmetic internal. Strict-reasoning upper bound.
- **`cadquery` (P2, unimplemented).** Full CadQuery kernel; one correct call suffices. Reserved
  for the RL Training stage; `tools_for_mode` raises `NotImplementedError`.

The `run_code` execution path is `train_and_eval/run_code_sandbox.py` (`python -I -B`), an
**accidental-misuse guard, not a security boundary** (D-E3). Its isolation remains `[unverified]`
(trust-audit TA-B1).

---

## 3. Tool-call and answer contract

- **The `[answer contract]` suffix** tells the LLM model to end with the matching `submit_*` call.
- **One submit tool per Answer format** (`train_and_eval/tool_calls.py::FORMAT_TO_TOOL`); `json` is
  specifically the CadQuery workplane tool, not generic JSON (FT-D4).
- **The native tool-call spelling is base-specific.** The evaluation harness must be re-pointed at
  the chosen base's tokens: for LFM2.5, `<|tool_call_start|>`/`<|tool_call_end|>` with Pythonic
  calls by default. The gemma `<|tool_call>` spelling does not transfer (FT-D3;
  `../../development-context.md` "Tool-call and answer-submission format churn"). This is why
  the harness, not just the data, must change when the base changes.

---

## 4. The scorer — and the one-scorer rule

The repo currently has **three** scoring implementations:

| Scorer | Used by | Decision rule |
|---|---|---|
| `grading/grade.py::exact_match` (+ `grading/parse.py::parse_answer`) | Harbor, dataset CLI (`cadqa evaluation`, `experiment.py`) | parse by Answer format, then `gold == predicted`; `coordinate` rounded to 6 dp; `number` plain `float`; `boolean` handled |
| `tool_calls.py::tool_call_matches` | local harness, teacher rejection sampling | exact strings/ints, `1e-3` relative floats, `text` tolerates float formatting; no `boolean` entry |
| `reward_cadqa.py::reward_cadqa` | GRPO | different fallback parser; `text` uses substring presence |

**Rule (proposed, P0): one scorer.** Evaluation, teacher rejection sampling, and any future reward
must share a single verified scorer, or the thesis number and the training signal measure different
things. Reconciling them is trust-audit **TA-A3**. `grading/parse.py` already covers the `boolean`
Answer format that the typed contract omits — the union is the target.

**Why this outranks cleanup (2026).** In RLVR the Query verifier *is* the objective, so a noisy or
divergent scorer is optimized, not merely mis-counted. Query verifier audits find self-agreement as low
as 53.8% and two configurations of the same library disagreeing on 49.9% of pairs ([24]); the
numeric/coordinate formats need an explicit equivalent-answer (metamorphic) test. See
`../fine-tuning/system.md` §4 and FT-D14.

**Oracle is not correctness.** The oracle key path returning 1.0 proves the public/private merge
and parser accept the gold encoding; it does **not** establish grader correctness on wrong answers
(D-B2; TA-A2). A near-miss/formatting-variant fixture is required.

---

## 5. Evaluation procedure

- **Held-out rows.** Evaluate on an immutable, group-safe held-out slice only (never a Mixed training dataset).
- **Metrics.** Accuracy; invalid-output rate (parse errors); missing-response rate; accuracy by
  Reasoning hop count, Answer format, and LLM harness mode; reasoning length; calibration when
  confidence is requested; and **`pass@1` with a CI per prompt/tier**, plus a chance-corrected rate for
  bounded answer spaces (`p_chance` per row: `1/K` for `candidate_label`/fixed enums, `1/2` for
  `boolean`, `0` otherwise). The RL go/no-go uses the **pooled tier-level** corrected rate; per-row
  chance tests only decide which rows need confirmation. Report `pass@k` only for `k < n` with the
  unbiased estimator; `c/n` is not `pass@k`.
  (`../fine-tuning/system.md` §3).
- **Judge independence.** No LLM model in the trusted grading path (DD-03). Grading is exact-match
  code; the teacher only produces training traces, never evaluated answers.
- **Public/private hygiene.** `grading/no_cadquery_access.py::no_cadquery_access_request_audit` fails on any
  hidden-field leak, incomplete request coverage, or Answer format disagreement.

### 5.1 External transfer (H3)

The internal held-out slice cannot show that the dataset is useful; that needs transfer to
**existing, credible** external benchmarks. A benchmark counts only if it is **independent** of us,
**adopted** (a publication or a leaderboard, ideally cited by other work), **deterministic** (no LLM
judge), **reachable** by the evaluated LLM model, **construct-matched** (comprehension/reasoning,
text-in for a text-only base LLM model), and **unsaturated**.

Two rules:

- **No subset-shopping.** The headline is the benchmark's **official full split and official
  metric**; spatial-axis, family, and Reasoning-hop breakdowns are diagnostics, not a hand-picked
  result.
- **Freshness.** No external gap is quoted without a current re-run. `GeoGramBench` (2025) and
  `QueryCAD` (2024) gaps are `[stale — verify or drop]`.

**Suite by role** (comprehension is the means; generation and defect prevention are the end):

| Role | Benchmark | In → output | Modality | Tier |
|---|---|---|---|---|
| Means | BenchCAD `qa_code` (`../../research/2026-benchcad.md`, ref [33]) | CadQuery program + numeric question → number | text-in | **P0** |
| End | BenchCAD `edit_code` T4/T5 | instruction + program → edited program | code-in | P1 |
| End | `Text2CAD-Bench` (arXiv:2605.18430) | text → CadQuery program | text-in | P1, reachability-gated |
| End / defect | `Text-to-CadQuery` (arXiv:2505.06507); `CAD-Editor` (ICML 2025) | text → CadQuery program; text edit | text-in | P1 |
| Defect | `Text2CAD-Bench` Invalidity Rate; BenchCAD `exec%` | — | text-in | P1 |
| Motivation only | EngineerBench (ours) | — | — | not evidence |

- **Not targets:** Vision2Code, Vision QA, and BenchCAD 2.0 assembly/PCB (image/drawing-in, agentic);
  `CADBench`, `cadrille`, `CAD-Recode` (image/point-cloud → need a multimodal LLM model);
  `MechReason` (multi-image multi-hop) and `CADWorld` (FreeCAD computer-use) are credible but
  wrong-modality context.
- **Arms (hold base and recipe fixed; vary only training data):**

| Arm | Training data | Isolates |
|---|---|---|
| Base | none | floor; pretraining-contamination proxy |
| Format-only | `emit_our_tool_call_format` + the general tasks | H1 format compliance |
| Answer-only | CAD-QA answers, no reasoning | supervision format vs reasoning content |
| CAD-QA reasoning | release-hop tiers of `learn_the_cadqa_task` | H2 capability |
| Full primary (optional) | the full Mixed training dataset | external reasoning support |
| General-only (H4 counter-arm) | the full general mix **without** `learn_the_cadqa_task` | isolates CAD-QA supervision from general capability (H4) |

- **Tier selection (exploratory, before confirmation).** On a group-safe **selection batch** from the
  generated pool (first-run or scale-up), measure base and teacher accuracy across hops `3,4,5,6–10`, rows per tier,
  teacher acceptance, and admitted-trace rate at 16,384 tokens. Choose the highest tier satisfying
  teacher ≥ `[to measure]`, base ≤ `[to measure]`, `n` ≥ `[to measure]`, and admitted traces; freeze the
  tier before confirmation. A fresh, family-disjoint **confirmation batch** supplies the thesis number.
  These values are filled after the pilot, not before.
- **Primary result (P0, H2).** CAD-QA reasoning > Base, Format-only, and Answer-only on the chosen
  CAD-QA hard tier, reported with a paired CI. This is the instrument result; it is not conditioned on
  external transfer.
- **Transfer result (P1, H3).** The same tuned arm improves on BenchCAD `qa_code` (official split)
  relative to Base / Format-only / Answer-only, reported in percentage points with a paired CI;
  `edit_code` corroborates. A null transfer is reported as a finding, not hidden.
- **Stretch (P2).** Under the identical harness and slice, test whether the tuned model surpasses its
  teacher (`deepseek-v4.1-flash`; name any additional teacher models explicitly). Exploratory, with a
  CI — not a pre-registered gate.
- **H4 (means → end).** Test whether the CAD-QA pass rate tracks external transfer: a dose-response
  swept over `learn_the_cadqa_task` volume (0.5k→10k) or over checkpoints, measuring the CAD-QA pass
  rate and the external score at each point. Controls: fixed recipe and **matched compute**; the
  `preserve_general_math_and_code_reasoning` evaluation dataset as a covariate (transfer is claimed only if the external score tracks the CAD-QA
  pass rate *at equal general capability*); and a **general-only counter-arm** (the same mix without
  `learn_the_cadqa_task`). RL, where used, is the means to extend the sweep to harder tiers
  (`../fine-tuning/system.md` §3).
- **Preconditions (pre-registered):** reachability pilot per target (the base LLM model must be
  low-but-nonzero; a zero floor yields no signal, a high floor means saturated); format-adaptation
  control (BenchCAD wants a JSON array of numbers — report invalid-output rate); contamination audit
  (exclude every external benchmark's families from every training arm; dedup CAD-QA programs against
  them).
- **Peer-review stake (P1 transfer).** Without a measured gain on a credible external benchmark the
  dataset-usefulness claim rests on an internal split and does not withstand review. A null transfer
  is reported as a finding (comprehension supervision is task-local), not hidden.

---

## 6. Evaluation datasets

The datasets that serve H1–H4 (§5.1). The architecture doc owns the training mechanics; the data
doc holds the rows. Each is composed across Difficulty tiers, hard-excluded from training, and run at
four points in the training pipeline (§1): **baseline**, **periodic** (subset), **phase-end**
(extensive), and **final** (complete).

**Cadence and GPU isolation (proposed).** Evaluate **once per epoch** on a **64-row** stratified subset;
run the **full validation** split at each phase end; run the **final test** once after phase 2. Save at
eval points and keep the last two checkpoints. Do **not** run a vLLM `sidecar` on the same 24 GB GPU as
2.6B LoRA training at 8k: a second model copy plus KV cache likely OOMs, and the contention slows
training even when it fits. On a single 24 GB card use `sync` eval at those boundaries, or put eval on a
separate GPU; `sidecar`/`reserved` require headroom or dedicated GPUs. The full validation pass
(~1,159 rows) is a phase-end pause, not a periodic one.

| Evaluation dataset | Training role mirrored | Serves |
|---|---|---|
| CAD-QA held-out | `learn_the_cadqa_task` | H2; the thesis number |
| Tool-format held-out | `emit_our_tool_call_format` | H1 format compliance |
| General math + code | `preserve_general_math_and_code_reasoning` | specialization-tradeoff monitor; H4 covariate |
| External transfer | — (external) | H3, H4 |

Regression monitor: if the `preserve_general_math_and_code_reasoning` accuracy drops by more than a
pre-registered review threshold (suggest ≤2 points) while the CAD-QA held-out accuracy rises, report the
run as a **specialization tradeoff** (with the paired CI) — it is a monitoring signal, not a failed run or
a non-inferiority gate. Instruction-following forgetting, if measured, is a separate general-task
diagnostic.

**Evaluation-dataset provenance hygiene ([29]).** The `emit_our_tool_call_format` held-out set must
be **disjoint from the public training corpora** (`xLAM`/`ToolACE`/`Glaive`), which the base LLM model
likely saw in post-training; a memorized set inflates format compliance. Prefer our own `submit_*`
rows, a disjoint dataset, or a synthetic set.

---

## 7. Baselines

- **Shortcut families** must be reported separately from geometry-reasoning accuracy (D-B1), and
  re-run on the current row schema before any number is quoted. Current state is `stale`
  (`baselines.md`).
- **Cost-effective LLM model runs** via the **same local tool-call harness** (Harbor is deferred P2,
  D-E9); every number names its slice (D-B3). The recorded
  65/63/59% are the **rc10 clean-100 (0-hop, easy)** slice, not the hard target slice.
- **Oracle / tool-assisted** is a key-path/upper-bound check, never an LLM model baseline (D-B2).

---

## 8. Current status

| Scope | Status | Note |
|---|---|---|
| `numpy` mode | `exists` | implemented and runnable; no preserved `numpy` run (`[unverified — needs GPU]`) |
| `no_tools` mode | `exists` | implemented |
| `cadquery` mode | `missing` | `NotImplementedError` |
| Harbor export/grading | `exists` | materialization, submission loading, per-row grading |
| Oracle grading path | `verified` | 1.0 on recorded slices |
| Grader off the oracle path | `[unverified]` | no wrong-answer/formatting-variant fixture (TA-A2) |
| Harbor end-to-end large LLM model numbers | `[unverified — needs <env>]` | trajectories not preserved |
| Scorers agree (eval / reward / harness) | **no** | three implementations (TA-A3) |

These are exactly the Phase 0 audit units (TA-A1–A4, TA-B1, TA-C*); this doc consumes their
results rather than repeating the plan.

---

## 9. P0 / P1 / P2 (evaluation)

| Item | Tier | Rationale |
|---|---|---|
| Single scorer shared by eval, rejection sampling, and reward | **P0** | otherwise the thesis number and the training signal diverge (TA-A3) |
| Oracle + off-oracle grader fixture (near-miss and formatting variants) | **P0** | oracle 1.0 is not grader correctness (TA-A2) |
| Evaluation-dataset procedure wired to the cookbook eval (`learn_the_cadqa_task`, `emit_our_tool_call_format`, `preserve_general_math_and_code_reasoning`) | **P0** | every training run needs the specialization-tradeoff monitor, not a gate |
| Immutable held-out rows + hard-excluded evaluation-dataset rows | **P0** | held-out hygiene (owned with the data doc) |
| Public/private leak audit | **P0** | a leak invalidates the benchmark |
| External transfer harness on BenchCAD `qa_code` (primary) and `edit_code` (secondary) | **P1** | the evidence that the dataset is useful beyond its own split; transfer gate for H3 |
| Reachability pilot + family-disjoint BenchCAD subset | **P0** | a target the base LLM model cannot attempt yields no transfer signal |
| H4 dose-response: CAD-QA pass rate vs external score | **P1** | proves the dataset is a lever, not a tutorial |
| Re-run shortcut baselines on the current schema | **P1** | current baselines are `stale` |
| Harbor: external-agent baselines + untrusted-code sandbox | **P2** | deferred (D-E9). It was to show the tuned LLM model working in a general agent setting (`opencode`-style), but that is unwise before   the base setup works and adds sampling cost; even in P2 it may not earn its keep. External baselines
  can run through the **same local tool-call harness**, so Harbor is only needed for genuinely untrusted
  agent code, and its practical cost is container RAM (Daytona can replace local Docker). |
| Few-shot baseline | **P2** | extra comparison |
| `no_tools` and `cadquery` mode matrices | **P2** | upper-bound studies |

---

## 10. Decisions (evaluation)

The consolidated decision log is [`decisions.md`](decisions.md): **D-E1**–**D-E9** (harness, transfer,
and the one-scorer rule) and **D-B1**–**D-B3** (baselines). This section is now a pointer.

---

## 11. Open questions (evaluation)

- **Q1.** Should the local harness (`train_and_eval/eval/eval_bench.py`, which grades with
  `tool_calls.py::tool_call_matches`) import the **Harbor grader**
  (`train_and_eval/grading/grade.py::grade_public_private`, copied into the container as
  `tests/grade_cadqa.py`) — or the reverse — so the two exact-match paths cannot drift? (D-E2 open
  question.) Applies only if Harbor is revived; while Harbor is deferred (D-E9), the one local
  scorer (D-E8) is the target.
- **Q3.** Which rows make up the `preserve_general_math_and_code_reasoning` evaluation dataset? A
  500–1,000 row math + code set is a cheap monitoring signal; report paired CIs and do not treat it as a
  powered non-inferiority test. A full MMLU is P2.
- **Q5.** Which BenchCAD slice is the canonical transfer target: full `qa_code`, the Spatial Reasoning axis,
  or a hard family subset? And is `edit_code` T4/T5 reachable by a 2–4B LLM model? `[unknown]`.

## Resolved questions (evaluation)

- **Q2.** *(2026-10-09)* Not a single "canonical baseline slice". **Evaluation is the set of datasets
  that serve H1–H4**, each composed across Difficulty tiers and run at four points — baseline, periodic
  (subset), phase-end (extensive), final (complete). Baselines run on those same evaluation datasets,
  composed across Difficulty tiers; per-dataset composition is
  `../datasets.md`.
- **Q4.** *(2026-10-09)* Liquid Finetune runs `evals:` with pluggable metrics (the Evaluation Guide) and a
  standalone `eval` subcommand writing `results.json`; wire our exact-match scorer as a custom metric, or
  grade its generations offline. `async_eval` runs evals without blocking training.
  (`../../research/2026-liquid-finetune.md`.)

---

## 12. Immediate next step (evaluation)

1. **Reconcile the scorer** (§4, P0): one implementation for eval, rejection sampling, and reward,
   with the `boolean` union from `parse.py`.
2. **Build the oracle + off-oracle fixture** (P0) and assert both the identity path and the
   wrong-answer/formatting variants.
3. **Freeze the held-out and evaluation-dataset rows** with the data doc and hard-exclude them from training.
4. **Wire the evaluation-dataset procedure** (`learn_the_cadqa_task`, `emit_our_tool_call_format`,
   `preserve_general_math_and_code_reasoning`) into the cookbook eval
   path once the training doc has the `mixed_dataset_general_and_easy_cadqa` artifact.
5. **Pilot the external transfer target** (§5.1, P0): run the base LLM model on a family-disjoint
   BenchCAD `qa_code` subset to confirm a low-but-nonzero floor before any training spend.
