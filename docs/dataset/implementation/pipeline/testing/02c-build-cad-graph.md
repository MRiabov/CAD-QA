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
  attributes and measurements `graph-content.md` sections 2 and 4 declare;
- every face carries its `face_surface_kind`, its `position` set (every
  bounding-box extreme plane it lies in), and its `outward_normal`, which is null
  exactly when the face is not planar;
- `has_face`, `has_edge`, and `has_vertex` derived from the topology records, and
  `adjacent_to` derived from shared topology;
- per-entity measurements total over their scope: every face has an area, every
  edge a length, every path segment a length, every vertex a centroid and a
  bounding box, every CadQuery profile an area, every region a volume, an area, a
  bounding box, and a centroid, and every solid state a volume and a bounding box;
- the final state's 15 edges are all present, including the seam edge;
- every relation and measurement row carries CAD graph evidence: `derived` with
  its rule and references, or `measured` with the kernel call.

`test_02c_pair_emission_completeness` — for every pair measurement, and every
P1 pair relation, in the state, recompute the expected pair set from the entity
tables:

1. derive the reference classes of the state — face surface kind, position, and
   provenance — and the candidate endpoints of the declared endpoint entity
   category;
2. for a sparse kind, take every true pair; for a dense kind, take the cross
   product of each class within `max_anchor_class_size` and the candidates;
3. drop a pair whose two endpoints are the same entity, and reduce to unordered
   pairs;
4. compare with the emitted rows as a set, with the endpoints in canonical id
   order.

A missing pair fails. So does an extra pair: it is a predicate the graph does not
support, and a clue built from it would be a fact about nothing.

Three edge cases are asserted separately. A class with no member emits no pair. A
class with several members within the bound emits its whole cross product: that
is the case the single-endpoint rule used to drop, and it is why the bound
exists. A class over the bound emits no pair row for a dense kind and does not
reject the program; the test reads the recorded constant, asserts the absence,
and asserts that the clue which needs the class fails at `03b` with the bound as
its reason.

`test_02c_state_size_rejection` — a program whose state exceeds
`max_state_entities` is rejected with the state, the count, the limit, and
disposition `by_design`; no partial graph is written. The limit is read from the
recorded scope constant, not recomputed.

`test_02c_report_rows_are_capability_cells` — every `GraphCompletenessReport`
row carries the identity the
[must-extract capability set](../extraction/validation.md#the-must-extract-capability-set)
uses: `entity:<node_kind>`,
`relation:<relation_kind>@<subject_kind>-><object_kind>`, and
`measurement:<measurement_kind>@<subject_kind>`. A program that realizes a
declared cell reports `actual_count > 0` for it, and a realized cell outside the
declared set is reported with its own identity rather than folded into another
row. A row kind the set cannot name is a contract gap, so the test fails rather
than recording an unclassified row.

**TDD pin:** pins the seam edge as a graph entity, the pair emission rule as a set
equality, and the state-size rejection before `02c` exists.

## Failure-mode tests

- `test_02c_missing_per_entity_measurement` — a missing area or length rejects the
  graph. It is a graph defect, not a data condition.
- `test_02c_over_bound_reference_class` — covered by the pair test above, and
  asserted on the row count, not on a warning.
- `test_02c_tolerance_override_recorded` — a relation with an overridden tolerance
  carries the tolerance and the reason on its row.
- `test_02c_unmeasured_predicate` — a relation or measurement with neither a rule
  nor a kernel call is not written; the graph is rejected.

## What this does not prove

- That the box-with-hole report is the chain's report. The box-with-hole graph
  and its `GraphCompletenessReport` are built by this test; the chain's report
  covers a fixture-pool program.
- That a task exists for the graph. That is
  [`03b-construct-task-definitions.md`](03-task-generation/03b-construct-task-definitions/README.md).
- That every declared capability is realized somewhere in the pool. That is
  [`05`'s `extraction_capability_coverage`](../05-validate-and-export-release/release-checks.md#extraction-capability-coverage).
- That the support table is complete. That is
  [`00-support-tables.md`](00-support-tables.md).
