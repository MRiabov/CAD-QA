# Baselines

**Status:** `stale` — the shortcut-heuristic baseline families recorded under
`runs/` were produced against the pre-graph-first row schema and their generating
code is no longer at HEAD; only the simple baselines and the oracle key-path check
are current. 2026-10-07.

## Purpose

Record what an LLM model must beat on CAD-QA: the trivial and shortcut systems whose
accuracy bounds how much of the benchmark is answerable without real CAD
reasoning, and the reference numbers for small and cost-effective LLM models.

## Requirement

The paper's claim that models fail CAD reasoning is only credible if a shortcut
system that exploits assignment names, operation order, literal arguments, or simple
patterns in the CadQuery program cannot answer the benchmark. A baseline is meaningful only when it
runs under the same grading contract as the LLM model (`train_and_eval/grading/grade.py`)
and is reported separately from geometry-reasoning accuracy
(`specs/research-experiment-spec.md`, "Primary Setting").

## Baseline families

Each family's status is one tag. "Recorded run" is what was actually executed and
preserved; "Code" is what exists at HEAD unless marked otherwise. The historical
heuristic families were defined in `train_and_eval/grading/baselines.py` at commit `85cb532`
("Add P0 shortcut baselines") and removed in commit `a0187dd` ("Pruning and
re-doing") when dataset generation moved to the graph-first design; they are not present
at `512a514`.

| Family | Logic | Code | Recorded run | Status |
|---|---|---|---|---|
| Graph-resolver oracle | Emit the private `gold_answer` (or a formatted variant of the private Query verifier artifacts) | `train_and_eval/grading/baselines.py::oracle_answer`; `train_and_eval/grading/tool_assisted.py::run_tool_assisted_upper_bound` | `runs/baseline_smoke/baseline_metrics.json` (1.0, 37 rows); `runs/cadqa_cadevolve_rc_10_baselines/baseline_metrics.json` (1.0, 958 rows) | `verified` |
| Majority | Predict the most frequent gold answer | `train_and_eval/grading/baselines.py::majority_answer` | rc10 0.333 (958 rows); heuristic smoke 0.571 (35 rows); not in `runs/baseline_smoke` | `exists` |
| Random | Uniform/typed random guess per answer format | historical only (pruned) | rc10 0.100 (958 rows); heuristic smoke 0.171 (35 rows) | `stale` |
| Regex / static syntax | Count operations by regex over the prompt code, or read a static label | historical only (pruned) | rc10 `regex_operation_count` 0.331, `static_operation_count` 0.340 (958 rows); heuristic smoke 0.314 / 0.314 (35 rows) | `stale` |
| CadQuery selector-name heuristic | Guess CadQuery selector cardinality from CadQuery selector expression tokens and CAD ontology node type | historical only (pruned) | rc10 0.301 (958 rows); heuristic smoke 0.200 (35 rows) | `stale` |
| Operation-order heuristic | Answer from operation order in the CadQuery program | not found in code or artifacts; named in `specs/paper-spec.md`, `specs/research-experiment-spec.md` | none found | `missing` |
| Symbolic primitive geometry | Closed-form volume delta from the builder operation and its literal args (box, hole, cutBlind, extrude) | historical only (pruned) | heuristic smoke 0.114 (35 rows) | `stale` |
| AABB-only | Classify point membership using the row's own bounding box (inside / on boundary / outside) | historical only (pruned) | heuristic smoke 0.029, invalid-output 0.829 (35 rows) | `stale` |
| First candidate | Predict the first candidate in the answer candidate set trace | `train_and_eval/grading/baselines.py::first_candidate_answer` | `runs/baseline_smoke/baseline_metrics.json` (0.297, 37 rows); retired `implementation_status.md` records 0.333 full-smoke and 0.667 filtered release | `exists` |
| First static filter | Predict the first candidate surviving a static filter | `train_and_eval/grading/baselines.py::first_static_candidate_answer` | none found | `exists` |
| Null | Always predict nothing | `train_and_eval/grading/baselines.py::run_baselines` ("null") | `runs/baseline_smoke/baseline_metrics.json` (0.0, 37 rows) | `exists` |

Notes on interpretation:

- The oracle is an **identity check on the key path**, not an LLM model result. Its 1.0
  is evidence that the public/private merge and parser accept the gold encoding; it
  does not establish grader correctness on wrong answers (see `harness.md`).
- The historical heuristic numbers were measured on the pre-graph-first rows
  (`task_type`, `labels`, `target_feature_id`), a different row schema from the
  current `answer_format`/`logical_hop_count` contract. Treat them as directional
  evidence that shortcuts do not solve the geometry rows, not as current baseline
  numbers.
- `majority_answer` at HEAD computes one global majority answer, while the
  historical runner used a per-`task_type` majority. The HEAD code is
  `exists`/unchecked; no recording of the HEAD form was found.

## Cost-effective LLM model runs

The evaluation contract targets cost-effective models at or below 30% on the hard
slices (`PRD.md`, "Evaluation contract"; `docs/_archive/paper/cadqa_draft.md`). The recorded
Harbor numbers for big LLM models are on the **rc10 clean-100 slice (0-hop, easy)** — the
easiest slice, not the hard target slice — and are quoted as context for the
small LLM model baseline in the experiment record.

| LLM model | Setting | Recorded result | Evidence | Status |
|---|---|---|---|---|
| xiaomi-mimo-v2.5 (pro) | Harbor, rc10 clean-100 (0-hop) | 65% | `docs/experiments/2026-08-08-gemma-e2b-bench.md#purpose`; `docs/development-context.md#proven` | `exists` |
| deepseek-v4-flash | Harbor, rc10 clean-100 (0-hop) | 63% | same | `exists` |
| Kimi (exact LLM model id not recorded) | Harbor, rc10 clean-100 (0-hop) | 59% | same | `exists` |
| NVIDIA NemoTron super | planned cost-effective LLM model | no run found | named in `docs/_archive/paper/cadqa_draft.md` | `missing` |
| gemma-4-E2B base (`google/gemma-4-E2B-it`) | local harness, `no_tools` LLM harness | rc10 30/100; release10k (2–5 hop) 14/100 | `docs/experiments/2026-08-08-gemma-e2b-bench.md#results` | `exists` |
| gemma-4-E2B + native-format SFT | local harness, 12 held-out rows | 50% accuracy / 58.3% tool-valid (post-fix re-run 41.7% / 75%) | `docs/development-context.md#proven` | `exists` |

The oracle-upper-bound setting (`tool_assisted.py`) is not an LLM model run; keep it
separate from the cost-effective LLM model table. `deepseek-v4-flash` is also the
teacher and the default Harbor LLM model (`glossary.md`, "teacher"; `docs/_archive/harbor.md`).

## Current status

Overall: `stale`. The shortcut families exist only as pre-graph-first artifacts,
and no current-schema run of them is recorded; the simple baselines and the LLM model
reference numbers are `exists`. Reproducing any recorded LLM model number needs a GPU
or OpenRouter environment that is not present: `[unverified — needs <env>]`. The
12-row SFT result is directionally encouraging but statistically unusable and must
not be quoted as a headline (`docs/development-context.md#proven`).

## What is runnable vs not

- Runnable now, no GPU: the simple baselines via
  `uv run cadqa evaluation baseline --rows <rows.jsonl> --out <dir>` and the same
  set embedded in `train_and_eval/experiment.py::run_smoke_experiment`.
- Runnable now, with a GPU and an LLM model: the local small-LLM-model harness
  (`train_and_eval/eval/eval_bench.py`).
- Runnable now, container/API needed: Harbor materialization and grading; a full
  Harbor run needs Docker or Daytona plus an OpenRouter key.
- Not runnable: the historical heuristic families. The runner module named in
  `runs/heuristic_baselines/run_status.json`
  (`scripts.evaluation.evaluate_baseline`) does not exist at HEAD, and the pruned
  `train_and_eval/grading/baselines.py` no longer matches the current row schema.

## Verification

- Regenerate the simple baselines:
  `uv run cadqa evaluation baseline --rows <rows.jsonl> --out <dir>`, then compare
  `baseline_metrics.json` to `runs/baseline_smoke/baseline_metrics.json` for the
  same rows.
- Re-run the current-schema oracle check:
  `uv run cadqa evaluation tool-assisted-upper-bound ...` and confirm accuracy 1.0.
- Re-run a cost-effective LLM model:
  `uv run cadqa harbor materialize ...` then `harbor run -c ...`, and compare to the
  experiment record.
- Re-run the small LLM model: the command under `harness.md#verification`.

A baseline moves from `stale` to `verified` only when it is re-run against the
current row schema and the artifacts are preserved.

## Local decisions

**D-B1. Shortcut baselines are reported separately from geometry-reasoning
accuracy.** Rationale: the benchmark's claim is that geometry rows are not
answerable by syntax shortcuts, so mixing the two would hide the failure.
Consequence: baseline tables must name the slice and schema they were measured on;
pre-graph-first numbers are `stale`, not current.

**D-B2. The oracle is a key-path check, not a capability result.** Rationale: it
prints the answer it is given. Consequence: oracle at 1.0 is never reported as a
LLM model baseline; it is cited only as grader/key evidence.

**D-B3. LLM model baselines name the slice.** Rationale: rc10 is 0-hop and easy, while
the thesis target is the hard (3+ hop) slice; an unlabeled "65%" is misleading.
Consequence: every LLM model number in this doc carries its slice; the hard-slice
big LLM model number remains `[assumed]`/unrecorded (`docs/development-context.md`).

## Open questions

- **Q1.** Are the recorded cost-effective LLM model Harbor artifacts (trajectories, graded
  rows) preserved anywhere, or only the headline percentages? Not found in-repo.
- **Q2.** Should the historical heuristic families be re-implemented against the current
  row schema, or retired in favour of the geometry-first split audit? The spec
  still names the operation-order heuristic, which was never found in code.
- **Q3.** Which slice is the canonical baseline slice for the paper: rc10 clean-100,
  release10k, or an immutable hard test?

## Resolved questions

None yet.

## Extra deliverables - P2

### Full baseline matrix by hop, relation family, and measurement scope

Re-run every family on the immutable release test and publish the full breakdown, not
just the headline accuracy.

### No-access-to-CadQuery few-shot baseline

Export the few-shot requests (`train_and_eval/grading/requests.py::few_shot_requests`)
and report cost-effective LLM model few-shot accuracy beside zero-shot.

### Hard-slice big LLM model numbers

Record the 3+ hop cost-effective LLM model accuracy that the paper's ≤30% target
actually refers to; it is currently assumed and unrecorded.
