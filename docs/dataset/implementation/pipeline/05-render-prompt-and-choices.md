# Pipeline stage 05 — Render prompt and choices

**Purpose:** turn a selected task definition into the exact model-facing prompt
and, for multiple choice, the rendered choice set.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Render the prompt from program text, question, task clues, choices, and answer
  instruction.
- Keep the prompt answer-free.
- For multiple choice, order and label the selected definition's choice pool. Do
  not re-bind entities or recompute answers.
- For P2 multiple choice, render the validated near-miss choice pool produced by
  `03`.
- Emit release rows with the prompt and answer columns.

## No rejection

Rendering must not reject a selected definition. Choice availability, choice
validity, target ambiguity, answer evidence, and uniqueness are decided in `03`.
Selection is decided in `04`. A rejection at `05` is a defect in an earlier
pipeline stage.

## Not here

Gold-answer correctness and task validity (`03`), selection and balance (`04`),
and release export (`06`).
