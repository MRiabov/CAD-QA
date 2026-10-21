# Pipeline stage 03 — Enumerate tasks

**Purpose:** turn CAD graphs into task candidates: task target, ordered task
clues, task reasoning step count, canonical identity, and gold answer.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Define the task tuple and canonical identity.
- Define the valid-task set.
- Define exact task reasoning step accounting.
- Define the typed clue predicate schema.
- Resolve the gold answer and its evidence.
- Reject ambiguous or invalid tasks.

## Resolved questions

- **Q4.** *Resolved 2026-10-21.* Multiple choice is valid for every answer
  meaning; it is a presentation wrapper, not a separate answer meaning. The
  native answer format is recorded with the answer meaning; multiple choice may
  be used when enough choices can be generated.

- **Q5.** *Resolved 2026-10-21.* A task is a duplicate when its canonical task
  tuple is identical: `(program_sha256, task target identity, canonical task
  clue sequence, answer meaning)`. The canonical task clue sequence is the task
  solution sequence after canonical serialization: preserve the dependency order
  required by references, then sort independent clues deterministically. Answer
  format, multiple-choice choices, prompt wording, and answer instruction are
  excluded because multiple choice is a presentation wrapper.

## Open questions

- **Q2.** Is a chain clue one task reasoning step or one step per relation? Is a
  clue that combines a relation and a property one condition or two?
  - **Recommendation:** Option B: atomic predicates. Each relation or property
    is one clue and one step.

## Not here

Prompt rendering, multiple-choice choices, release selection, and export.
