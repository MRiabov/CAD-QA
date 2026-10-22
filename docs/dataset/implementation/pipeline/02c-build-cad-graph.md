# 02c — Build CAD graph

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** combine the static CadQuery model and execution result into the CAD
graph.

## Input / output

- Input: `StaticCadQueryModel` plus `ExecutionResult`.
- Output: `CadGraph`.

## Graph tables

`CadGraph` is three logical Parquet tables: `nodes.parquet`,
`relations.parquet`, and `measurements.parquet`. The graph for one program is
the subset of rows whose `program_id` matches; the tables are not duplicated per
program. Every row carries `program_id` and `graph_schema_version`.
`graph_schema_version` is constant across the artifact. Physical partitioning and
file paths are artifact concerns in [`../artifacts.md`](../artifacts.md).

Parquet and Arrow types are used, not a SQL dialect. `UUID` is
`FIXED_LEN_BYTE_ARRAY(16)` with the UUID logical type. `STRING` is UTF-8. `LIST<T>`
and `STRUCT<...>` are the standard three-level list and nested group encodings.

Parquet has no `LowCardinality` logical type. The equivalent is dictionary encoding
(`RLE_DICTIONARY`), which is an encoding rather than a logical type. Parquet's
`ENUM` logical annotation is still a string and carries neither the enum value set nor
a compact code. Closed enum columns here are `STRING` with a closed value set and
must use dictionary encoding. This maps to `LowCardinality(String)` in ClickHouse.
Join keys are UUID, never enum strings.

### `nodes.parquet`

| Column | Parquet type | Null | Meaning |
|---|---|---|---|
| `program_id` | `STRING` | not null | `cadqaprog:<program_sha256>`. |
| `graph_schema_version` | `STRING` | not null | Constant across the artifact. |
| `node_id` | `UUID` | not null | Deterministic UUIDv5 of `(program_id, node_type, local_id)`. |
| `node_type` | `STRING` enum `GraphNodeType` | not null | Graph entity category. |
| `local_id` | `STRING` | not null | Stable ID within the program and node type. |
| `state_id` | `STRING` | nullable | Containing or selected solid state, when the graph node type requires one. |
| `operation_id` | `STRING` | nullable | Creating or evaluated operation, when the graph node type requires one. |
| `label` | `STRING` | not null | Display string; not used for identity or binding. |
| `attributes` | `STRUCT` tagged union | not null | Exactly one group is non-null and matches `node_type`. |

### `relations.parquet`

| Column | Parquet type | Null | Meaning |
|---|---|---|---|
| `program_id` | `STRING` | not null | `cadqaprog:<program_sha256>`. |
| `graph_schema_version` | `STRING` | not null | Constant across the artifact. |
| `relation_id` | `UUID` | not null | Deterministic UUIDv5 of the relation identity. |
| `relation_type` | `STRING` enum from `graph-content.md` | not null | Relation category. |
| `from_node_id` | `UUID` | not null | Existing `nodes.parquet.node_id`. |
| `to_node_id` | `UUID` | not null | Existing `nodes.parquet.node_id`. |

### `measurements.parquet`

| Column | Parquet type | Null | Meaning |
|---|---|---|---|
| `program_id` | `STRING` | not null | `cadqaprog:<program_sha256>`. |
| `graph_schema_version` | `STRING` | not null | Constant across the artifact. |
| `measurement_id` | `UUID` | not null | Deterministic UUIDv5 of `(program_id, subject_node_id, object_node_id or "", measurement_type)`. |
| `subject_node_id` | `UUID` | not null | Existing `nodes.parquet.node_id`. |
| `object_node_id` | `UUID` | nullable | Existing `nodes.parquet.node_id`; null for a one-entity measurement. |
| `measurement_type` | `STRING` enum `MeasurementType` | not null | Measurement category. |
| `value` | `MeasurementValue` | not null | Typed measurement payload. |
| `unit` | `STRING` enum `MeasurementUnit` | not null | Unit or stated frame; use `unitless` when there is no unit. |
| `evidence_kind` | `STRING` enum `derived`, `measured` | not null | How the measurement was obtained. |
| `evidence_rule` | `STRING` | not null | Exact rule or kernel operation used. |
| `evidence_refs` | `LIST<EvidenceRef>` | not null | References that reproduce the measurement. |
| `tolerance` | `Tolerance` | nullable | Null means inherit the run tolerance policy; otherwise an override. |

