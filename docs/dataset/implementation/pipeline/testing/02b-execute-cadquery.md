# 02b execute CadQuery — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../02b-execute-cadquery.md`](../02b-execute-cadquery.md).

## Happy-path integration test (test-first, adversarial)

`test_02b_execution_happy_path_adversarial` — runs the box-with-hole fixture
program in a real child process and asserts the runtime result read back through
the reader `02c` build CAD graph uses.

**Given** the normalized box-with-hole program and its
`CadQueryAstExtractionResult`.

**When** `02b` runs it with the pinned CadQuery and OCP versions.

**Then** assert the persisted `CadQueryRuntimeExtractionResult`:

- one `shape_snapshots` row per solid-producing assignment, each with `volume`,
  `bbox_min`, `bbox_max`, `centroid`, and the face, edge, and vertex counts. The
  final state has 15 edges, not 14: the cylindrical face carries a periodic seam
  edge, and the seam is a real edge, not a duplicate of a circular edge.
- `entity_table_ref` resolves to one row per face, edge, and vertex, each with a
  stable `entity_id` that is a hash of `state_id`, entity category, and the
  canonical geometric fingerprint.
- `selector_results` has one row per evaluated selector, and its
  `selected_entity_ids` and `count` agree with the entity table.
- `effect_deltas` has one row per operation, with the before and after state ids
  and the measured volume, bounding-box, and topology deltas.
- `final_state_id` names the last solid-producing state.

`test_02b_point_probes_are_reproducible` — for every `point_probes` row, recompute
`is_inside(state, point)` and compare the classification, and recompute
`distance_to_face_surface` within kernel noise. The first probe of each state is
the Shape snapshot centroid on the 0.1 mm grid. The second probe is at most
`sqrt(3) × 1`
mm plus one grid step from the nearest face and may lie outside the bounding box.
When both probes survive they carry opposite labels. Running the same program
twice produces the same two points, because the draw is seeded from
`program_sha256`, `state_id`, and `probe_index`.

A probe within the clear-case margin is absent. The test feeds the probe filter
constructed rows below, at, and above `100 × 1e-6 × d`, `d` the bounding-box
diagonal, and asserts only the rows above survive. It does not need a degenerate
program: a well-formed solid keeps its centroid probe, so no realistic program
reaches zero probes.

`test_02b_failure_tombstones` — a program that raises, one that exceeds the 30
second wall clock, and one that exceeds 2 GiB each produce a failure tombstone
naming the failure, with no partial success result. A re-run produces the same
tombstone.

**TDD pin:** pins the seam edge, the probe count and centroid rule, the margin
filter, and the three failure tombstones before `02b` exists.

## Failure-mode tests

- `test_02b_rejects_unaccepted_ast` — a statement outside the accepted `02a`
  subset is not executed, and the failure names the statement.
- `test_02b_entity_id_collision` — two entities in one state with the same
  fingerprint reject the program as ambiguous topology, and no result is written.
- `test_02b_no_partial_state` — a crash in the middle of the program leaves no
  `shape_snapshots` row for the incomplete state.
- `test_02b_version_pin` — a changed CadQuery or OCP version changes the
  environment record and therefore the result hash; a cached result is not
  reused across versions.

## What this does not prove

- That the graph is correct. That is
  [`02c-build-cad-graph.md`](02c-build-cad-graph.md).
- That a membership answer is valid. That is
  [`03b-construct-task-definitions.md`](03-task-generation/03b-construct-task-definitions/README.md).
