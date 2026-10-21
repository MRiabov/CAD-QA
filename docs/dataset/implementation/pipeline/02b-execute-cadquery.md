# 02b — Execute CadQuery

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** run the normalized program and capture shape snapshots and selector
results, or a failure tombstone when execution fails.

## Input / output

- Input: normalized program text plus `StaticCadQueryModel`.
- Output: `ExecutionResult`, either success or a failure tombstone.

## Execution boundary

- Run in an isolated Python worker with no network access.
- Pin the CadQuery and OCP versions and record them in the result.
- Apply a wall-clock timeout and a memory limit.
- Execute only the accepted static subset from `02a`.
- Execute top-level statements in program order.

## Success result

`ExecutionSuccess` contains:

- `program_id`, `program_sha256`, and the environment record;
- `shape_snapshots`: one per solid-producing assignment;
- `selector_results`: one per evaluated CadQuery selector;
- `operation_effects`: before/after state pairs and measured deltas;
- `final_state_id`.

Each `ShapeSnapshot` contains:

- `state_id` and `operation_id`;
- `shape_hash`;
- `solid`, `valid`;
- `volume`, `bbox_min`, `bbox_max`, and `centroid`;
- `face_count`, `edge_count`, and `vertex_count`.

Each `SelectorResult` contains:

- `selector_result_id` and `selector_id`;
- `state_id`;
- `selected_entity_handles`, the kernel handles or stable in-state indices;
- `count`.

Each `OperationEffect` contains:

- `operation_id`;
- `before_state_id` and `after_state_id`;
- volume change, bounding-box change, and topology counts.

## Failure tombstone

`ExecutionFailure` contains:

- `program_id`, `operation_id`, and `error_kind`;
- `message` and `source_line`;
- environment record;
- `cache_key`.

A failed result is never passed to graph assembly as a measurable state.

## Caching

The cache key includes the normalized program hash, CadQuery and OCP versions,
the execution environment, and the timeout. A failure tombstone is reusable for
the same key.

## Open questions

- What are the timeout and memory limits for the first release?
- Are kernel entity handles stable enough inside one shape snapshot, or should
  graph assembly use geometric fingerprints?
- Should selector evaluation failures reject the whole program or only the
  affected selector result?
