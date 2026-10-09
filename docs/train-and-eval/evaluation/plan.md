# Evaluation

**Status:** active, 2026-10-09. The evaluation companion to `../fine-tuning/training.md` (training)
and `../fine-tuning/data.md` (data). Evaluation is **not fine-tuning-specific** — the same harness,
scorer, and baselines score the base LLM model, the tuned LLM model, and the cost-effective external
models through Harbor.

**This doc owns — the shared evaluation base:** the LLM harness and its modes, the tool-call and
answer contract, the scorer, the evaluation-dataset procedure, grading reconciliation, judge independence,
baselines, and evaluation P0/P1/P2.

**Why it is its own doc.** The evaluation concern is *not* a sub-part of training. It is the shared
dependency that (a) scores the final thesis number, (b) generates the teacher traces through
rejection sampling (the data doc's `learn_the_cadqa_task`), and (c) would supply the reward if RL is run.
Training is the extra step that adds gradients and data on top of this base; evaluation adds none.
Single-sourcing the scorer is what makes the thesis number mean anything.

**Shared interfaces, single-sourced:**

- **Format contract** (Liquid `messages` SFT JSONL, and the native tool-call tokens) — owned by
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
implementation** — a recorded defect (see §4).

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
  confidence is requested; and **pass@k per prompt/tier** — the RL-readiness signal
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
| CAD-QA reasoning | progressively complex `learn_the_cadqa_task` | H2 capability |
| Full primary (optional) | the full Mixed training dataset | external reasoning support |
| General-only (H4 counter-arm) | the full general mix **without** `learn_the_cadqa_task` | isolates CAD-QA supervision from general capability (H4) |

- **Claim.** CAD-QA reasoning > format-only **and** > Base on the P0 means target (BenchCAD
  `qa_code`, official split) is the transfer result; the end/defect targets corroborate the causal
  chain (comprehension → construction and fewer invalid shapes).
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
- **Peer-review stake.** Without a measured gain on a credible external benchmark the
  dataset-usefulness claim rests on an internal split and does not withstand review. A null transfer
  is reported as a finding (comprehension supervision is task-local), not hidden.

---

## 6. Evaluation datasets

The datasets that serve H1–H4 (§5.1). The architecture doc owns the training mechanics; the data
doc holds the rows. Each is composed across Difficulty tiers, hard-excluded from training, and run at
four points in the training pipeline (§1): **baseline**, **periodic** (subset), **phase-end**
(extensive), and **final** (complete).

| Evaluation dataset | Training role mirrored | Serves |
|---|---|---|
| CAD-QA held-out | `learn_the_cadqa_task` | H2; the thesis number |
| Tool-format held-out | `emit_our_tool_call_format` | H1 format compliance |
| General math + code | `preserve_general_math_and_code_reasoning` | forgetting guard; H4 covariate |
| External transfer | — (external) | H3, H4 |

Regression gate: if the `preserve_general_math_and_code_reasoning` accuracy drops beyond a
pre-registered tolerance (suggest ≤2 points) while the CAD-QA held-out accuracy rises, the run is a
**forgetting result** and is reported, not hidden. Instruction-following forgetting, if gated, is a
separate general-task guard.

**Evaluation-dataset provenance hygiene ([29]).** The `emit_our_tool_call_format` held-out set must
be **disjoint from the public training corpora** (`xLAM`/`ToolACE`/`Glaive`), which the base LLM model
likely saw in post-training; a memorized set inflates format compliance. Prefer our own `submit_*`
rows, a disjoint dataset, or a synthetic set.

---

## 7. Baselines

- **Shortcut families** must be reported separately from geometry-reasoning accuracy (D-B1), and
  re-run on the current row schema before any number is quoted. Current state is `stale`
  (`baselines.md`).
- **Cost-effective LLM model runs** via Harbor; every number names its slice (D-B3). The recorded
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
| Evaluation-dataset procedure wired to the cookbook eval (`learn_the_cadqa_task`, `emit_our_tool_call_format`, `preserve_general_math_and_code_reasoning`) | **P0** | every training run needs a forgetting gate |
| Immutable held-out rows + hard-excluded evaluation-dataset rows | **P0** | held-out hygiene (owned with the data doc) |
| Public/private leak audit | **P0** | a leak invalidates the benchmark |
| External transfer harness on BenchCAD `qa_code` (primary) and `edit_code` (secondary) | **P0** | the only evidence the dataset is useful beyond its own split; peer-review gate for H3 |
| Reachability pilot + family-disjoint BenchCAD subset | **P0** | a target the base LLM model cannot attempt yields no transfer signal |
| H4 dose-response: CAD-QA pass rate vs external score | **P0** | proves the dataset is a lever, not a tutorial |
| Re-run shortcut baselines on the current schema | **P1** | current baselines are `stale` |
| Harbor large LLM model baseline refresh on the hard slice | **P1** | the ≤30% target refers to the hard slice, currently unrecorded |
| Few-shot baseline | **P2** | extra comparison |
| `no_tools` and `cadquery` mode matrices | **P2** | upper-bound studies |

---

## 10. Decisions (evaluation)

- **D-E1** `numpy` primary; `no_tools`/`cadquery` P2. **D-E2** local harness and Harbor are
  separate environments sharing the row contract, not one harness with two backends. **D-E3**
  `run_code` is an accidental-misuse guard, not a security boundary. **D-E4** Harbor reward is a
  scalar 0/1 exact match; diagnostics live in the artifact. (From
  `harness.md`.)
- **D-B1** shortcut baselines reported separately. **D-B2** oracle is a key-path check. **D-B3**
  LLM model baselines name the slice. (From `baselines.md`.)
- **D-E5** the transfer claim (H3) is evaluated against a suite of **existing, credible**
  benchmarks — BenchCAD `qa_code` (P0 means), with BenchCAD `edit_code` and a text-in text-to-CAD
  benchmark (P1 end/defect) — each on its official full split and metric, against
  Base / format-only / answer-only controls. It is a P0 gate: the only evidence that the dataset is
  useful beyond its own split. Stale gaps (`GeoGramBench`, `QueryCAD`) are re-run or dropped.
- **D-E6** the dataset's value is measured as a dose-response (H4): CAD-QA pass rate against the
  independent-benchmark score, at fixed recipe and matched compute, with the
  `preserve_general_math_and_code_reasoning` evaluation dataset as covariate.
- **New (proposed):** one scorer for eval, rejection sampling, and reward; the
  `preserve_general_math_and_code_reasoning` regression tolerance pre-registered at ≤2 points.
- **D-E7** evaluation is the datasets that serve H1–H4, run at four points — baseline (untrained
  instruct base LLM model), periodic (subset), phase-end (extensive), final (complete; the thesis
  number); no canonical baseline slice, and "canary" is retired for "evaluation dataset". Owner:
  §1/§6; `../datasets.md`.

---

## 11. Open questions (evaluation)

- **Q1.** Should the local harness import the Harbor grader (or the reverse) so the two exact-match paths
  cannot drift? (D-E2 open question.)
- **Q3.** Which rows make up the `preserve_general_math_and_code_reasoning` evaluation dataset? A
  500–1,000 row math + code set is cheap and enough for regression detection; a full MMLU is P2.
- **Q4.** Does `liquid-finetune`'s eval config let us plug in our scorer, or do we grade its generations
  offline? `[unknown]`.
- **Q5.** Which BenchCAD slice is the canonical transfer target: full `qa_code`, the Spatial Reasoning axis,
  or a hard family subset? And is `edit_code` T4/T5 reachable by a 2–4B LLM model? `[unknown]`.

## Resolved questions (evaluation)

- **Q2.** *(2026-10-09)* Not a single "canonical baseline slice". **Evaluation is the set of datasets
  that serve H1–H4**, each composed across Difficulty tiers and run at four points — baseline, periodic
  (subset), phase-end (extensive), final (complete). Baselines run on those same evaluation datasets,
  composed across Difficulty tiers; per-dataset composition is
  `../datasets.md`.

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