### Measurement payload types

These are closed tagged unions. A row with zero or several non-null groups
rejects the graph.

| Payload type | Fields |
|---|---|
| `Point3D` | `x: double`, `y: double`, `z: double` |
| `Vector3D` | `x: double`, `y: double`, `z: double` |
| `BoundingBox` | `min: Point3D`, `max: Point3D` |
| `BoundingBoxChange` | `before: BoundingBox`, `after: BoundingBox` |
| `TopologyDelta` | `face_delta: int64`, `edge_delta: int64`, `vertex_delta: int64` |
| `WorkplaneFrame` | `origin: Point3D`, `x_direction: Vector3D`, `normal: Vector3D` |
| `MeasurementValue` | `kind: MeasurementValueKind`; exactly one non-null group: `scalar: double`, `integer: int64`, `boolean: bool`, `point: Point3D`, `bounding_box: BoundingBox`, `bounding_box_change: BoundingBoxChange`, `topology_delta: TopologyDelta`, `workplane_frame: WorkplaneFrame` |

`MeasurementValueKind`: `scalar`, `integer`, `boolean`, `point`,
`bounding_box`, `bounding_box_change`, `topology_delta`, `workplane_frame`.

`MeasurementUnit`: `millimetre`, `square_millimetre`, `cubic_millimetre`,
`degree`, `radian`, `unitless`.

#### Measurement type catalog

| `measurement_type` | Value kind | Unit | Subject | Object |
|---|---|---|---|---|
| `volume` | `scalar` | `cubic_millimetre` | `solid_state`, `region` | null |
| `area` | `scalar` | `square_millimetre` | `face`, `cadquery_profile`, `region` | null |
| `length` | `scalar` | `millimetre` | `edge`, `cadquery_path_segment` | null |
| `distance` | `scalar` | `millimetre` | graph entity | graph entity |
| `angle` | `scalar` | `degree` or `radian` | `face`, `edge`, `cadquery_path_segment` | same category, or null for a path tangent |
| `bounding_box` | `bounding_box` | `millimetre` | `solid_state`, `face`, `edge`, `vertex`, `region` | null |
| `centroid` | `point` | `millimetre` | `solid_state`, `face`, `edge`, `vertex`, `region` | null |
| `face_count` | `integer` | `unitless` | `solid_state` | null |
| `edge_count` | `integer` | `unitless` | `solid_state`, `face` | null |
| `vertex_count` | `integer` | `unitless` | `solid_state`, `face` | null |
| `selected_count` | `integer` | `unitless` | `cadquery_selector_result` | null |
| `validity` | `boolean` | `unitless` | `solid_state` | null |
| `volume_change` | `scalar` | `cubic_millimetre` | `operation` | null |
| `bounding_box_change` | `bounding_box_change` | `millimetre` | `operation` | null |
| `topology_change` | `topology_delta` | `unitless` | `operation` | null |
| `workplane_frame` | `workplane_frame` | `millimetre` | `cadquery_workplane` | null |

For `workplane_frame`, `unit` describes the origin; the direction components are
unitless.

#### Tolerance

| Tolerance type | Fields |
|---|---|
| `Tolerance` | `kind: ToleranceKind`, `value: double \| null`, `unit: MeasurementUnit \| null` |
| `TolerancePolicy` | `millimetre: Tolerance`, `square_millimetre: Tolerance`, `cubic_millimetre: Tolerance`, `degree: Tolerance`, `radian: Tolerance`, `unitless: Tolerance` |

`ToleranceKind`: `exact`, `absolute`, `relative`.

