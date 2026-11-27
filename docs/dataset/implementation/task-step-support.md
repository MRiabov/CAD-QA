# Task reasoning step support table

**Status:** draft, 2026-11-27. This document defines the derived QA baseline used
to check a release. It is a run artifact consumed by `03a` allocate task quotas
and `05` validate and export release; it is not a release file.

## Role

The **task reasoning step support table** records which target categories, clue type,
clue reduction forms, answer meanings, and answer formats the constructor
produced at each task reasoning step count over the coverage fixture set.

It exists to check the dataset:

- a supported value missing from the release is a coverage gap;
- a value present in the release but marked unsupported is a generator or
  specification defect;
- actual task counts are a separate coverage question.

It also defines the set of cells the release is balanced over. The conditional
release share divides by the values supported at a task reasoning step count
([`03a`/`b-balance.md`](pipeline/03-task-generation/03a-allocate-task-quotas/b-balance.md#conditional-share)),
so a cell the table does not support has no quota target and no share. A
`balance.yaml` target that names an unsupported cell is a policy defect, not a
zero.

The table is derived from the constructor, using the rules in
[`pipeline/03-task-generation/03b-construct-task-definitions/README.md`](pipeline/03-task-generation/03b-construct-task-definitions/README.md). It is not
hand-authored, and `03b` does not read it to decide what to attempt.

The derivation takes `implementation_scope` from the requirement priority
marks. That derivation is the implementation-scope filter: a value above the
release scope has no row, so it is neither planned nor accepted. `03a`
allocates task quotas from the same derivation, so the plan and these rows
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
  CadQuery, `02c` build CAD graph, written to the run's artifact directory. No
  Parquet enters the repository, so a graph schema change regenerates the graph
  instead of invalidating a binary fixture.
- Because a fixture is a pool program, its graph is part of the `02c` output the
  run already builds. A fixture with no accepted graph is a run defect: `03a`
  fails and names the fixture, rather than marking its cells unsupported. A
  rejected program must not look like a grammar limit.

The fixture set follows the vocabulary, not the cell count. A new value adds
rows to the table; if no fixture can produce them, the test names the missing
capability and the set grows by one program.

## Expected table and produced table

There are two artifacts, and they are different things:

- **Expected table.** `pipeline/testing/support-table.json`, reviewed like code.
  It carries the full vocabulary with `implementation_scope` per row, so it is
  scope-independent. A diff claims that a value became possible or impossible,
  and the reviewer asks which fixture or rule changed.
- **Produced table.** `<run>/03a-allocate-task-quotas/support/support.parquet`,
  written by `03a` from the same derivation and filtered to the run's
  implementation scope. `05` reads this table; the release directory does not
  contain it.

The expected table is not re-derived on every run. A table that follows the
current pool would change whenever a program was added or removed, which would
make coverage gaps and specification defects indistinguishable. The pool is
used once, when a fixture or an expected row is added.

An absent cell means the fixture set produced no valid definition for it; it does
not prove that no valid definition exists. Every absent cell carries a reason code
from the closed set below, so an absence is explained rather than left blank.

## The produced table

The table is one Parquet file, one row per dimension value and task reasoning
step count:

```go
type TaskReasoningStepSupportRow struct {
	Dimension              SupportDimension `parquet:"dimension"`
	Value                  string           `parquet:"dimension_value"`
	TaskReasoningStepCount int16            `parquet:"task_reasoning_step_count"`
	Supported              bool             `parquet:"supported"`
	ImplementationScope    ImplementationScope `parquet:"implementation_scope"`
	ReasonCode             *SupportReason   `parquet:"reason_code,optional"`
	WitnessProgramSHA256   *string          `parquet:"witness_program_sha256,optional"`
}
```

`dimension` is one of `target_category`, `clue_type`, `clue_reduction_form`,
`answer_meaning`, or `answer_format`. One column carries the dimension, so the
table has one schema and one schema version instead of one file and one schema
per dimension.

`witness_program_sha256` names the fixture that produced the definition. It is
non-null exactly when `supported` is true. When several fixtures produce one,
the witness is the lexicographically smallest `program_sha256`, so a rerun
writes the same row. It is a reference, not a count: a supported cell means "at
least one", not "enough for a quota". Capacity is the program capability census
and the deficit ledger, not this table.

The table carries no target share, quota, or task count. Balance numbers stay in
`balance.yaml`, and actual counts are the release checks; a copy here would be a
second home that drifts.

Table metadata: `schema_version`, `vocabulary_version`, `constructor_version`,
`derivation_version`, `implementation_scope`, and `fixture_set_sha256` over the
sorted fixture program hashes. The file SHA-256 is the artifact identity.

`reason_code` is a low-cardinality enum, not free text. It is null when the row
is supported. Unsupported rows use one of:

- `task_reasoning_step_count_too_low`;
- `prior_candidates_required`;
- `reference_entity_required`;
- `answer_format_incompatible`;
- `target_not_identifiable`;
- `ambiguous_target`;
- `no_valid_construction`.

The list is a precedence order: when more than one reason applies to a cell, the
row carries the first one, so the table is deterministic.

## Producer and readers

- `03a` derives the rows in-process from the constructor over the fixture set and
  writes the produced table before it allocates quotas. It records
  `support_schema_version` and `support_table_sha256` in the `TaskQuotaPlan`.
- `05` reads the produced table, requires its SHA-256 and schema version to equal
  the ones in the plan, and records both in `manifest.json`. A mismatch is an
  input error and blocks the export.
- The dataset browser reads the produced table from the run to order its review
  queue; it does not read a release copy.
- No pipeline stage copies the table into the release. The table is an input to
  the coverage and balance checks, and the checks carry its per-cell result:
  every `coverage` and balance row records `supported_cell` and `reason_code`, so a
  reader sees why a cell is absent without the matrix.

## Validation use

The structural floor is checked in every run, and the witness check runs in the
generation job. The two-tier test contract is
[`pipeline/testing/00-support-tables.md`](pipeline/testing/00-support-tables.md).

For each task reasoning step count and dimension:

1. Read the feasible values from the task reasoning step support table.
2. Read the values present in the release and their counts.
3. Report a coverage gap for every feasible value with zero tasks.
4. Report a specification defect for every released value the table marks
   unsupported at that step count.
5. Report balance against the release targets separately.

The table does not say how many tasks are needed. That belongs to coverage and
task quota planning.

## What this is not

- It is not a committed generator input; it is derived inside the run.
- It is not a task quota planning policy. `balance.yaml` is.
- It is not a coverage or balance report. The `checks` rows in `manifest.json`
  are.
- It is not a release file. It is not shipped in the release directory.
- It does not prove that the corpus contains enough instances.
- It is not the valid-task set.
