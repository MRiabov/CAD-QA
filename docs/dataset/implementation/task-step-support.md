# Task reasoning step support tables

**Status:** draft, 2026-10-21. This document defines the derived QA baseline used
to check a release. It is not a pipeline stage and not a generator input.

## Role

The **task reasoning step support tables** record which target categories, clue type
values, answer meanings, and answer formats are structurally feasible at each task
reasoning step count.

They exist to check the dataset:

- a feasible value missing from the release is a coverage gap;
- a value present in the release but marked infeasible is a generator or
  specification defect;
- actual task counts are a separate coverage question.

The tables are derived from the task-definition rules in
[`pipeline/03-task-generation/03b-construct-task-definitions.md`](pipeline/03-task-generation/03b-construct-task-definitions.md). They are not
hand-authored, and `03` does not read them to decide what to attempt.

The derivation takes `implementation_scope` from the requirement priority
marks. That derivation is the implementation-scope filter: a value above the
release scope has no row, so it is neither planned nor accepted. `03a`
allocate task quotas calls the same derivation, so the plan and these tables
cannot disagree.

## Derivation

A task definition is a dependency chain:

```text
graph observation -> clue step 1 -> clue step 2 -> ... -> answer step?
```

The graph observation is input. It is not a task reasoning step. If the prompt
states the observation as a numbered task clue, it becomes a clue step.

Task reasoning step count is the number of task clue steps plus one if the task
needs an answer step:

- `observation -> A -> B -> C`, with `C` as the target identity: 3 steps.
- The same chain, asking for a measurement of `C`: 4 steps.
- `observation -> A`, asking for the identity of `A`: 1 step.

A dimension value is **supported** at a task reasoning step count when the
constructor produces at least one valid definition of exactly that many steps for
it, over the coverage fixture set:

```text
support(dimension_value, task_reasoning_step_count)
  = the fixture set produced at least one valid definition with that value
    and exactly that task reasoning step count
```

Support is an observation, not an abstraction of the grammar. There is one
implementation, the constructor, and the table records what it did. A second
description of what the grammar permits would be a second implementation that
can disagree with the first.

Dependency depth is a lower bound. A value may be supported at more than one
task reasoning step count. The table records feasibility; the release report
records availability and count.

`implementation_scope` comes from the product priority declarations. It is not
derived from the graph.

## Coverage fixture set

The fixture set is what makes "supported" concrete. It is part of the contract,
not a test detail.

- A fixture is a CadQuery program and its `program_sha256`, committed under
  [`pipeline/testing/fixtures/`](pipeline/testing/fixtures/). The hash is
  checked, so an edited fixture fails.
- A fixture is chosen from the pinned pool for a capability it exercises:
  several solid states, a pair relation, a CadQuery profile, a CadQuery workplane,
  and a feature-added region. One program may cover several capabilities.
- A fixture is representative, not degenerate. A solid built only to make one
  cell true is not a fixture.
- The graph is derived, not committed: `02a` extract CadQuery AST, `02b` execute
  CadQuery, `02c` build CAD graph, cached under `data/` by program hash and
  versions. No Parquet enters the repository, and a graph schema change
  regenerates the cache instead of invalidating a binary fixture.

The fixture set follows the vocabulary, not the cell count. A new value adds
rows to the table; if no fixture can produce them, the test names the missing
capability and the set grows by one program.

## The checked-in table

The expected table is `pipeline/testing/support-table.json`, one row per
dimension value and task reasoning step count. It is reviewed like code:
a diff claims that a value became possible or impossible, and the reviewer asks
which fixture or rule changed.

The table is not re-derived on every run. A table that follows the current pool
would change whenever a program was added or removed, which would make coverage
gaps and specification defects indistinguishable. The pool is used once, when a
fixture or an expected row is added.

An absent cell is not an observed absence. Every absent cell carries a reason
code from the closed set below, so a missing fixture cannot hide behind "not
produced".

## Files

The release carries four files under `support/`:

```text
support/target-category-by-step.json
support/clue-type-by-step.json
support/answer-meaning-by-step.json
support/answer-format-by-step.json
```

Each file has a versioned envelope and typed rows:

```json
{
  "schema_version": "1",
  "rows": [
    {
      "task_reasoning_step_count": 1,
      "target_category": "solid_state",
      "structurally_supported": true,
      "implementation_scope": "P0",
      "reason_code": null
    }
  ]
}
```

The row field is named after the file: `target_category`, `clue_type`,
`answer_meaning`, or `answer_format`.

`reason_code` is a low-cardinality enum, not free text. It is null when the row
is supported. Unsupported rows use one of:

- `task_reasoning_step_count_too_low`;
- `prior_candidates_required`;
- `reference_entity_required`;
- `answer_format_incompatible`;
- `target_not_identifiable`;
- `ambiguous_target`;
- `no_valid_construction`.

The four files are generated from the constructor over the coverage fixture set.
`05` copies them into the release and `manifest.json` records their schema
versions and hashes.

## Validation use

The structural floor is checked in every run, and the witness check runs in the
generation job. The two-tier test contract is
[`pipeline/testing/task-step-support.md`](pipeline/testing/task-step-support.md).

For each task reasoning step count and dimension:

1. Read the feasible values from the task reasoning step support table.
2. Read the values present in the release and their counts.
3. Report a coverage gap for every feasible value with zero tasks.
4. Report a specification defect for every released value marked infeasible.
5. Report balance against the release targets separately.

The table does not say how many tasks are needed. That belongs to coverage and
task quota planning.

## What this is not

- It is not a generator input.
- It is not a task quota planning policy.
- It does not prove that the corpus contains enough instances.
- It is not the valid-task set.