- `exact`: `value` and `unit` are null.
- `absolute`: `value` is non-negative and `unit` is required and is not
  `unitless`.
- `relative`: `value` is a non-negative fraction and `unit` is null.

`TolerancePolicy` is resolved once per run, not per measurement and not per
program. It is stored once in the run manifest with `tolerance_policy_version`
and `tolerance_policy_sha256`; every graph artifact in the run reads the same
policy. A measurement `tolerance` of null inherits the policy entry for its
`unit`; a non-null value overrides it. Counts and validity are exact by default
through the `unitless` policy. A literal length may carry an `exact` override.

Answer-scoring tolerance is not this tolerance type. It belongs to the task definition and
the release `tolerance_json` field.

#### CAD graph evidence references

| Evidence reference type | Fields |
|---|---|
| `EvidenceRef` | `kind: EvidenceRefKind`; exactly one non-null group: `node: NodeEvidenceRef`, `measurement: MeasurementEvidenceRef`, `operation: OperationEvidenceRef`, `source_line: SourceLineEvidenceRef`, `execution_artifact: ExecutionArtifactEvidenceRef` |
| `NodeEvidenceRef` | `node_id: UUID` |
| `MeasurementEvidenceRef` | `measurement_id: UUID` |
| `OperationEvidenceRef` | `operation_id: STRING` |
| `SourceLineEvidenceRef` | `source_line: int64` |
| `ExecutionArtifactEvidenceRef` | `artifact_uri: STRING`, `artifact_field: STRING \| null` |

`EvidenceRefKind`: `node`, `measurement`, `operation`, `source_line`,
`execution_artifact`.

### Parquet struct declarations

The schema tables above are the field lists. The nested Parquet groups are written
out here so the physical schema is unambiguous. `TolerancePolicy` is not a
Parquet column; it is a run-manifest model listed with the tolerance types.

```text
NodeAttributes = STRUCT<
  cadquery_program: CadQueryProgramAttributes | NULL,
  operation: OperationAttributes | NULL,
  feature: FeatureAttributes | NULL,
  solid_state: SolidStateAttributes | NULL,
  face: FaceAttributes | NULL,
  edge: EdgeAttributes | NULL,
  vertex: VertexAttributes | NULL,
  edge_endpoint: EdgeEndpointAttributes | NULL,
  cadquery_profile: CadQueryProfileAttributes | NULL,
  cadquery_workplane: CadQueryWorkplaneAttributes | NULL,
  cadquery_path: CadQueryPathAttributes | NULL,
  cadquery_path_point: CadQueryPathPointAttributes | NULL,
  cadquery_path_segment: CadQueryPathSegmentAttributes | NULL,
  region: RegionAttributes | NULL,
  cadquery_selector_result: CadQuerySelectorResultAttributes | NULL
>

Point3D = STRUCT<x: DOUBLE, y: DOUBLE, z: DOUBLE>
Vector3D = STRUCT<x: DOUBLE, y: DOUBLE, z: DOUBLE>
BoundingBox = STRUCT<min: Point3D, max: Point3D>
BoundingBoxChange = STRUCT<before: BoundingBox, after: BoundingBox>
TopologyDelta = STRUCT<face_delta: INT64, edge_delta: INT64, vertex_delta: INT64>
WorkplaneFrame = STRUCT<origin: Point3D, x_direction: Vector3D, normal: Vector3D>

MeasurementValue = STRUCT<
  kind: STRING,
  scalar: DOUBLE | NULL,
  integer: INT64 | NULL,
  boolean: BOOLEAN | NULL,
  point: Point3D | NULL,
  bounding_box: BoundingBox | NULL,
  bounding_box_change: BoundingBoxChange | NULL,
  topology_delta: TopologyDelta | NULL,
  workplane_frame: WorkplaneFrame | NULL
>

Tolerance = STRUCT<
  kind: STRING,
  value: DOUBLE | NULL,
  unit: STRING | NULL
>

NodeEvidenceRef = STRUCT<node_id: UUID>
MeasurementEvidenceRef = STRUCT<measurement_id: UUID>
OperationEvidenceRef = STRUCT<operation_id: STRING>
SourceLineEvidenceRef = STRUCT<source_line: INT64>
ExecutionArtifactEvidenceRef = STRUCT<artifact_uri: STRING, artifact_field: STRING | NULL>

EvidenceRef = STRUCT<
  kind: STRING,
  node: NodeEvidenceRef | NULL,
  measurement: MeasurementEvidenceRef | NULL,
  operation: OperationEvidenceRef | NULL,
  source_line: SourceLineEvidenceRef | NULL,
  execution_artifact: ExecutionArtifactEvidenceRef | NULL
>
```

