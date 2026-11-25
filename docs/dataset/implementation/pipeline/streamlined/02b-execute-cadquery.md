# 02b execute CadQuery — runtime captures or tombstone

> Authoritative: `../02b-execute-cadquery.md`
> Models: `models/02-execute-cadquery-and-build-graph.md`

READ:

- `NormalizedProgram` → `program_id, program_sha256, canonical_text`
- `CadQueryAstExtractionResult` → `ast_extraction_result_sha256`, operations
- cache → committed result for the computed cache key, when present; the cache
  location and resume rule are in
  [`../../run-contract.md`](../../run-contract.md#8-cache)

## 1 — Execute and capture

TRANSFORM:

- cache key = `program_sha256 + ast_extraction_result_sha256 + extractor version + canonicalization version + CadQuery version + OCP version + execution environment + timeout + memory limit`; a hit returns the stored result
- run each program in a child Python process; 30 seconds wall clock and 2 GiB address space; a changed limit is a new execution environment and a new cache key
- kill on timeout → `timeout`; memory-limit failure → `memory`
- pin and record the CadQuery and OCP versions
- execute top-level statements in program order; only the accepted `02a` subset
- capture one `ShapeSnapshot` per solid-producing assignment: `state_id, operation_id, shape_hash, solid, valid, volume, bbox_min, bbox_max, centroid, face_count, edge_count, vertex_count, entity_table_ref`
- build the entity table with one row per face, edge, and vertex; `entity_id = hash(state_id, category, canonical geometric fingerprint)`
- fingerprint: vertex = point; edge = endpoints and length; face = centroid, area, normal, and bounding box
- two entities in one state with the same fingerprint → `fingerprint_collision`; reject the program
- capture one `CadQuerySelectorResult` per evaluated selector: `selector_result_id, selector_id, state_id, selected_entity_ids, count`; zero matches is success; a CadQuery selector exception rejects the program
- capture one `CadFeatureSolidStateEffectDelta` per operation: `operation_id, before_state_id, after_state_id, volume change, bounding-box change, topology counts`
- capture one or two `PointProbe` per solid state: `point_probe_id, state_id, point, location (inside | outside), distance_to_face_surface, classifier, margin`; the centroid probe plus a seeded point next to the state surface on either side, with the first and second probes carrying opposite labels when both survive; do not emit a probe within the clear-case margin; never confine a probe to the bounding box
- set `final_state_id`
- never persist raw kernel handles or BRep

WRITE:

- `CadQueryRuntimeExtractionSuccess` `(cache_key)` → `program_id, program_sha256, ast_extraction_result_sha256, environment record, operation_recordings, shape_snapshots, workplane_frames, selector_results, effect_deltas, point_probes, final_state_id, runtime_extraction_result_sha256`
- `runtime_*` Parquet tables
- one runtime result per program in `parts/<program_sha256>/`; a committed
  result, including a tombstone, is not recomputed unless forced

## 2 — Failure tombstone

TRANSFORM:

- on failure emit `FailureTombstone`: `program_id, program_sha256, operation_id when known, error_kind, message, source_line when known, source_span when known, environment record, cache_key`
- `error_kind` is one of `timeout, memory, cadquery_exception, recorder, result_kind, non_solid_result, missing_state, missing_shape, unmapped_entity, fingerprint_collision, no_state, geometry_capture, internal`
- a failed result is never passed to graph assembly as a measurable state
- a tombstone is reusable for the same cache key

WRITE:

- `CadQueryRuntimeExtractionResult` `(cache_key)` → `CadQueryRuntimeExtractionSuccess` captures or `FailureTombstone`
- `runtime_*` Parquet tables; no raw kernel handles and no BRep
- failure partition `02b_execute_cadquery`
