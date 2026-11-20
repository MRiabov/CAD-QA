# Clue form support table

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-20. Contract for the `clue-form-by-step` release
artifact.

## Purpose

The table records which clue forms a graph can support at each task reasoning
step count. It is the input to coverage (`DS-37`) and to the chain search, so the
generator never asks for a clue form that cannot exist at that step count.

## What a cell is

A cell is one `(task reasoning step count, clue type, clue operand form)`.

| Field | Meaning |
|---|---|
| `task_reasoning_step_count` | 1 to the release maximum. |
| `clue_type` | property, relation, comparison, aggregation, or provenance. |
| `clue_operand_form` | `named`, `selected`, `aggregated`, or `cross_state`. |
| `support` | `supported`, `structurally_impossible`, `needs_graph_support`, or `p2`. |
| `reason` | Why the cell is not `supported`; required for every other state. |

## Structural rules

These hold before any graph is inspected (`DS-31`):

- **The property clue type has no operand form.** A property clue constrains the
  candidate set directly, so its operand form is absent and no cell exists for
  it.
- **`selected` needs an earlier clue.** Step count 1 has no cell for it.
- **`aggregation` with an `aggregated` reference is degenerate.** It is
  aggregation over an aggregate, and it is written as two clues.
- **`cross_state` waits for P2.** P0 and P1 tasks use the final solid state
  (`DS-34`), so every `cross_state` cell is `p2` until a second state is in scope.

## Graph-dependent rules

The rest is derived from the graph coverage check in
`docs/dataset/requirements/graph-content.md` section 8:

- a form that needs a relation the graph does not carry is `needs_graph_support`;
- a form that needs a measurement the graph cannot measure is
  `needs_graph_support`;
- a cell that passes both is `supported`.

The table is rebuilt whenever the graph, the support rules, or the release scope
change. It is versioned with the graph artifact, and a mismatch is rejected
rather than used.

## Consumers

| Consumer | Use |
|---|---|
| `03a` | Requires coverage of every `supported` cell at each step count (`DS-37`). |
| `03b` | Skips `structurally_impossible` and `needs_graph_support` cells during the search. |
| `03c` | Turns an underfilled `supported` cell into a deficit, and a `needs_graph_support` cell into a graph gap. |
| `05` | Reports the table and the coverage result together. |

## Failure

A `supported` cell with zero accepted tasks is a coverage gap, not a balance
problem. A `needs_graph_support` cell is a graph gap and is reported with the
missing graph element. A `structurally_impossible` cell is not a gap and is never
counted against coverage.
