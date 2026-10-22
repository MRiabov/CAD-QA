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

Types are Parquet/Arrow types, not a SQL dialect. `UUID` is
`FIXED_LEN_BYTE_ARRAY(16)` with the UUID logical type. `STRING` is UTF-8. `LIST<T>`
and `STRUCT<...>` are the standard three-level list and nested group encodings.

Parquet has no `LowCardinality` type. The equivalent is dictionary encoding
(`RLE_DICTIONARY`), which is an encoding rather than a logical type. Parquet's
`ENUM` logical annotation is still a string and carries neither the value set nor
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
| `state_id` | `STRING` | nullable | Containing or selected solid state, when the type requires one. |
| `operation_id` | `STRING` | nullable | Creating or evaluated operation, when the type requires one. |
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
| `measurement_type` | `STRING` enum from `graph-content.md` | not null | Measurement category. |
| `value` | `MeasurementValue` | not null | Typed measurement payload; see the pending types below. |
| `unit` | `STRING` | nullable | Unit or stated frame; null means unitless. |
| `evidence_kind` | `STRING` enum `derived`, `measured` | not null | How the value was obtained. |
| `evidence_rule` | `STRING` | not null | Exact rule or kernel operation used. |
| `evidence_refs` | `LIST<EvidenceRef>` | not null | References that reproduce the measurement. |
| `tolerance` | `Tolerance` | nullable | Null means exact; otherwise the comparison tolerance. |

### Pending measurement types

These three types are named in the table but are not closed yet. They belong to
the measurement payload contract, tracked as MC-36 in
[`../missing-contracts.md`](../missing-contracts.md).

| Type | What must be defined |
|---|---|
| `MeasurementValue` | Union of scalar, point, vector, and bounding-box payloads with their units and canonical encoding. |
| `Tolerance` | Exact or numeric tolerance, including absolute versus relative mode and unit. |
| `EvidenceRef` | Typed reference to a graph node, measurement, operation, source line, or execution artifact. |

### Encoding requirements

| Columns | Encoding | Reason |
|---|---|---|
| `node_type`, `relation_type`, `measurement_type`, `evidence_kind` | dictionary (`RLE_DICTIONARY`) required | Closed low-cardinality enums. |
| `graph_schema_version`, `unit` | dictionary required | Repeated low-cardinality values. |
| `program_id`, `state_id`, `operation_id` | dictionary recommended | Repeated within a program's row groups. |
| `node_id`, `relation_id`, `measurement_id`, `from_node_id`, `to_node_id`, `subject_node_id`, `object_node_id` | none; fixed-width UUID | High-cardinality join keys; dictionaries add no value. |
| `label`, `selector_expression`, `evidence_rule` | plain | High-cardinality text. |

ClickHouse may expose a closed string enum as `LowCardinality(String)`.
`Enum8` or `Enum16` is optional; it is a ClickHouse storage choice, not part of
the Parquet contract.

## Table scope

- `nodes.parquet` is the only table that stores graph entities. `node_type` is
  the closed discriminator; an unknown value rejects the graph.
- `relations.parquet` stores relations. It stores no graph entity payload.
- `measurements.parquet` stores measurements. A measurement is a graph element,
  not a graph entity: it has a `measurement_id` and never a `node_id`.
- A graph entity never appears as a measurement row, and a measurement never
  appears as a node row. `graph-content.md` lists Measurement as an entity
  category; in storage it is a `measurements.parquet` row, not a graph node.
- `state_id` and `operation_id` are scope columns, not attributes. Their
  nullability is defined per node type below.
- `attributes` is one Parquet struct with one nullable group per node type.
  Exactly one group is non-null, and its field name equals `node_type`. A row
  with zero or several non-null groups rejects the graph.
- `label` is a non-empty display string. It is stable but not unique, and it is
  never used for identity, binding, or prompt text.

## ID types and derivation

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

| ID | Type | Canonical components |
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
plus the measurement name. The value, unit, tolerance, and evidence do not
participate in `measurement_id`.

`node_id` is not parsed. `node_type` and `local_id` are separate columns, so the
readable identity components remain available for debugging and filtering.

Go carries graph-local IDs as a 16-byte UUID value, such as `uuid.UUID` from
`github.com/google/uuid`, not as a `string`. The Parquet boundary must read and
write the UUID logical type directly. Do not convert an ID to text for storage,
map keys, comparisons, or joins. Convert to canonical lowercase hyphenated text
only when forming a UUIDv5 name component or writing inspection output.
`program_id` and the `02a`/`02b` IDs remain strings.

## Node types and local identity

`local_id` is defined as follows. `node_id` is derived from it, `program_id`, and
`node_type` as specified in [ID types and derivation](#id-types-and-derivation).
`ordinal` is a zero-based position in the static-model list for the creating
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

## Node attributes

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
| `OperationKind` | `workplane`, `sketch`, `solid`, `cadquery_selector`, `boolean`, `modifier`, `transform` |
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
- `is_final` is true for exactly one `solid_state` node when the graph has at
  least one solid state.
- `is_closed` is the closed flag reported by the source entity. `02c` does not
  recompute it from geometry.
- `result_var` is internal provenance. It is never rendered into a prompt.
- A null optional field means the value is absent. Empty strings and sentinel
  values such as `-1` are invalid.

### Validation invariants

- `node_type` matches the one non-null `attributes` group, and `node_id` uses the
  `local_id` from the table above.
- `state_id` and `operation_id` follow the table above exactly.
- `sequence_index` is unique and strictly increases with operation order.
- Every relation endpoint is an existing `node_id`; every measurement subject and
  every non-null object is an existing `node_id`; a missing reference rejects the
  graph.
- Every P0 node category has a row when the source model or execution result has
  an instance. P1 categories may be absent in a P0 graph.
- A change to a node type, attribute field, or enum value is a
  `graph_schema_version` change. Readers reject an unknown version.

## Relation identity

- `relation_id` is the UUIDv5 of
  `(program_id, relation_type, from_node_id, to_node_id)` as defined in
  [ID types and derivation](#id-types-and-derivation).

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
- Attach evidence at the same time as each measurement: derived or measured,
  the rule, and references.
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
  execution, including selector membership. Evidence records whether a
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

- **Typed graph attributes and table scope.** *Resolved 2026-10-22.* Option A.
  Keep the three-table layout. Store all graph entities in `nodes.parquet`, with a
  closed `node_type` discriminator and a tagged `NodeAttributes` union whose one
  non-null group matches the discriminator. Define `local_id`, scope columns, and
  one typed attribute struct for every entity category in `graph-content.md`.
  Attributes carry identity, classification, and scope; geometry values remain in
  `measurements.parquet` with evidence. This makes the schema typed, keeps one
  entity identity per row, and prevents an untyped property bag.
