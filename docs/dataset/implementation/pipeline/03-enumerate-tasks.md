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

## Support tables

The task reasoning step support table is four small JSON files:

```text
support/target-category.json
support/clue-type.json
support/answer-meaning.json
support/answer-format.json
```

Each file has a versioned envelope and typed rows:

```json
{
  "schema_version": "1",
  "rows": [
    {
      "task_reasoning_step_count": 1,
      "target_category": "face",
      "structurally_supported": true,
      "implementation_scope": "P0",
      "reason": "..."
    }
  ]
}
```

The row field is named after the file: `target_category`, `clue_type`,
`answer_meaning`, or `answer_format`. There is no generic
`(dimension, value)` map.

The tables are derived from the task rules: target identification, clue
preconditions, answer-step accounting, answer meaning to answer format
compatibility, and implementation scope. The `reason` records why a value is
unsupported or which construction supports it.

The Go binary embeds the four files with `//go:embed support/*.json`, parses them
into typed structs, and validates the schema version, enum values, and primary
key `(task_reasoning_step_count, <typed value>)`. The files are compile-time
generator inputs, not mutable runtime configuration.

The four files are pipeline definitions for now. When they are generated, the
release is expected to copy them into its `support/` directory and record their
schema versions and hashes in `manifest.json`. That release-contract change is
deferred until the tables exist.

## Resolved questions

- **Q2.** *Resolved 2026-10-21.* Option B: atomic predicates. Each relation or
  property is one task clue and one task clue step. A list item that states a
  relation and a property is split into two task clues. A chain is not one task
  clue; it is a P2 ordered sequence of relation task clues, one step per
  relation. Task clues are rendered as numbered list items, not prose.

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

## Not here

Prompt rendering, multiple-choice choices, release selection, and export.
