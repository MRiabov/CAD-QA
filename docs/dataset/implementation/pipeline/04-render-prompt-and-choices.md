# Pipeline stage 04 — Render prompt and choices

**Purpose:** turn a task definition into the exact model-facing prompt
and, for multiple choice, the rendered choice set.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Render the prompt from program text, question, task clues, choices, and answer
  instruction.
- Keep the prompt answer-free.
- Render task clues in the definition's canonical order in P0. A seeded
  permutation that respects reference dependencies is P1; it is recorded as the
  render seed, and clue wording uses presentation positions.
- For multiple choice, order and label the definition's choice pool. Do
  not re-bind entities or recompute answers.
- For P2 multiple choice, render the validated near-miss choice pool produced by
  `03`.
- Emit dataset release rows with the prompt and answer columns.

## Prompt copy comes from YAML

LLM-facing wording is data, not Go code. Pipeline stage `04` renders from
`prompts.yaml`; it does not contain hardcoded question, clue, choice, or answer
instruction strings.

- Templates cover the question, each clue type, choice descriptions, and the
  answer instruction.
- Each template has a stable ID and typed placeholders. Validation rejects a
  missing, extra, or untyped placeholder.
- Template variants are selected deterministically from the template ID and
  seed, not by an LLM.
- The template version and `prompts.yaml` hash are recorded with the release so
  the rendered prompt is reproducible.
- The YAML is answer-free. It must not contain gold answers, hidden identifiers,
  or generated answer data.
- P2 near-miss choice copy uses the same template mechanism.

Evaluation prompts outside the dataset follow the same rule: they live in
`prompts.yaml`, not in Python strings. Dataset and evaluation templates use
separate namespaces in that file.

## Language and parallelism

- **Go:** prompt and choice rendering.
- Rendering is parallel per task; a task definition is immutable and rendering
  has no shared mutable state.
- The release table has one deterministic writer. Parallel output is merged by
  `task_id`.

## No rejection

Rendering must not reject a task definition. Choice availability, choice
validity, target ambiguity, answer evidence, and uniqueness are decided in `03`.
Task quota planning is decided in `03a`. A rejection here is a defect in an earlier
pipeline stage.

## Not here

Gold-answer correctness and task validity (`03b`), task quota planning (`03a`), and
release export (`05`).
