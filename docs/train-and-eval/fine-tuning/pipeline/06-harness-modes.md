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
`tool_call_matches`; Harbor grades with the public/private grader.

## Evaluation datasets

The datasets that serve H1–H4 (`../../evaluation/plan.md` §6), run at baseline, periodic (subset),
phase-end, and final; all hard-excluded from training.

## Sandbox

`run_code` is an **accidental-misuse guard, not a security boundary** (D-E3); its isolation is measured
by the audit (TA-B1).

## Open questions

- **Q1.** Does `liquid-finetune`'s eval config take our scorer, or do we grade its generations offline?
- **Q2.** Does the local harness import the Harbor grader (or the reverse) so the two exact-match paths
  cannot drift (`../../evaluation/plan.md` Q1)?
