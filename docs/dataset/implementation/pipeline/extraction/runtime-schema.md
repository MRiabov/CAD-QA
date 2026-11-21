# Runtime model schema

**Parent:** [`README.md`](README.md).

This document fixes the runtime artifact schema produced by `02b`. Field
meanings are in the `cadquery/` documents; exact tables and nested models are
here.

`runtime_schema_version = "cadqa-runtime-v1"`.

## Common columns

Every runtime table carries:

- `program_id: STRING`;
- `program_sha256: STRING`;
- `normalization_version: STRING`;
- `extractor_version: STRING`;
- `runtime_schema_version: STRING`;
- `canonicalization_version: STRING`.

No runtime table carries timestamps, hostnames, process IDs, absolute paths, or
kernel handles.

## `runtime_program`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `ast_extraction_result_sha256` | `STRING` | not null | Input CadQuery program AST extraction result hash. |
| `runtime_status` | `STRING` enum `success`, `failure` | not null | Terminal result. |
| `runtime_extraction_result_sha256` | `STRING` | null | Canonical runtime hash. |
| `python_version` | `STRING` | not null | Pinned Python version. |
| `cadquery_version` | `STRING` | not null | Pinned CadQuery version. |
| `ocp_version` | `STRING` | not null | Pinned OCP version. |
| `timeout_seconds` | `INT64` | not null | Child wall-clock limit. |
| `memory_bytes` | `INT64` | not null | Child address-space limit. |
| `environment_id` | `STRING` | not null | Canonical environment identity. |
| `cache_key` | `STRING` | not null | Cache identity. |

Exactly one row exists per `program_id`.

## `runtime_recordings`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `operation_id` | `STRING` | not null | AST operation ID. |
| `result_var` | `STRING` | not null | Assigned variable. |
| `result_kind` | `STRING` enum `ResultKind` | not null | Runtime result category. |
| `state_id` | `STRING` | null | Produced state, when any. |
| `selector_result_id` | `STRING` | null | CadQuery selector result, when any. |
| `source_span` | `SourceSpan` | not null | Assignment span. |

Every AST call operation has exactly one row.

## `runtime_states`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `state_id` | `STRING` | not null | `state:<operation_id>`. |
| `operation_id` | `STRING` | not null | Producing operation. |
| `shape_hash` | `STRING` | not null | Canonical shape hash. |
| `is_solid` | `BOOLEAN` | not null | Contains at least one solid. |
| `is_valid` | `BOOLEAN` | not null | Kernel validity. |
| `volume` | `DOUBLE` | not null | Volume. |
| `bbox_min` | `Point3D` | not null | Minimum bounding-box corner. |
| `bbox_max` | `Point3D` | not null | Maximum bounding-box corner. |
| `centroid` | `Point3D` | not null | Centroid. |
| `face_count` | `INT64` | not null | Face count. |
| `edge_count` | `INT64` | not null | Edge count. |
| `vertex_count` | `INT64` | not null | Vertex count. |
| `entity_table_ref` | `STRING` | not null | `entity:<state_id>`. |
| `source_span` | `SourceSpan` | not null | Producing assignment span. |

## `runtime_entities`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `state_id` | `STRING` | not null | Containing state. |
| `entity_id` | `STRING` | not null | `ent:<sha256>`. |
| `entity_category` | `STRING` enum `face`, `edge`, `vertex` | not null | Entity category. |
| `fingerprint` | `EntityFingerprint` | not null | Canonical geometry. |
| `fingerprint_sha256` | `STRING` | not null | Fingerprint hash. |
| `face_surface_kind` | `STRING` | null | Face surface category. |
| `edge_curve_kind` | `STRING` | null | Edge curve category. |
| `is_closed` | `BOOLEAN` | null | Closed edge flag. |

## `runtime_topology`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `topology_id` | `STRING` | not null | `topo:<sha256>`. |
| `state_id` | `STRING` | not null | Containing state. |
| `relation_kind` | `STRING` enum `TopologyRelationKind` | not null | Relation category. |
| `from_entity_id` | `STRING` | not null | From entity. |
| `to_entity_id` | `STRING` | not null | Target entity. |
| `evidence` | `TopologyEvidence` | not null | Traversal evidence. |

## `runtime_workplanes`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `workplane_id` | `STRING` | not null | CadQuery workplane ID in the AST extraction result. |
| `operation_id` | `STRING` | not null | Creating operation. |
| `origin` | `Point3D` | not null | Measured origin. |
| `x_direction` | `Vector3D` | not null | Measured x direction. |
| `normal` | `Vector3D` | not null | Measured normal. |
| `workplane_kind` | `STRING` enum `named`, `custom`, `face` | not null | CadQuery workplane category. |
| `named_plane` | `STRING` enum `xy`, `yz`, `xz` | null | Named plane. |
| `source_span` | `SourceSpan` | not null | Creating call span. |

