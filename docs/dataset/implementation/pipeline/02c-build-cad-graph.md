# 02c — Build CAD graph

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** combine the static CadQuery model and execution snapshots into the
CAD graph.

## Input / output

- Input: static CadQuery model plus `ExecutionResult`.
- Output: `CadGraph`.

## Behavior

- Build graph entities and relations in the shapes the requirements define.
- Attach measurements to entities and pairs.
- Attach evidence at the same time as each measurement: measured or derived,
  the rule, and references. There is no separate evidence pipeline stage.
- Skip failure tombstones; tasks that need the failed output are rejected.
- Reject ambiguous topology rather than guessing.

## Resolved questions

- **Q2.** *Resolved 2026-10-21.* Option C. Store a CadQuery selector-result
  entity plus `selected_by` membership edges. The result entity carries the set
  identity, its `selected_from` solid state, and its count; the edges carry
  membership for graph traversal. Both come from one extraction, and the graph
  builder enforces one invariant: the result count equals the number of its
  membership edges.

## Open questions

- **Q3.** Which measurements can be derived exactly from the program text, and
  which must always be measured by CadQuery?
  - **Option A — measure everything.** Simple, but loses exact syntax evidence.
  - **Option B — derive everything possible from syntax.** Fast, but wrong when
    later operations change the geometry.
  - **Option C — derive only exact syntax values; measure geometry.** Use exact
    rules for literals, operation counts, and selector membership; measure
    volumes, areas, distances, and topology after operations.
  - **Recommendation:** C, with the evidence recording which path was used.