### Encoding requirements

| Columns | Encoding | Reason |
|---|---|---|
| `node_type`, `relation_type`, `measurement_type`, `evidence_kind`, `unit`, `MeasurementValue.kind`, `Tolerance.kind`, `EvidenceRef.kind` | dictionary (`RLE_DICTIONARY`) required | Closed low-cardinality enums. |
| `graph_schema_version` | dictionary required | Repeated low-cardinality value. |
| `program_id`, `state_id`, `operation_id` | dictionary recommended | Repeated within a program's row groups. |
| `node_id`, `relation_id`, `measurement_id`, `from_node_id`, `to_node_id`, `subject_node_id`, `object_node_id` | none; fixed-width UUID | High-cardinality join keys; dictionaries add no value. |
| `label`, `selector_expression`, `evidence_rule` | plain | High-cardinality text. |

ClickHouse may expose a closed string enum as `LowCardinality(String)`.
`Enum8` or `Enum16` is optional; it is a ClickHouse storage choice, not part of
the Parquet contract.

## Run-level tolerance policy

`TolerancePolicy` is resolved once per run. It is not derived per program and is
not stored on each measurement. The run manifest carries the policy,
`tolerance_policy_version`, and `tolerance_policy_sha256`; every graph artifact in
the run references the same policy.

The policy is part of the graph artifact identity. A change to any tolerance is a
new policy version and a new graph artifact; it never edits an existing graph.
Measurement `tolerance` null inherits the policy; a non-null value overrides it.

This policy covers measurement precision only. Relation comparison tolerances
remain MC-35, and answer-scoring tolerance remains the task definition's
`Tolerance` and the release `tolerance_json` field.

## Table scope

- `nodes.parquet` is the only table that stores graph entities. `node_type` is
  the closed discriminator; an unknown value rejects the graph.
- `relations.parquet` stores relations. It stores no graph entity payload.
- `measurements.parquet` stores measurements. A measurement is a graph element,
  not a graph entity: it has a `measurement_id` and never a `node_id`.
- A graph entity never appears as a measurement row, and a measurement never
  appears as a graph node row. `graph-content.md` lists Measurement as an entity
  category; in storage it is a `measurements.parquet` row, not a graph node.
- `state_id` and `operation_id` are scope columns, not attributes. Their
  nullability is defined per node type below.
- `attributes` is one Parquet struct with one nullable group per node type.
  Exactly one group is non-null, and its field name equals `node_type`. A row
  with zero or several non-null groups rejects the graph.
- `label` is a non-empty display string. It is stable but not unique, and it is
  never used for identity, binding, or prompt text.

## Graph ID derivation

`program_id` remains a string of the form `cadqaprog:<program_sha256>`. It is a
domain key used by the release contract, not a graph-local UUID.

Every graph-local ID is a native 16-byte UUID stored in Parquet as the `UUID`
logical type, which is physically `FIXED_LEN_BYTE_ARRAY(16)`. The IDs are
deterministic UUIDv5 values, not random UUIDv4 or time-ordered UUIDv7 values.
The namespace is:

```text
CADQA_GRAPH_ID_NAMESPACE =
  UUIDv5(NAMESPACE_DNS, "cad-qa.graph")
  = 09097f5d-9da1-540a-8bf7-20aed4f8a370
```

