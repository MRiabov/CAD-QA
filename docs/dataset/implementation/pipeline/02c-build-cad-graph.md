# 02c — Build CAD graph

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** combine the static CadQuery model and execution result into the CAD
graph.

## Input / output

- Input: `StaticCadQueryModel` plus `ExecutionResult`.
- Output: `CadGraph`.

## Graph tables

`CadGraph` is three Parquet tables. Every table carries `program_id` and
`graph_schema_version`.

| Table | Fields |
|---|---|
| `nodes.parquet` | `node_id`, `node_type`, `state_id`, `operation_id`, `label`, `attributes` |
| `relations.parquet` | `relation_id`, `relation_type`, `from_node_id`, `to_node_id` |
| `measurements.parquet` | `measurement_id`, `subject_node_id`, `object_node_id`, `measurement_type`, `value`, `unit`, `evidence_kind`, `evidence_rule`, `evidence_refs`, `tolerance` |

`attributes` is a typed nested struct per graph node type, not a JSON string.
`object_node_id` is null for a measurement on one entity.
`evidence_kind` is `derived` or `measured`.

## Graph node and relation identity

- `node_id` is `program_id:node_type:local_id`.
- Operation nodes use the `operation_id` from `02a`.
- State nodes use the `state_id` from `02b`.
- Entity nodes use the in-state kernel handle or fingerprint from `02b`.
- `relation_id` is a deterministic hash of
  `(program_id, relation_type, from_node_id, to_node_id)`.

The graph includes a `cadquery_selector_result` graph node for each
`SelectorResult`. `selected_by` relations link an entity graph node to its
CadQuery selector result; `selected_from` links the CadQuery selector result to
its state. The CadQuery selector result carries a count measurement equal to the
number of `selected_by` edges.

## Behavior

- Join operations to shape snapshots by `operation_id`.
- Create entity graph nodes for each shape snapshot and relation records for
  operation order, containment, adjacency, provenance, and measurements.
- Map CadQuery selector handles to entity graph nodes in the same shape snapshot.
- Attach evidence at the same time as each measurement: derived or measured,
  the rule, and references.
- Compute operation effects from before/after shape snapshots.
- Skip failure tombstones; tasks that need the failed output are rejected.
- Reject ambiguous topology rather than guessing.

## Resolved questions

- **Q2.** *Resolved 2026-10-21.* Option C. Store a CadQuery selector-result
  entity plus `selected_by` membership edges. The result entity carries the set
  identity, its `selected_from` solid state, and its count; the edges carry
  membership for graph traversal. Both come from one extraction, and the graph
  builder enforces one invariant: the result count equals the number of its
  membership edges.

- **Q3.** *Resolved 2026-10-21.* Option C. Derive a measurement only when the
  program text fixes it and no later operation can change it: literals, operation
  counts, and similar syntax facts. Measure geometry and topology from CadQuery
  execution, including selector membership. Evidence records whether a
  measurement was derived or measured, the exact rule, and the references.

## Open questions

- What is the typed `attributes` schema for each graph node type?
- Are kernel handles stable enough for `node_id`, or should entity graph nodes
  use a geometric fingerprint?
- If a CadQuery selector handle cannot be mapped to an entity graph node, should
  the graph be rejected, or should only that CadQuery selector result be dropped?
