# 02b — Execute CadQuery

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Execution and resume:** [`../run-contract.md`](../run-contract.md).

**Purpose:** run the normalized program and capture shape snapshots and selector
results, or a failure tombstone when execution fails.

## Input / output

- Input: normalized program text plus `CadQueryAstExtractionResult`.
- Output: `CadQueryRuntimeExtractionResult`, either success or a failure tombstone.

## Execution boundary

- Run each program in a fresh child process forked from a worker that has
  already imported CadQuery and OCP. This is process isolation for crash cleanup
  and resource control, not a security sandbox; the library import is worker
  startup, not per-program work. See
  [`extraction/cadquery/algorithm/runtime.md`](extraction/cadquery/algorithm/runtime.md#execution-boundary).
- The preload exists because the CadQuery/OCP import costs 2.1–2.8 s and about
  450 MiB of resident memory on the reference host. Measure it once per
  implementation scope and record it with the run; do not re-measure it per
  program.
- Treat CADEvolve programs as trusted build inputs; do not add a network,
  filesystem, or prompt-injection boundary.
- Pin the CadQuery and OCP versions and record them in the result.
- Use stable defaults: 30 seconds wall clock and a 2 GiB address-space budget
  per child process. The 30-second clock starts at the child's ready signal. The
  memory budget is above the preloaded baseline: measure the preloaded worker's
  address space once and add the 2 GiB budget, so the preload is not charged
  twice. A changed limit is a new execution environment and a new cache key.
- A child that does not signal ready within 10 seconds is killed and recorded as
  an `internal` failure. The ready timeout is a fixed constant, outside the
  30-second execution budget.
- Kill the child on timeout and record a `timeout` failure. A memory-limit failure
  records a `memory` failure.
- A worker has one child in flight at a time. With a shard pass, the number of
  concurrent children is the number of active shards
  ([`run-contract.md`](../run-contract.md#45-concurrency)).
- Execute only the accepted AST subset from `02a`.
- Execute top-level statements in program order.

## Success result

`CadQueryRuntimeExtractionSuccess` contains:

- `program_id`, `program_sha256`, `ast_extraction_result_sha256`, and the environment record;
- `operation_recordings`: one per AST operation;
- `shape_snapshots`: one per solid-producing assignment;
- `workplane_frames`: one per workplane-producing operation;
- `selector_results`: one per evaluated CadQuery selector;
- `effect_deltas`: before/after state pairs and measured deltas;
- `point_probes`: one or two classified points per solid state;
- `final_state_id`;
- `runtime_extraction_result_sha256`.

Each `ShapeSnapshot` contains:

- `state_id` and `operation_id`;
- `shape_hash`;
- `solid`, `valid`;
- `volume`, `bbox_min`, `bbox_max`, and `centroid`;
- `face_count`, `edge_count`, and `vertex_count`;
- `entity_table_ref`, the canonical entity table for this state.

The entity table carries one row per face, edge, and vertex with a stable
`entity_id` and its `fingerprint_sha256`. The ID is a hash of `state_id`, entity
category, and the canonical geometric fingerprint; `fingerprint_sha256` is the
hash of that fingerprint:

- vertex: point;
- edge: endpoints and length;
- face: centroid, area, normal, and bounding box.

Raw kernel handles are internal to the child process and are never persisted. Two
entities in one state with the same fingerprint are a collision; reject the
program as ambiguous topology.

Each `CadQuerySelectorResult` contains:

- `selector_result_id` and `selector_id`;
- `state_id`;
- `selected_entity_ids`, the stable entity IDs;
- `count`.

Each `PointProbe` contains:

- `point_probe_id` and `state_id`;
- `point`, in the program frame;
- `location`, `inside` or `outside`;
- `distance_to_surface`, measured to the nearest face;
- `classifier` and the margin used.

A probe within the clear-case margin is not emitted. The centroid probe is the
state centroid already measured in the Shape snapshot; the second probe is a seeded
point in the state bounding box.

Each `CadFeatureSolidStateEffectDelta` contains:

- `operation_id`;
- `before_state_id` and `after_state_id`;
- volume change, bounding-box change, and topology counts.

## Field contracts

The complete runtime algorithm is in
[`extraction/cadquery/algorithm/runtime.md`](extraction/cadquery/algorithm/runtime.md). Field sets and
canonical rules are in
[`extraction/cadquery/features/states.md`](extraction/cadquery/features/states.md),
[`extraction/cadquery/features/entities.md`](extraction/cadquery/features/entities.md),
[`extraction/cadquery/features/topology.md`](extraction/cadquery/features/topology.md),
[`extraction/cadquery/features/selectors.md`](extraction/cadquery/features/selectors.md),
[`extraction/cadquery/features/effects.md`](extraction/cadquery/features/effects.md),
[`extraction/cadquery/features/evidence.md`](extraction/cadquery/features/evidence.md),
[`extraction/canonicalization.md`](extraction/canonicalization.md),
[`extraction/runtime-schema.md`](extraction/runtime-schema.md),
[`extraction/cadquery/algorithm/geometry-classification.md`](extraction/cadquery/algorithm/geometry-classification.md),
and [`extraction/validation.md`](extraction/validation.md).

## Failure tombstone

`FailureTombstone` contains:

- `program_id`, `program_sha256`, `operation_id` when known, and `error_kind`;
- `error_kind` from [`extraction/validation.md`](extraction/validation.md),
  including `timeout`, `memory`, `cadquery_exception`, `recorder`,
  `non_solid_result`, `missing_state`, and `fingerprint_collision`;
- `message`, `source_line`, and `source_span` when known;
- environment record;
- `cache_key`.

A failed result is never passed to graph assembly as a measurable state.

## Caching

The cache key includes the normalized program hash, `ast_extraction_result_sha256`,
extractor and canonicalization versions, CadQuery and OCP versions, the execution
environment, timeout, and memory limit. A failure tombstone is reusable for the
same key. A change to the CadQuery program AST extraction result or canonicalization is a cache miss.

The cache location, lookup, and resume rule are in
[`../run-contract.md`](../run-contract.md#8-cache). The run directory stores
one runtime result per program; a committed result, including a failure
tombstone, is not recomputed unless it is forced.

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
  [`extraction/cadquery/algorithm/runtime.md`](extraction/cadquery/algorithm/runtime.md).
