# Evaluation — local decisions

Unit-level decisions for the evaluation harness, baselines, and the external-transfer suite, in ADR
format. Step-scoped rationale also appears in `harness.md`, `baselines.md`, and `plan.md`; this file is
the consolidated decision log. Open questions stay in `plan.md` §11.

## D-E1 — `numpy` is the primary LLM harness mode

- **Status:** accepted.
- **Context:** the dataset's value is geometry reasoning without a CAD kernel, and the thesis needs one
  primary, comparable score.
- **Decision:** `numpy` (submit tools + sandboxed `run_code`) is primary; `no_tools` and `cadquery` are
  P2 upper-bound studies.
- **Consequences:** `numpy` is the mode that gates claims; `no_tools`/`cadquery` are collected under
  `## Extra deliverables - P2`. Detail: `harness.md`.

## D-E2 — The local harness and Harbor are separate environments

- **Status:** accepted; grader reconciliation open (`plan.md` Q1).
- **Context:** the local checkpoint speaks native tool calls, while Harbor runs a general coding agent
  that writes files; the two answer protocols differ.
- **Decision:** the local harness (`train_and_eval/eval/eval_bench.py`) and **Harbor** are **separate
  execution environments** sharing the CAD-QA dataset row contract — not one harness with two backends.
- **Consequences:** grading is not literally shared; a change to one grader must be mirrored
  deliberately and is an audit item (TA-A3). Reconcile via one authoritative grader (Q1).
- **Update (2026-10-09).** Harbor is **deferred to P2**. It was built to show the tuned LLM model
  working in a general agent setting (`opencode`-style) rather than a confined tool call — unwise before
  the base setup works, and it adds sampling cost; even within P2 it may not earn its keep, and its
  practical cost is container RAM (Daytona can replace local Docker). The thesis does not depend on it:
  **training and evaluation share one tool-call harness and the same rollout loop**, so external/teacher
  evaluation runs through the local rollouts, not Harbor. Harbor remains the only sandbox for
  genuinely untrusted agent code and the containerized RL reward (both optional).

## D-E3 — `run_code` is an accidental-misuse guard, not a security boundary

- **Status:** accepted.
- **Context:** a plain Python subprocess cannot isolate a determined attacker, and the training box
  cannot provide namespaces.
- **Decision:** `run_code` is an accidental-misuse guard, not a security boundary.
- **Consequences:** `run_code` must not be exposed to untrusted input; sandbox isolation remains
  `[unverified]` (TA-B1).

## D-E4 — Harbor reward is a scalar 0/1 exact match

- **Status:** accepted.
- **Context:** the agent loop consumes a reward, while analysis needs the full breakdown.
- **Decision:** Harbor reward is a scalar 0/1 exact match; diagnostics live in the artifact.
- **Consequences:** `reward.txt` is the interface to Harbor; richer metrics come from
  `cadqa_grade.json`. Detail: `harness.md`.

## D-E5 — H3 transfer is evaluated on existing, credible benchmarks

- **Status:** accepted.
- **Context:** the dataset's usefulness must be shown on data it was not built from.
- **Decision:** the transfer claim (H3) is evaluated against **existing, credible** benchmarks — BenchCAD
  `qa_code` (P0 means), with BenchCAD `edit_code` and a text-in text-to-CAD benchmark (P1) — each on its
  official full split and metric, against Base / format-only / answer-only controls. Stale gaps
  (`GeoGramBench`, `QueryCAD`) are re-run or dropped.
- **Consequences:** it is a P0 check — the only evidence the dataset is useful beyond its own split.
  Detail: `plan.md` §5.1.

## D-E6 — H4 is a dose-response

- **Status:** accepted.
- **Context:** the mechanism claim (H4) needs the dataset's value linked to the independent benchmark.
- **Decision:** the dataset's value is measured as a dose-response (H4): CAD-QA pass rate against the
  independent-benchmark score, at fixed recipe and matched compute, with the
  `preserve_general_math_and_code_reasoning` evaluation dataset as covariate.
- **Consequences:** Detail: `plan.md` §5.1.

## D-E7 — Evaluation is the datasets that serve H1–H4, at four points

- **Status:** accepted (2026-10-09).
- **Context:** a single number (or a canonical slice) would hide which hypothesis is being tested.
- **Decision:** evaluation is the datasets that serve H1–H4, run at four points — baseline (untrained
  instruct base LLM model), periodic (subset), phase-end (extensive), final (complete; the thesis
  number). No canonical baseline slice; the `canary` label is retired for "evaluation dataset".
- **Consequences:** owner: `plan.md` §1/§6; `../datasets.md`.

## D-E8 — One scorer across evaluation, rejection sampling, and reward

- **Status:** proposed.
- **Context:** three exact-match implementations can drift (TA-A3).
- **Decision:** one scorer for evaluation, rejection sampling, and reward; the
  `preserve_general_math_and_code_reasoning` regression tolerance pre-registered at ≤2 points.
- **Consequences:** pending the TA-A3 reconciliation (`plan.md` Q1); detail: `plan.md` §4.

## D-B1 — Shortcut baselines are reported separately from geometry-reasoning accuracy

- **Status:** accepted.
- **Context:** the benchmark's claim is that geometry rows are not answerable by syntax shortcuts, so
  mixing the two would hide the failure.
- **Decision:** shortcut baselines are reported separately.
- **Consequences:** baseline tables must name the slice and schema they were measured on; pre-graph-first
  numbers are `stale`, not current. Detail: `baselines.md`.

## D-B2 — The oracle is a key-path check, not a capability result

- **Status:** accepted.
- **Context:** it prints the answer it is given.
- **Decision:** the oracle is a key-path check, not an LLM-model capability result.
- **Consequences:** an oracle at 1.0 is never reported as an LLM-model baseline; it is cited only as
  grader/key evidence.

## D-B3 — LLM-model baselines name the slice

- **Status:** accepted.
- **Context:** rc10 is 0-hop and easy, while the thesis target is the hard (3+ hop) slice; an unlabeled
  "65%" is misleading.
- **Decision:** every LLM-model number carries its slice.
- **Consequences:** the hard-slice big-LLM-model number remains `[assumed]`/unrecorded
  (`development-context.md`).
