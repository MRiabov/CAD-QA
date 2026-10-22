# Extraction artifacts

**Parent:** [`extraction/README.md`](README.md).

This document defines the logical tables emitted by `02a` and `02b`. Physical
paths and partitioning belong to [`../../artifacts.md`](../../artifacts.md);
field definitions remain in the linked field docs.

## Common columns

Every table carries:

- `program_id`: `cadqaprog:<program_sha256>`;
- `program_sha256`;
- `extractor_version`;
- `static_schema_version` or `runtime_schema_version`;
- `canonicalization_version`.

No table carries timestamps, hostnames, process IDs, or kernel handles.

## `02a` static tables

| Table | Key | Contents |
|---|---|---|
| `static_program` | `program_id` | Program identity, normalization version, import alias, static status, `static_model_sha256`. |
| `static_operations` | `(program_id, operation_id)` | Call operations, classification, receiver, expression trees, program span. |
| `static_aliases` | `(program_id, alias_id)` | Name and subscript aliases. |
| `static_workplanes` | `(program_id, workplane_id)` | Static CadQuery workplane kind, named plane, frame status, derivations, tags. |
| `static_profiles` | `(program_id, profile_id)` | CadQuery profile kind, dimensions, points, closed flag, CadQuery workplane reference. |
| `static_paths` | `(program_id, path_id)` | Path kind, points, segments, closed flag, CadQuery workplane reference. |
| `static_selectors` | `(program_id, selector_id)` | CadQuery selector kind, expression, category, filter predicate. |
| `static_failures` | `(program_id)` | Static rejection reason and location. |

Expression trees are nested Parquet structs on the owning operation, alias, or
CadQuery selector row. They are not JSON strings. Exact columns and nested models
are in [`static-schema.md`](static-schema.md).

A static failure writes only `static_program` and `static_failures`. It writes no
operation, alias, CadQuery workplane, CadQuery profile, path, or CadQuery selector rows.

## `02b` runtime tables

| Table | Key | Contents |
|---|---|---|
| `execution_program` | `program_id` | Environment, static model hash, execution status, `execution_result_sha256`. |
| `execution_recordings` | `(program_id, operation_id)` | One row per static operation: result kind, state, CadQuery selector result, program span. |
| `execution_states` | `(program_id, state_id)` | Shape snapshot: shape hash, validity, solid flag, volume, bbox, centroid, counts. |
| `execution_entities` | `(program_id, state_id, entity_id)` | Entity table: category, fingerprint, fingerprint hash, face surface and edge curve category. |
| `execution_topology` | `(program_id, topology_id)` | Face-edge, edge-vertex, face-face, and state incidence records. |
| `execution_workplanes` | `(program_id, workplane_id)` | Measured origin, x direction, normal, CadQuery workplane category, named plane. |
| `execution_selectors` | `(program_id, selector_result_id)` | Static CadQuery selector, state, selected entity IDs, count. |
| `execution_effects` | `(program_id, effect_id)` | Before/after states and measured deltas. |
| `execution_failures` | `(program_id)` | Runtime tombstone: error category, message, operation, program span, cache key. |

Exact runtime columns and nested models are in [`runtime-schema.md`](runtime-schema.md).

`execution_recordings` is the join table between static operations and runtime
capture. It is written even when a later operation fails; the failure record
marks the terminal operation. A failed execution still writes no state or
CadQuery selector row for the failed operation.

## Identity

- `static_model_sha256` is the canonical hash of the complete static model.
- `execution_result_sha256` is the canonical hash of the complete execution
  result, including sorted recordings, states, entities, topology, frames,
  selectors, effects, and final state.
- `cache_key` is defined in
  [`cadquery/runtime.md`](cadquery/runtime.md).
- `entity_table_ref` is `entity:<state_id>`. The `execution_entities` rows for
  that state are the table.

A reader must reject a missing table, mismatched hash, unknown schema version, or
row whose `program_id` does not match the artifact.

## Physical shape policy

- Static and runtime tables are Parquet.
- Large tables may be partitioned by `program_id`.
- One program's rows are merged by `program_id`; parallel writers never append to
  a shared file.
- Raw BRep geometry and kernel objects are not persisted.
- `execution_states` and `execution_entities` are sufficient for `02c` and for
  inspection. If a debugging export of a shape is needed, it is a separate,
  non-pipeline artifact.
- Failures are copied into the release-level `failures.parquet` by `05`; the
  extraction tables remain the authoritative record.

## Schema change rules

A change to a table name, key, column, nested field, enum value, fingerprint
field, hash input, or ordering rule changes the relevant schema version. Readers
reject an unknown version. A change to an existing table is never applied in
place.
