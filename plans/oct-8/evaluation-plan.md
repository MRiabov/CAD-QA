# Evaluation plan (2026-10-08)

**Status:** draft, 2026-10-08. This is the evaluation companion to
`fine-tuning-architecture-plan.md` (training) and `fine-tuning-data-plan.md` (data). Evaluation is
**not fine-tuning-specific** — the same harness, scorer, and baselines score the base LLM model, the
tuned LLM model, and the cost-effective external models through Harbor. Written in the primary
checkout per the repo-local rule in `plans/oct-7/restructure-docs.md` §0.

**This doc owns — the shared evaluation base:** the LLM harness and its modes, the tool-call and
answer surface, the scorer, the canary procedure, grading reconciliation, judge independence,
baselines, and evaluation P0/P1/P2.

**Why it is its own doc.** The evaluation surface is *not* a sub-part of training. It is the shared
dependency that (a) scores the final thesis number, (b) generates the teacher traces through
rejection sampling (the data doc's `cadqa_hop`), and (c) would supply the reward if RL is run.
Training is the extra step that adds gradients and data on top of this base; evaluation adds none.
Single-sourcing the scorer is what makes the thesis number mean anything.

**Shared interfaces, single-sourced:**

- **Format contract** (Liquid `messages` SFT JSONL, and the native tool-call tokens) — owned by
  `fine-tuning-architecture-plan.md`.
- **`TrainingExample` + converter** — owned by `fine-tuning-system-plan.md`.
- **Canary procedure** — owned here; the canary **rows** are produced and held by the data doc.
- **H1/H2** — owned by the architecture doc; the mixes they test are defined by the data doc.

**Related docs.** `../../docs/train-and-eval/evaluation/harness.md` and `baselines.md` (current
descriptive docs); `../../docs/train-and-eval/fine-tuning/decisions.md`; `../../plans/oct-8/trust-audit.md`
(Phase 0 audit units TA-A*, TA-C*); `../../docs/PRD.md` (evaluation contract).

---

## 1. What "evaluation" means here

Run an LLM model **closed-book** over CAD-QA dataset rows and score **exact structured answers**
under a switchable compute mode. The evaluation harness is the whole chain:
model → chat template → tool declarations → generation loop → tool execution → tool-call parser →
scorer. Training and evaluation differ only in what they do with the output: training adds a
gradient update; evaluation does not.

**Tools are shared with training.** The `submit_*` tools, the `run_code` compute tool, the
`[answer contract]` suffix, and the Answer format → tool mapping are the same surface the training
data uses. This is the sense in which "eval == training tool calls": the tool-call/harness layer is
common. The difference is at the objective (see the architecture doc, §1: SFT scores only to
*admit* a trace and trains by imitation; RL would score as a reward).

**Two execution surfaces (D-E2).** The local harness speaks the native tool-call protocol and
grades with `tool_calls.py::tool_call_matches`; Harbor runs an external coding agent that writes
`/app/answer.json|txt` and grades with `grading/grade.py::grade_public_private`. They share the
CAD-QA dataset row contract and the exact-answer principle but **do not share a grader
implementation** — a recorded defect (see §4).

---

## 2. LLM harness modes

An LLM harness mode is which compute tools the model gets. All modes are closed-book: no CadQuery
kernel, no network. Detail and status: `../../docs/train-and-eval/evaluation/harness.md`.

- **`numpy` (primary, P0).** Submit tools plus the sandboxed `run_code` (Python + NumPy + `math`).
  This mode gates the thesis claims.
- **`no_tools` (P2).** Submit tools only; arithmetic internal. Strict-reasoning upper bound.
- **`cadquery` (P2, unimplemented).** Full CadQuery kernel; one correct call suffices. Reserved
  for the RL stage; `tools_for_mode` raises `NotImplementedError`.

The `run_code` execution path is `train_and_eval/run_code_sandbox.py` (`python -I -B`), an
**accidental-misuse guard, not a security boundary** (D-E3). Its isolation remains `[unverified]`
(trust-audit TA-B1).

---

## 3. Tool-call and answer surface

- **The `[answer contract]` suffix** tells the model to end with the matching `submit_*` call.
- **One submit tool per Answer format** (`train_and_eval/tool_calls.py::FORMAT_TO_TOOL`); `json` is
  specifically the CadQuery workplane tool, not generic JSON (FT-D4).
- **The native tool-call spelling is base-specific.** The evaluation harness must be re-pointed at
  the chosen base's tokens: for LFM2.5, `<|tool_call_start|>`/`<|tool_call_end|>` with Pythonic
  calls by default. The gemma `<|tool_call>` spelling does not transfer (FT-D3;
  `../../docs/development-context.md` "Tool-call and answer-submission format churn"). This is why
  the harness, not just the data, must change when the base changes.

---

## 4. The scorer — and the one-scorer rule

The repo currently has **three** scoring implementations:

| Scorer | Used by | Decision rule |
|---|---|---|
| `grading/grade.py::exact_match` (+ `grading/parse.py::parse_answer`) | eval, Harbor | parse by Answer format, then `gold == predicted`; `coordinate` rounded to 6 dp; `number` plain `float`; `boolean` handled |
| `tool_calls.py::tool_call_matches` | local harness, teacher rejection sampling | exact strings/ints, `1e-3` relative floats, `text` tolerates float formatting; no `boolean` entry |
| `reward_cadqa.py::reward_cadqa` | GRPO | different fallback parser; `text` uses substring presence |

**Rule (proposed, P0): one scorer.** Evaluation, teacher rejection sampling, and any future reward
must share a single verified scorer, or the thesis number and the training signal measure different
things. Reconciling them is trust-audit **TA-A3**. `grading/parse.py` already covers the `boolean`
Answer format that the typed contract omits — the union is the target.

**Why this outranks cleanup (2026).** In RLVR the verifier *is* the objective, so a noisy or
divergent scorer is optimized, not merely mis-counted. Verifier audits find self-agreement as low
as 53.8% and two configurations of the same library disagreeing on 49.9% of pairs ([24]); the
numeric/coordinate formats need an explicit equivalent-answer (metamorphic) test. See
`fine-tuning-system-plan.md` §4 and FT-D14.

**Oracle is not correctness.** The oracle key path returning 1.0 proves the public/private merge
and parser accept the gold encoding; it does **not** establish grader correctness on wrong answers
(D-B2; TA-A2). A near-miss/formatting-variant fixture is required.

---

## 5. Evaluation procedure

- **Held-out rows.** Evaluate on a frozen, group-safe held-out slice only (never a training mix).
- **Metrics.** Accuracy; invalid-output rate (parse errors); missing-response rate; accuracy by
  Reasoning hop count, Answer format, and LLM harness mode; reasoning length; calibration when
  confidence is requested; and **pass@k per prompt/tier** — the RL-readiness signal
  (`fine-tuning-system-plan.md` §3).
- **Judge independence.** No LLM model in the trusted grading path (DD-03). Grading is exact-match
  code; the teacher only produces training traces, never evaluated answers.
- **Public/private hygiene.** `grading/closed_book.py::closed_book_request_audit` fails on any
  hidden-field leak, incomplete request coverage, or Answer format disagreement.

---

## 6. Canaries

Every run evaluates three surfaces; the architecture doc owns the training mechanics and the data
doc holds the rows.

| Canary | What | Why | Frequency |
|---|---|---|---|
| `cadqa_heldout` | frozen held-out CAD-QA dataset rows, primary `numpy` mode | the thesis number | every run |
| `tool_valid` | a held-out `format_tool` slice: does the emitted call parse and match? | isolates format compliance (H1) | every run |
| `general` | a small fixed math + instruction probe | detects forgetting | every run |

Regression gate: if `general` drops beyond a pre-registered tolerance (suggest ≤2 points) while
`cadqa_heldout` rises, the run is a **forgetting result** and is reported, not hidden.

Open question: does `liquid-finetune`'s eval config cover our scorer, or do we grade offline from
its generations? `[unknown]` — resolve on the cookbook reproduction.

---

## 7. Baselines

- **Shortcut families** must be reported separately from geometry-reasoning accuracy (D-B1), and
  re-run on the current row schema before any number is quoted. Current state is `stale`
  (`../../docs/train-and-eval/evaluation/baselines.md`).
- **Cost-effective LLM model runs** via Harbor; every number names its slice (D-B3). The recorded
  65/63/59% are the **rc10 clean-100 (0-hop, easy)** slice, not the hard target slice.
- **Oracle / tool-assisted** is a key-path/upper-bound check, never a model baseline (D-B2).

---

## 8. Current status

| Surface | Status | Note |
|---|---|---|
| `numpy` mode | `exists` | implemented and runnable; no preserved `numpy` run (`[unverified — needs GPU]`) |
| `no_tools` mode | `exists` | implemented |
| `cadquery` mode | `missing` | `NotImplementedError` |
| Harbor export/grading | `exists` | materialization, submission loading, per-row grading |
| Oracle grading path | `verified` | 1.0 on recorded slices |
| Grader off the oracle path | `[unverified]` | no wrong-answer/formatting-variant fixture (TA-A2) |
| Harbor end-to-end big-model numbers | `[unverified — needs <env>]` | trajectories not preserved |
| Scorers agree (eval / reward / harness) | **no** | three implementations (TA-A3) |

These are exactly the Phase 0 audit units (TA-A1–A4, TA-B1, TA-C*); this doc consumes their
results rather than repeating the plan.

---

## 9. P0 / P1 / P2 (evaluation)

| Item | Tier | Rationale |
|---|---|---|
| Single scorer shared by eval, rejection sampling, and reward | **P0** | otherwise the thesis number and the training signal diverge (TA-A3) |
| Oracle + off-oracle grader fixture (near-miss and formatting variants) | **P0** | oracle 1.0 is not grader correctness (TA-A2) |
| Canary procedure wired to the cookbook eval (`cadqa_heldout`, `tool_valid`, `general`) | **P0** | every training run needs a forgetting gate |
| Frozen held-out rows + hard-excluded canary rows | **P0** | held-out hygiene (owned with the data doc) |
| Public/private leak audit | **P0** | a leak invalidates the benchmark |
| Re-run shortcut baselines on the current schema | **P1** | current baselines are `stale` |
| Harbor big-model baseline refresh on the hard slice | **P1** | the ≤30% target refers to the hard slice, currently unrecorded |
| Few-shot baseline | **P2** | extra comparison |
| `no_tools` and `cadquery` mode matrices | **P2** | upper-bound studies |

---

## 10. Decisions (evaluation)

- **D-E1** `numpy` primary; `no_tools`/`cadquery` P2. **D-E2** local harness and Harbor are
  separate surfaces sharing the row contract, not one harness with two backends. **D-E3**
  `run_code` is an accidental-misuse guard, not a security boundary. **D-E4** Harbor reward is a
  scalar 0/1 exact match; diagnostics live in the artifact. (From
  `../../docs/train-and-eval/evaluation/harness.md`.)
- **D-B1** shortcut baselines reported separately. **D-B2** oracle is a key-path check. **D-B3**
  LLM model baselines name the slice. (From `baselines.md`.)
- **New (proposed):** one scorer for eval, rejection sampling, and reward; canary `general`
  regression tolerance pre-registered at ≤2 points.

---

## 11. Open questions (evaluation)

- Should the local harness import the Harbor grader (or the reverse) so the two exact-match paths
  cannot drift? (D-E2 open question.)
- Which slice is the canonical baseline slice: rc10 clean-100, release10k, or a frozen hard test?
- What is the exact `general` canary probe? A 500–1,000 row math+instruction set is cheap and
  enough for regression detection; a full MMLU is P2.
- Does `liquid-finetune`'s eval config let us plug in our scorer, or do we grade its generations
  offline? `[unknown]`.

---

## 12. Immediate next step (evaluation)

1. **Reconcile the scorer** (§4, P0): one implementation for eval, rejection sampling, and reward,
   with the `boolean` union from `parse.py`.
2. **Build the oracle + off-oracle fixture** (P0) and assert both the identity path and the
   wrong-answer/formatting variants.
3. **Freeze the held-out and canary rows** with the data doc and hard-exclude them from training.
4. **Wire the canary procedure** (`cadqa_heldout`, `tool_valid`, `general`) into the cookbook eval
   path once the architecture doc has the `mix-format` artifact.
