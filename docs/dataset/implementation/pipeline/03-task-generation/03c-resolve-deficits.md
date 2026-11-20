# 03c — Resolve deficits

**Parent:** [`03-task-generation.md`](../03-task-generation.md).

**Purpose:** respond to quota deficits with the cheapest effective loop:
replanning the current data, or expanding the program pool.

## Input / output

- Input: the deficit ledger from `03b`, the current `TaskQuotaPlan`, current family
  profiles, and program metadata.
- Output: a `ProgramReassignmentRequest`, a `ProgramRequest`, or an accepted miss.

`03c` is a controller, not a terminal reconciliation step. It does not render
anything and does not write dataset release rows.

## Two loops

There are two distinct loops with different costs.

### Fast loop: replan current data

```text
03c ProgramReassignmentRequest
  → 03a residual replan
  → 03b resume
```

This loop uses the graphs and families already in the pool. It does not fetch or
execute anything. `03a` can move quota to unassigned families, relax an internal family
quota, or try a different family for a quota target.

### Slow loop: expand the program pool

```text
03c ProgramRequest
  → 01b supplemental selection
  → 01c fetch delta
  → 01d normalize delta
  → 02 build graphs for delta
  → 03a update family profiles and residual plan
  → 03b resume
```

This loop adds programs or families that were not in the current pool. It is the
only loop that pays fetch, normalization, and execution cost.

## Deficit classes

| Class | Response |
|---|---|
| Construction batch underfilled | `ProgramReassignmentRequest` to `03a`; adjust the construction attempt budget or family assignment. |
| High rejection rate | Fix the constructor or validity rule in `03b`; expanding data will not help. |
| Current pool has unused capacity | `ProgramReassignmentRequest` to `03a`; reassign families or quotas. |
| Current family quota or cap blocks the quota target | `ProgramReassignmentRequest`; change the plan, not the data. |
| Reserve or new capability needed | `ProgramRequest` to `01b`; expand the pool. |
| Constructor limitation | Fix `03b`; neither loop helps. |
| Structural infeasibility | Fix the plan or support table; no data can supply it. |
| Plan cap conflict | Reconcile the plan; expanding data will not remove the cap. |

## ProgramReassignmentRequest

Use `ProgramReassignmentRequest` when the current graphs can supply the deficit
but the current plan does not use them.

It contains:

- the originating quota target: task reasoning step count, quota dimension, dimension value;
- the current family assignment and quota that block the quota target;
- accepted and remaining counts for the affected quota targets, families, and
  task reasoning step counts;
- unassigned families or unused capacity that could help;
- the requested change: quota target, family assignment, or internal quota;
- the retry budget;
- the plan version.

`03a` applies the residual change, increments the plan version, and returns control to
`03b`. It does not fetch, normalize, or execute.

## ProgramRequest

Use `ProgramRequest` when the current pool cannot supply the deficit.

It contains:

- the originating quota target: task reasoning step count, quota dimension, dimension value;
- the missing graph capability;
- accepted and remaining counts for the affected quota targets, families, and
  task reasoning step counts;
- useful feature tags, collections, or family constraints;
- whether to extend the existing selection order or target metadata;
- the number of programs requested;
- the maximum graph-build budget;
- the request reason and plan version.

`01b` answers with an immutable `ProgramSelectionDelta`. It does not replace the
original selection. Existing family split assignments stay fixed; a new program
in an assigned family inherits its split. A genuinely new family is assigned in
`03a` before generation.

## Escalation order

`03c` tries the cheapest response first:

1. `ProgramReassignmentRequest` to `03a`; adjust family assignment or
   construction attempt budget using current graphs.
2. `ProgramRequest` to `01b`; expand the program pool.
3. Accept and record the miss.

The fast loop comes first because reassigning existing families is cheaper than
fetching and executing more programs. The slow loop is used only when the current
pool truly lacks the capability or capacity.

## Stop conditions

The loop stops when:

- the deficit is filled;
- the expansion budget is reached;
- the remaining deficit is structurally infeasible;
- the owner accepts the miss.

Every request, delta, and accepted miss is recorded with its plan version.

## Not here

Task construction, prompt rendering, release validation, and export.
