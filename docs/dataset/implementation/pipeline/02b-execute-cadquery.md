# 02b — Execute CadQuery

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** run the normalized program and capture shape snapshots and selector
results, or a failure tombstone when execution fails.

## Input / output

- Input: normalized program text plus `StaticCadQueryModel`.
- Output: `ExecutionResult`, either success or a failure tombstone.

## Execution boundary

- Run each program in a child Python process. This is process isolation for
  crash cleanup and resource control, not a security sandbox.
- Treat CADEvolve programs as trusted build inputs; do not add a network,
  filesystem, or prompt-injection boundary.
- Pin the CadQuery and OCP versions and record them in the result.
- Use stable defaults: 30 seconds wall clock and 2 GiB address space per child
  process. A changed limit is a new execution environment and a new cache key.
- Kill the child on timeout and record a `timeout` failure. A memory-limit failure
  records a `memory` failure.
- Execute only the accepted static subset from `02a`.
- Execute top-level statements in program order.

## Success result

`ExecutionSuccess` contains:

- `program_id`, `program_sha256`, `static_model_sha256`, and the environment record;
- `operation_recordings`: one per static operation;
- `shape_snapshots`: one per solid-producing assignment;
- `workplane_frames`: one per workplane-producing operation;
- `selector_results`: one per evaluated CadQuery selector;
- `operation_effects`: before/after state pairs and measured deltas;
- `final_state_id`;
- `execution_result_sha256`.

Each `ShapeSnapshot` contains:

- `state_id` and `operation_id`;
- `shape_hash`;
- `solid`, `valid`;
- `volume`, `bbox_min`, `bbox_max`, and `centroid`;
- `face_count`, `edge_count`, and `vertex_count`;
- `entity_table_ref`, the canonical entity table for this state.

The entity table carries one row per face, edge, and vertex with a stable
`entity_id`. The ID is a hash of `state_id`, entity category, and a canonical
geometric fingerprint:

- vertex: point;
- edge: endpoints and length;
- face: centroid, area, normal, and bounding box.

Raw kernel handles are internal to the child process and are never persisted. Two
entities in one state with the same fingerprint are a collision; reject the
program as ambiguous topology.

Each `SelectorResult` contains:

- `selector_result_id` and `selector_id`;
- `state_id`;
- `selected_entity_ids`, the stable entity IDs;
- `count`.

Each `OperationEffect` contains:

- `operation_id`;
- `before_state_id` and `after_state_id`;
- volume change, bounding-box change, and topology counts.

## Field contracts

The complete runtime algorithm is in
[`extraction/cadquery/runtime.md`](extraction/cadquery/runtime.md). Field sets and
canonical rules are in
[`extraction/cadquery/states.md`](extraction/cadquery/states.md),
[`extraction/cadquery/solids.md`](extraction/cadquery/solids.md),
[`extraction/cadquery/topology.md`](extraction/cadquery/topology.md),
[`extraction/cadquery/selectors.md`](extraction/cadquery/selectors.md),
[`extraction/cadquery/effects.md`](extraction/cadquery/effects.md),
[`extraction/canonicalization.md`](extraction/canonicalization.md), and
[`extraction/validation.md`](extraction/validation.md).

## Failure tombstone

`ExecutionFailure` contains:

- `program_id`, `program_sha256`, `operation_id` when known, and `error_kind`;
- `error_kind` from [`extraction/validation.md`](extraction/validation.md),
  including `timeout`, `memory`, `cadquery_exception`, `recorder`,
  `non_solid_result`, `missing_state`, and `fingerprint_collision`;
- `message`, `source_line`, and `source_span` when known;
- environment record;
- `cache_key`.

A failed result is never passed to graph assembly as a measurable state.

## Caching

The cache key includes the normalized program hash, `static_model_sha256`,
extractor and canonicalization versions, CadQuery and OCP versions, the execution
environment, timeout, and memory limit. A failure tombstone is reusable for the
same key. A change to the static model or canonicalization is a cache miss.

## Resolved questions

- **Sandbox.** *Resolved 2026-10-21.* No security sandbox. Run each program in a
  child process with a timeout and memory limit. CADEvolve programs are trusted
  build inputs, so network and filesystem isolation are not requirements.
- **Execution limits.** *Resolved 2026-10-21.* Use 30 seconds and 2 GiB per
  child as stable defaults.
- **Entity identity.** *Resolved 2026-10-21.* Do not persist kernel handles. Use
  the stable geometric entity ID emitted by `02b`; reject fingerprint collisions.
- **CadQuery selector failure.** *Resolved 2026-10-21.* A CadQuery selector exception
  rejects the whole program. A valid CadQuery selector with zero matches is a successful
  result with count 0.
- **Runtime capture algorithm.** *Resolved 2026-10-22.* The exact instrumentation
  ABI, capture classes, state/CadQuery selector/entity/effect algorithms, final-state rule,
  and failure taxonomy are in
  [`extraction/cadquery/runtime.md`](extraction/cadquery/runtime.md).
