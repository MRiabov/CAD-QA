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
[`pipeline/03b-construct-task-definitions.md`](pipeline/03b-construct-task-definitions.md). They are not
hand-authored, and `03` does not read them to decide what to attempt.

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

For a dimension value, support is an existential:

```text
support(value, s) = there exists a feasible derivation of exactly s steps
```

Dependency depth is a lower bound. A value may have feasible derivations at more
than one step count. The table records feasibility; the release report records
availability and count.

`implementation_scope` comes from the product priority declarations. It is not
derived from the graph.

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
is structurally supported. Unsupported rows use one of:

- `step_count_too_low`;
- `prior_candidates_required`;
- `reference_entity_required`;
- `answer_format_incompatible`;
- `target_not_identifiable`;
- `ambiguous_target`;
- `no_valid_construction`.

The four files are generated from the task-definition rules. `05` copies them
into the release and `manifest.json` records their schema versions and hashes.

## Validation use

For each task reasoning step count and dimension:

1. Read the feasible values from the task reasoning step support table.
2. Read the values present in the release and their counts.
3. Report a coverage gap for every feasible value with zero tasks.
4. Report a specification defect for every released value marked infeasible.
5. Report balance against the release targets separately.

The table does not say how many tasks are needed. That belongs to coverage and
release planning.

## What this is not

- It is not a generator input.
- It is not a release planning policy.
- It is not evidence that the corpus contains enough instances.
- It is not the valid-task set.
