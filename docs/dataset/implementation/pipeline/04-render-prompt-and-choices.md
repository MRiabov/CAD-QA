# Pipeline stage 04 — Render prompt and choices

**Purpose:** turn a task definition into the exact model-facing prompt
and, for multiple choice, the rendered choice set.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Render the prompt from program text, question, task clues, choices, and answer
  instruction.
- Keep the prompt answer-free.
- For multiple choice, order and label the definition's choice pool. Do
  not re-bind entities or recompute answers.
- For P2 multiple choice, render the validated near-miss choice pool produced by
  `03`.
- Emit release rows with the prompt and answer columns.

## No rejection

Rendering must not reject a task definition. Choice availability, choice
validity, target ambiguity, answer evidence, and uniqueness are decided in `03`.
Release planning is decided in `03a`. A rejection here is a defect in an earlier
pipeline stage.

## Not here

Gold-answer correctness and task validity (`03b`), release planning (`03a`), and
release export (`05`).
