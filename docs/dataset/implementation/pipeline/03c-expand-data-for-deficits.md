# 03c — Expand data for deficits

**Parent:** [`03-enumerate-tasks.md`](03-enumerate-tasks.md).

**Purpose:** respond to quota deficits by looking for more or better data in a
bounded escalation, then loop back into planning and task construction.

## Input / output

- Input: the deficit ledger from `03b`, the current `ReleasePlan`, and program
  metadata.
- Output: a `DataRequest`, or an accepted miss.

`03c` is a loop back, not a terminal reconciliation step. It does not render
anything and does not select release rows.

## Deficit classes

Classify a deficit before expanding:

| Class | Response |
|---|---|
| More samples may help | Try more constructors, bindings, or parameter values on existing graphs. |
| Unused programs may help | Use unused programs in the current pool. |
| Reserve programs may help | Fetch and execute reserve programs. |
| Capability missing | Request supplemental `01b` selection by feature tag, collection, or family. |
| Constructor limitation | Fix `03b`; expanding data will not help. |
| Structural infeasibility | Fix the plan or support table; no data can supply it. |
| Release cap conflict | Reconcile the plan; expanding data will not remove the cap. |

## Data request

A `DataRequest` contains:

- the originating quota cell: step count, dimension, value;
- the missing graph capability;
- useful feature tags, collections, or family constraints;
- the number of programs requested;
- the maximum graph-build budget;
- the request reason and plan version.

`03c` makes the smallest request that can plausibly fill the deficit. It does not
request a random slice of the broader corpus.

## Escalation ladder

1. **Existing graphs, more sampling.** Try different constructors, bindings, and
   parameter values.
2. **Current pool, unused programs.** Use programs in the selected pool that have
   not yet been sampled.
3. **Reserve programs.** Fetch, normalize, and execute only the reserve IDs that
   can serve the deficit.
4. **Supplemental `01b` selection.** Extend the existing deterministic order or
   target metadata by feature tag, collection, or family.
5. **Accept and record the miss.** Stop when the expansion budget is exhausted or
   the remaining miss is accepted.

P2 may add a P-tier step for scale variation. P0 and P1 stay on C.

## Supplemental selection loop

```text
03c DataRequest
  → 01b supplemental selection
  → 01c fetch delta
  → 01d normalize delta
  → 02 build graphs for delta
  → 03a update family profiles and plan
  → 03b resume
```

The supplemental selection is an immutable `ProgramSelectionDelta`:

- do not re-run or replace the original selection;
- preserve existing family split assignments;
- a new program in an already-assigned family inherits that family's split;
- assign a split to a genuinely new family in `03a` before generation;
- fetch, normalize, and execute only the delta.

## Stop conditions

The loop stops when:

- the deficit is filled;
- the expansion budget is reached;
- the remaining deficit is structurally infeasible;
- the owner accepts the miss.

Every request, delta, and accepted miss is recorded with its plan version.

## Not here

Task construction, prompt rendering, release validation, and export.
