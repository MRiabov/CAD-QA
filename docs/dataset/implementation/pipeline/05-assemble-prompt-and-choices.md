# Pipeline stage 05 — Assemble prompt and choices

**Purpose:** turn a selected task definition into the exact model-facing prompt
and, for multiple choice, the rendered choice set.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Render the prompt from program text, question, task clues, choices, and answer
  instruction.
- Keep the prompt answer-free.
- For multiple choice, order and label the selected definition's choice pool. Do
  not re-bind entities or recompute answers.
- Add plausible near-miss distractors for P2.
- Emit release rows with the prompt and answer columns.

## No rejection on the P0/P1 path

P0/P1 rendering must not reject a selected definition. Choice availability,
target ambiguity, answer evidence, and uniqueness are decided in `03`. Selection
is decided in `04`. A P0/P1 rejection at `05` is a defect in an earlier stage.

P2 near-miss distractor generation may fail after selection; that is Q1.

## Open questions

- **Q1.** How are plausible, deterministic distractors generated and validated?
  - **Recommendation:** start from the correct task solution and apply one
    controlled error; validate against the graph; record the error mode. P0 and
    P1 do not require the near-miss audit.

## Not here

Gold-answer correctness and task validity (`03`), selection and balance (`04`),
and release export (`06`).