The UUIDv5 name is the UTF-8 encoding of the canonical components joined by one
NUL byte (`0x00`), with no trailing NUL. No component may contain a NUL byte. A
null optional component is encoded as the empty component.

| ID | ID type | Canonical components |
|---|---|---|
| `node_id` | UUID | `program_id`, `node_type`, `local_id` |
| `relation_id` | UUID | `program_id`, `relation_type`, `from_node_id`, `to_node_id` |
| `measurement_id` | UUID | `program_id`, `subject_node_id`, `object_node_id or ""`, `measurement_type` |
| `program_id` | str | `cadqaprog:<program_sha256>` |
| `local_id` | str | Defined per node type below. |
| `state_id`, `operation_id`, `entity_id`, `selector_result_id` | str | Stable IDs from `02a` or `02b`. |

`from_node_id`, `to_node_id`, `subject_node_id`, and `object_node_id` are
canonical lowercase hyphenated UUID strings when they are used as UUIDv5 name
components. Measurement identity follows `graph-content.md`: the subject or pair
plus the measurement name. The measurement value, unit, tolerance, and CAD graph evidence do
not participate in `measurement_id`.

`node_id` is not parsed. `node_type` and `local_id` are separate columns, so the
readable identity components remain available for debugging and filtering.

Go carries graph-local IDs as a 16-byte UUID value, such as `uuid.UUID` from
`github.com/google/uuid`, not as a `string`. The Parquet boundary must read and
write the UUID logical type directly. Do not convert an ID to text for storage,
map keys, comparisons, or joins. Convert to canonical lowercase hyphenated text
only when forming a UUIDv5 name component or writing inspection output.
`program_id` and the `02a`/`02b` IDs remain strings.

## Graph node types and local identity

