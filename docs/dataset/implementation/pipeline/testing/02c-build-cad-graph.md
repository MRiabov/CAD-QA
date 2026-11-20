# 02c build CAD graph — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../02c-build-cad-graph.md`](../02c-build-cad-graph.md),
with the emission rules in
[`../../../requirements/graph-content.md`](../../../requirements/graph-content.md)
and the derivation in [`../extraction/graph-construction.md`](../extraction/graph-construction.md).

## Happy-path integration test (test-first, adversarial)

`test_02c_graph_happy_path_adversarial` — builds the box-with-hole graph from the
real `02b` result and asserts the persisted tables read back through the reader
`03b` construct task definitions uses.

**Given** the box-with-hole runtime result.

**When** `02c` builds the graph.

**Then** assert the persisted graph:

- one entity row per face, edge, and vertex, with the category and the
  measurements `graph-content.md` section 2 declares;
- `has_face`, `has_edge`, and `has_vertex` derived from the topology records, and
  `adjacent_to` derived from shared topology;
- per-entity measurements total over their scope: every face has an area, every
  edge a length, every path segment a length, and every solid state a volume and
  a bounding box;
- the final state's 15 edges are all present, including the seam edge;
- every relation and measurement row carries CAD graph evidence: `derived` with
  its rule and references, or `measured` with the kernel call.

`test_02c_pair_emission_completeness` — for every pair relation and pair
measurement in the state, recompute the expected pair set from the entity tables:

1. derive the named endpoints of the state — face surface kind, position, and
   provenance — and the candidate endpoints of the declared endpoint entity
   category;
2. compute the cross product, drop a pair whose two endpoints are the same
   entity, and reduce to unordered pairs;
3. compare with the emitted rows as a set, with the endpoints in canonical id
   order.

A missing pair fails. So does an extra pair: it is a predicate the graph does not
support, and a clue built from it would be a fact about nothing.

Two edge cases are asserted separately. A name that resolves to zero entities
emits no pair, and so does a name that resolves to several. The test names a
face surface kind the program does not have, and a position name two faces share.
Both names exist only as a lookup, so neither creates a pair row.

`test_02c_state_size_rejection` — a program whose state exceeds
`max_state_entities` is rejected with the state, the count, and the limit, and no
partial graph is written. The limit is read from the recorded scope constant, not
recomputed.

**TDD pin:** pins the seam edge as a graph entity, the pair emission rule as a set
equality, and the state-size rejection before `02c` exists.

## Failure-mode tests

- `test_02c_missing_per_entity_measurement` — a missing area or length rejects the
  graph. It is a graph defect, not a data condition.
- `test_02c_unresolvable_named_endpoint` — covered by the pair test above, and
  asserted on the row count, not on a warning.
- `test_02c_tolerance_override_recorded` — a relation with an overridden tolerance
  carries the tolerance and the reason on its row.
- `test_02c_unmeasured_predicate` — a relation or measurement with neither a rule
  nor a kernel call is not written; the graph is rejected.

## What this does not prove

- That a task exists for the graph. That is
  [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md).
- That the support table is complete. That is
  [`00-support-tables.md`](00-support-tables.md).