## `runtime_selectors`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `selector_result_id` | `STRING` | not null | `sres:<operation_id>:<ordinal>`. |
| `selector_id` | `STRING` | not null | CadQuery selector ID in the AST extraction result. |
| `selected_entity_category` | `STRING` enum `face`, `edge`, `vertex` | not null | Selected entity category. |
| `state_id` | `STRING` | not null | State it ran on. |
| `selected_entity_ids` | `LIST<STRING>` | not null | Stable entity IDs. |
| `count` | `INT64` | not null | Selected count. |
| `source_span` | `SourceSpan` | not null | Evaluating call span. |

## `runtime_point_probes`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `probe_id` | `STRING` | not null | `probe:<state_id>:<probe_index>`. |
| `state_id` | `STRING` | not null | State the probe classifies. |
| `probe_index` | `INT64` | not null | 0 for the centroid probe, 1 for the seeded probe. |
| `point` | `Point3D` | not null | Probe point. |
| `is_inside` | `BOOLEAN` | not null | `is_inside(state, point)` classification. |
| `distance_to_surface` | `DOUBLE` | not null | Distance to the nearest face surface. |
| `classifier` | `STRING` enum `is_inside` | not null | Classifier that produced the label. |
| `source_span` | `SourceSpan` | null | Producing assignment span, when known. |

A state has at most two rows. A state with no surviving row supports no
membership task; that is a deficit, not a missing row.

## `runtime_effects`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `effect_id` | `STRING` | not null | `effect:<operation_id>`. |
| `operation_id` | `STRING` | not null | Producing operation. |
| `before_state_id` | `STRING` | null | State before the operation. |
| `after_state_id` | `STRING` | not null | State after the operation. |
| `volume_change` | `DOUBLE` | null | Signed volume change. |
| `bbox_change` | `BoundingBoxChange` | null | Bounding-box change. |
| `topology_change` | `TopologyDelta` | null | Count changes. |
| `evidence` | `EffectEvidence` | not null | Effect evidence. |

## `runtime_failures`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `error_kind` | `STRING` enum `ErrorKind` | not null | Failure category. |
| `operation_id` | `STRING` | null | Terminal operation. |
| `message` | `STRING` | not null | Failure message. |
| `source_line` | `INT64` | null | One-based CadQuery program line. |
| `source_span` | `SourceSpan` | null | Program span. |
| `cache_key` | `STRING` | not null | Cache identity. |

A failure row contains no state, entity, topology, CadQuery workplane, CadQuery selector,
or effect rows for the failed operation.

## Nested models

```text
SourceSpan = STRUCT<
  start_line: INT64,
  start_column: INT64,
  end_line: INT64,
  end_column: INT64
>

Point3D = STRUCT<x: DOUBLE, y: DOUBLE, z: DOUBLE>
Vector3D = STRUCT<x: DOUBLE, y: DOUBLE, z: DOUBLE>
BoundingBox = STRUCT<min: Point3D, max: Point3D>
BoundingBoxChange = STRUCT<before: BoundingBox, after: BoundingBox>
TopologyDelta = STRUCT<
  face_delta: INT64,
  edge_delta: INT64,
  vertex_delta: INT64
>

EntityFingerprint = STRUCT<
  point: Point3D | NULL,
  start: Point3D | NULL,
  end: Point3D | NULL,
  length: DOUBLE | NULL,
  centroid: Point3D | NULL,
  area: DOUBLE | NULL,
  normal: Vector3D | NULL,
  bbox: BoundingBox | NULL
>

EvidenceRef = STRUCT<
  kind: STRING,
  state_id: STRING | NULL,
  entity_id: STRING | NULL,
  operation_id: STRING | NULL,
  span: SourceSpan | NULL,
  call: STRING | NULL,
  selector_result_id: STRING | NULL,
  artifact_uri: STRING | NULL,
  artifact_field: STRING | NULL
>

EffectEvidence = STRUCT<
  before_state_id: STRING | NULL,
  after_state_id: STRING,
  rule: STRING,
  refs: LIST<EvidenceRef>
>

TopologyEvidence = STRUCT<
  relation_kind: STRING,
  from_entity_id: STRING,
  to_entity_id: STRING,
  call: STRING,
  refs: LIST<EvidenceRef>
>
```

`entity_category` selects which `EntityFingerprint` groups are non-null:
vertex uses `point`; edge uses `start`, `end`, and `length`; face uses
`centroid`, `area`, `normal`, and `bbox`.

## Runtime model hash

`runtime_extraction_result_sha256` is the SHA-256 of the canonical JSON of all runtime
rows for one program, using [`canonicalization.md`](canonicalization.md). Rows
are sorted by their table key. A failure tombstone hashes only
`runtime_program` and `runtime_failures`.
