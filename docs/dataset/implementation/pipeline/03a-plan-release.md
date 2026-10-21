# 03a — Plan release

**Parent:** [`03-enumerate-tasks.md`](03-enumerate-tasks.md).

**Purpose:** turn release targets and the bounded program pool into a quota plan,
family assignment, split assignment, and sampling budget before task definitions
are generated.

## Input / output

- Input: CAD graphs for the selected program pool, program metadata, the
  [task reasoning step support tables](../task-step-support.md), release
  targets, and `ReplanRequest` records from `03c`.
- Output: `ReleasePlan`.

## Release plan

`ReleasePlan` contains:

| Field | Meaning |
|---|---|
| `plan_version`, `seed` | Version and deterministic ordering seed. |
| `step_quotas` | Target task count for each task reasoning step count. |
| `quota_cells` | Dimension values with minimum, target, maximum, and priority. |
| `clue_quotas` | Clue type counts over clue occurrences. |
| `family_profiles` | Graph capabilities and capacity per CADEvolve program family. |
| `family_assignment` | Family to split, task budget, and assigned quota cells. |
| `attempt_budgets` | Generation attempts allowed per cell and family. |
| `expansion_tier` | Current data tier before a deficit triggers `03c`. |

The plan is a target. It does not prove that the corpus can supply every cell.

## Quota cells

A quota cell is `(step count, dimension, value)`. It records:

- `minimum`: coverage requirement;
- `target`: desired count;
- `maximum`: balance or cap limit;
- `priority`: coverage first, then balance, then volume.

Plan four separate dimensions:

- target category;
- clue type;
- answer meaning;
- answer format.

Do not create a full target × clue × meaning × format cross-product. The
requirements are marginal: coverage and balance at each step count, not every
joint combination. A task contributes to one target category, one answer format,
one answer meaning, one step count, and one or more clue occurrences.

Clue quotas are over clue occurrences, because one task has several clues.

## Initial allocation

1. Allocate the step mix: 1 step 5%, 2 15%, 3 40%, 4 25%, 5 15%.
2. Allocate minimum coverage for every feasible value at each step count.
3. Allocate remaining tasks by release shares and the conditional release share,
   using largest-remainder rounding.
4. Apply minimum and maximum bounds.
5. Allocate clue quotas over the planned clue occurrences.
6. Reserve capacity for warmup tasks, CAD model caps, and correct-answer caps.
7. Record any cell whose minimum cannot be allocated.

The conditional release share is allocated from the global targets and then
filled from available data. It is not recomputed after seeing the whole
valid-task set.

## Family profiles

Build a family profile from the graphs in the selected pool:

- CADEvolve program family and program count;
- split status, if already assigned;
- available target categories;
- available clue predicates and relations;
- available measurements and answer meanings;
- available answer formats;
- approximate chain depth;
- task budget per program and family;
- estimated yield per dimension cell.

Profiles describe capability, not a list of all tasks. A bounded probe may
construct a small deterministic sample of task definitions per family to improve
yield estimates. That is sampling, not full enumeration.

## Family assignment

Assign families before task construction because a family cannot cross splits.

1. Treat each family as atomic.
2. Estimate family capacity from program count, per-program task cap, and the
   probe yield.
3. Assign families to train, validation, and test by deterministic greedy
   balancing, with largest-remainder rounding for the approximate 70/15/15 split.
4. Use `sha256(seed || family_id)` for ordering and tie-breaks.
5. Assign quota cells scarcity-first: rare values first, then common values.
6. Prefer families with the required capability and remaining budget.
7. Keep a reserve of families for `03c`.

A family receives a task budget and a set of cells, not one task type. If it
cannot fill an assigned cell, the remainder returns to the plan.

Exact split and cell assignment is a bin-packing problem and can be hard. The
contract does not require an exact optimum. Deterministic greedy allocation,
reserves, and recorded misses are sufficient.

## Replanning

`03a` accepts a `ReplanRequest` from `03c` when the current graphs can supply a
deficit but the plan does not use them.

It can:

- assign an unassigned family to a quota cell;
- move task budget from a saturated family to one with spare capacity;
- relax an internal family budget;
- change a quota cell within its release bounds.

It does not fetch, normalize, or execute. It increments the plan version and
returns control to `03b`.

## Deficits

A cell enters the deficit ledger when:

- its minimum or target is not met after the attempt budget;
- the current graphs lack the required capability;
- family budgets or release caps block it;
- the requested value is structurally infeasible.

`03c` decides whether to sample more from existing graphs, use unused or reserve
programs, request a supplemental `01b` selection, or accept the miss.

## Resolved questions

- **Q1.** *Resolved 2026-10-21.* Use quota planning, not enumerate-and-cut.
  Select and sample into a release plan.
- **Q3.** *Resolved 2026-10-21.* Allocate the conditional release share from the
  global targets before task construction, then fill from available data.

## Not here

Task definition validity, clue predicates, answer resolution, prompt rendering,
and release validation.
