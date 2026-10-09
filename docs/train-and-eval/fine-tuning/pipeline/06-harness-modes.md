# 06 — evaluation harness modes

## Purpose

Evaluate a trained LLM model over CAD-QA rows under a selectable **LLM harness mode**, grading every
mode the same way with the one scorer.

## Modes (D-E1)

- **`numpy` (primary, P0):** submit tools + the sandboxed `run_code` (Python + NumPy + `math`). No
  access to CadQuery.
- **`no_tools` (P2):** submit tools only; arithmetic internal. Strict-reasoning upper bound.
- **`cadquery` (P2, unimplemented):** full CadQuery kernel; one correct call suffices. Reserved for the
  RL Training stage.

## Grading

One scorer (`../../evaluation/plan.md` §4). Both execution surfaces share the row contract but **do not
share a grader implementation** (D-E2) until reconciled (TA-A3): the local harness grades with
`tool_call_matches`; Harbor grades with the public/private grader. **Harbor is deferred to P2** (D-E9),
so the local harness is the live grader; the reconciliation (Q2) applies only if Harbor is revived.

## Evaluation datasets

The datasets that serve H1–H4 (`../../evaluation/plan.md` §6), run at baseline, periodic (subset),
phase-end, and final; all hard-excluded from training.

## Sandbox

`run_code` is an **accidental-misuse guard, not a security boundary** (D-E3); its isolation is measured
by the audit (TA-B1).

## Resolved questions

- **Q1.** *(2026-10-09)* Liquid Finetune runs `evals:` with pluggable metrics and a standalone `eval`
  subcommand writing `results.json`; wire our exact-match scorer as a custom metric (or grade its
  generations offline). `async_eval` runs evals without blocking training.

## Open questions

- **Q2.** Reconciling the two exact-match paths: should the local harness
  (`train_and_eval/eval/eval_bench.py`, grades with `tool_calls.py::tool_call_matches`) import the
  **Harbor grader** (`train_and_eval/grading/grade.py::grade_public_private`, copied into the container as
  `tests/grade_cadqa.py`) — or the reverse — so they cannot drift (`../../evaluation/plan.md` Q1)? (The
  "local harness" is the in-repo executor; an **LLM harness mode** is the tool access it selects — do not
  conflate them.)