`local_id` is defined as follows. `node_id` is derived from it, `program_id`, and
`node_type` as specified in [Graph ID derivation](#graph-id-derivation).
`ordinal` is a zero-based position in the static extraction list for the creating
operation. `index` and `sequence_index` are zero-based. `source_line` is one-based.

| `node_type` | `local_id` | `state_id` | `operation_id` |
|---|---|---|---|
| `cadquery_program` | `program` | null | null |
| `operation` | `operation_id` | null | the same `operation_id` |
| `feature` | `operation_id` | null | creating operation |
| `solid_state` | `state_id` | the same `state_id` | producing operation |
| `face` | `entity_id` from `02b` | containing solid state | producing operation of that state |
| `edge` | `entity_id` from `02b` | containing solid state | producing operation of that state |
| `vertex` | `entity_id` from `02b` | containing solid state | producing operation of that state |
| `edge_endpoint` | `{edge_local_id}:{start\|end}` | state of the edge | producing operation of that state |
| `cadquery_profile` | `{operation_id}:{ordinal}` | null | creating operation |
| `cadquery_workplane` | `{operation_id}:{ordinal}` | null | creating or using operation |
| `cadquery_path` | `{operation_id}:{ordinal}` | null | creating operation |
| `cadquery_path_point` | `{path_local_id}:{ordinal}` | null | creating operation of the path |
| `cadquery_path_segment` | `{path_local_id}:{ordinal}` | null | creating operation of the path |
| `region` | `{feature_local_id}:{added\|removed}` | state after the feature | creating operation of the feature |
| `cadquery_selector_result` | `selector_result_id` from `02b` | selected state | evaluated operation |

## Graph node attributes

`GraphNodeType` is the closed enum of the `node_type` values in the table above.
`NodeAttributes` is a tagged union with one group per `GraphNodeType` value. The
group named by `node_type` is the only non-null group. `Sha256` is 64 lowercase
hexadecimal characters; `str` is a non-empty UTF-8 string; an ordinal, index, or
count is a non-negative 64-bit integer.

| `node_type` | Attributes struct | Fields |
|---|---|---|
| `cadquery_program` | `CadQueryProgramAttributes` | `program_sha256: Sha256`, `normalization_version: str`, `extractor_version: str`, `execution_result_sha256: Sha256` |
| `operation` | `OperationAttributes` | `operation_kind: OperationKind`, `method: str`, `order: int`, `source_line: int`, `result_var: str \| None` |
| `feature` | `FeatureAttributes` | `feature_kind: FeatureKind` |
| `solid_state` | `SolidStateAttributes` | `sequence_index: int`, `is_final: bool`, `is_solid: bool`, `shape_hash: Sha256 \| None` |
| `face` | `FaceAttributes` | `fingerprint_sha256: Sha256`, `surface_kind: SurfaceKind` |
| `edge` | `EdgeAttributes` | `fingerprint_sha256: Sha256`, `curve_kind: CurveKind`, `is_closed: bool` |
| `vertex` | `VertexAttributes` | `fingerprint_sha256: Sha256` |
| `edge_endpoint` | `EdgeEndpointAttributes` | `end: EdgeEnd` |
| `cadquery_profile` | `CadQueryProfileAttributes` | `profile_kind: ProfileKind`, `is_closed: bool` |
| `cadquery_workplane` | `CadQueryWorkplaneAttributes` | `workplane_kind: WorkplaneKind`, `named_plane: NamedPlane \| None` |
| `cadquery_path` | `CadQueryPathAttributes` | `path_kind: PathKind`, `is_closed: bool` |
| `cadquery_path_point` | `CadQueryPathPointAttributes` | `index: int` |
| `cadquery_path_segment` | `CadQueryPathSegmentAttributes` | `index: int`, `segment_kind: PathSegmentKind` |
| `region` | `RegionAttributes` | `region_sign: RegionSign` |
| `cadquery_selector_result` | `CadQuerySelectorResultAttributes` | `selector_id: str`, `selector_expression: str`, `selector_kind: SelectorKind`, `source_line: int` |

### Attribute enums

| Enum | Values |
|---|---|
| `OperationKind` | `workplane`, `sketch`, `path`, `solid`, `cadquery_selector`, `boolean`, `assembly`, `modifier`, `transform`, `accessor` |
| `FeatureKind` | `add_material`, `remove_material`, `modify`, `construction` |
| `SurfaceKind` | `plane`, `cylinder`, `cone`, `sphere`, `torus`, `bspline`, `other` |
| `CurveKind` | `line`, `circle`, `ellipse`, `hyperbola`, `parabola`, `bspline`, `other` |
| `EdgeEnd` | `start`, `end` |
| `ProfileKind` | `rectangle`, `circle`, `ellipse`, `polygon`, `slot`, `other` |
| `WorkplaneKind` | `named`, `custom`, `face` |
| `NamedPlane` | `xy`, `yz`, `xz` |
| `PathKind` | `line`, `polyline`, `spline`, `arc`, `helix`, `other` |
| `PathSegmentKind` | `line`, `arc`, `spline`, `other` |
| `RegionSign` | `added`, `removed` |
| `SelectorKind` | `string`, `call` |

### Attribute rules

- The attribute groups are closed structs. An unknown field rejects the graph; it
  is not ignored.
- Attributes carry identity, classification, and scope only. Numeric geometry,
  counts, distances, angles, bounding boxes, validity, and volume changes are
  measurements, not attributes.
- `fingerprint_sha256` is the SHA-256 of the canonical geometric fingerprint that
  `02b` uses to derive `entity_id`. It is an audit value, not a measurement. When
  `02b` provides only `entity_id`, `02c` recomputes the hash from the canonical
  entity table. A mismatch between the attribute hash, the entity table, and
  `entity_id` rejects the graph.
- `execution_result_sha256` is computed by `02c` over the canonical execution
  result from `02b`.
- `shape_hash` is the shape identity hash from `02b`. It is not a measurement.
- `is_final` is true for exactly one solid-state graph node when the graph has at
  least one solid state.
- `is_closed` is the closed flag reported by the origin graph entity. `02c` does not
  recompute it from geometry.
- `result_var` is internal provenance. It is never rendered into a prompt.
- A null optional field means the measurement value is absent. Empty strings and sentinel
  values such as `-1` are invalid.

### Validation invariants

- `node_type` matches the one non-null `attributes` group, and `node_id` uses the
  `local_id` from the table above.
- `state_id` and `operation_id` follow the table above exactly.
- `sequence_index` is unique and strictly increases with operation order.
- Every relation endpoint is an existing `node_id`; every measurement subject and
  every non-null object is an existing `node_id`; a missing reference rejects the
  graph.
- Every P0 node category has a row when the static extraction result or execution result has
  an instance. P1 categories may be absent in a P0 graph.
- `MeasurementValue`, `Tolerance`, and `EvidenceRef` each have exactly one
  non-null group matching their `kind`.
- `measurement_type` determines the measurement value kind and `unit` through the catalog;
  a mismatch rejects the graph.
- `TolerancePolicy`, `tolerance_policy_version`, and `tolerance_policy_sha256` are present in the run manifest.
- `Tolerance` obeys its `exact`, `absolute`, and `relative` field rules.
- A change to a graph node type, attribute field, measurement type, enum value, or
  payload field is a `graph_schema_version` change. Readers reject an unknown
  version.

## Relation identity

- `relation_id` is the UUIDv5 of
  `(program_id, relation_type, from_node_id, to_node_id)` as defined in
  [Graph ID derivation](#graph-id-derivation).

The graph includes a `cadquery_selector_result` graph node for each
`SelectorResult`. `selected_by` relations link an entity graph node to its
CadQuery selector result; `selected_from` links the CadQuery selector result to
its state. The CadQuery selector result carries a count measurement equal to the
number of `selected_by` edges.

## Behavior

- Join operations to shape snapshots by `operation_id`.
- Create entity graph nodes for each shape snapshot and relation records for
  operation order, containment, adjacency, provenance, and measurements.
- Map `selected_entity_ids` to entity graph nodes in the same shape snapshot.
- Attach CAD graph evidence at the same time as each measurement: derived or
  measured, the rule, and references.
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
  execution, including selector membership. CAD graph evidence records whether a
  measurement was derived or measured, the exact rule, and the references.

- **Entity identity.** *Resolved 2026-10-21.* Entity graph nodes use the stable
  geometric `entity_id` from `02b`. Kernel handles are not persisted.

- **CadQuery selector mapping.** *Resolved 2026-10-21.* A selected entity ID that
  cannot be mapped to an entity graph node rejects the graph. The CadQuery selector
  count invariant must hold; do not drop a partial selector result.

- **Graph ID type.** *Resolved 2026-10-22.* Graph-local IDs use deterministic
  UUIDv5 stored as native Parquet UUID values. `node_id`, `relation_id`, and
  `measurement_id` are 16-byte fixed-width keys for joins; `program_id` and the
  `02a`/`02b` IDs stay strings. Random UUIDv4 is rejected because it would break
  deterministic reruns, cache hits, and duplicate detection.

- **Measurement payload and type catalog.** *Resolved 2026-10-22.* Measurement
  values are a tagged union of scalar, integer, boolean, point, bounding box,
  bounding-box change, topology delta, and workplane frame. Measurement types are
  the closed catalog above. Tolerances are a run-level `TolerancePolicy` stored
  once in the run manifest, with per-measurement overrides. CAD graph evidence
  references are a tagged union of graph node, measurement, operation, program line, and
  execution artifact. Answer-scoring tolerance remains separate.

- **Typed graph attributes and table scope.** *Resolved 2026-10-22.* Option A.
  Keep the three-table layout. Store all graph entities in `nodes.parquet`, with a
  closed `node_type` discriminator and a tagged `NodeAttributes` union whose one
  non-null group matches the discriminator. Define `local_id`, scope columns, and
  one typed attribute struct for every entity category in `graph-content.md`.
  Attributes carry identity, classification, and scope; geometry values remain in
  `measurements.parquet` with CAD graph evidence. This makes the schema typed,
  keeps one entity identity per row, and prevents an untyped property bag.
