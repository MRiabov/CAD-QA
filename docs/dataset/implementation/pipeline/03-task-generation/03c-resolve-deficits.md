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
only loop that pays fetch, normalization, and execution cost. Promotion of a
reserve program is the slow loop: reserve rows have no graph until promotion, and
the fast loop uses only the graphs of active programs.

## Stop rule

An expansion round adds at most 20% of the current program pool. After three
rounds, stop and record an `AcceptedMiss` for each unfilled quota target.

`AcceptedMiss` records the quota target, the remaining count, the reason, the
owner, and the plan version. The round count and the growth cap are plan fields,
not constants in `03c`: `03a` allocate task quotas stamps both from `expansion`
in `balance.yaml`.

## Deficit classes

`DeficitClass` is the closed set of obstacles a deficit can hit. It is owned
here: `03b` records a class directly, and `03c` classifies what `03a` reports.

| Class | Meaning | Response |
|---|---|---|
| `capability_deficit` | No active program's census has the capability the quota target needs. | Census query, then `ProgramRequest` to `01b`. |
| `probe_deficit` | The bound state has no surviving point probe, so it supports no membership task. | Drop membership for that state and record the deficit. No request. |
| `capacity_deficit` | A capable program exists, but family quota, split capacity, or assignment leaves no room. | `ProgramReassignmentRequest` to `03a`; `ProgramRequest` only when the split itself is short. |
| `construction_deficit` | The construction batch was underfilled, or the rejection rate is high. | `ProgramReassignmentRequest` to raise the attempt budget; a persistent high rate is a `03b` fix. |
| `constructor_deficit` | The constructor cannot express the target at all. | Fix `03b`; neither loop helps. |
| `plan_conflict` | A plan cap or bound blocks the target. | Reconcile the plan; expanding data will not remove the cap. |
| `structural_deficit` | No valid task can express the target at that task reasoning step count. | Fix the plan or the task-definition rules. |

### Classifying an allocation detail

`03a` records the allocation detail that produced the deficit; it does not choose
the class. The mapping is:

| Allocation detail | Class |
|---|---|
| `coverage_infeasible`, `answer_meaning_infeasible` | `structural_deficit` |
| `cap_conflict` | `plan_conflict` |
| `split_capacity_short`, `family_quota_short`, `family_quota_target_conflict` | `capacity_deficit` |
| `quota_target_family_unassigned` | `capability_deficit` when no active census has the capability, otherwise `capacity_deficit` |

### Capability lookup

`capability_deficit` and `capacity_deficit` differ only in whether the pool has
the capability, so the census decides:

1. Query every active program's census for the quota target's capability.
2. At least one program has it: `capacity_deficit`. The graph exists and the
   plan did not use it.
3. No program has it: `capability_deficit`. The request carries the missing
   capability and the census version it was checked against.

The census is a filter, not an oracle. A capability that is present but yields no
valid task is a `construction_deficit` or a `constructor_deficit`, not a
`capability_deficit`.

### Probe deficits stay local

A missing probe is per state. `03b` records `probe_deficit` and drops membership
for that state; one state without a probe is not a reason to fetch programs.

`03c` escalates only when no active program's census reports a state with a
surviving probe. Then every membership quota target is a `capability_deficit`,
and the request asks for programs whose graphs contain a probe.

A pair that is not emitted is not a deficit class. A pair outside the pair
emission rule is not a candidate, and a state above `max_state_entities` is
rejected at graph construction, so neither reaches `03c`. An underfilled pair
target is classified by the census like any other target.

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
