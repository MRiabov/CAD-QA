# Pipeline stage 04 — Assemble prompt and choices

**Purpose:** turn a task candidate into the exact model-facing prompt and, for
multiple choice, the choice set.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Render the prompt from program text, question, task clues, choices, and answer
  instruction.
- Keep the prompt answer-free.
- Generate real multiple-choice choices for P0 and P1.
- Add plausible near-miss distractors for P2.
- Reject the task if enough choices cannot be generated.

## P2 open question

- **Q1.** How are plausible, deterministic distractors generated and validated?
  - **Recommendation:** start from the correct task solution and apply one
    controlled error; validate against the graph; record the error mode. P0 and
    P1 do not require the near-miss audit.

## Not here

Gold-answer correctness (pipeline stage 03), selection and balance (pipeline stage 05), and
release export (pipeline stage 06).
