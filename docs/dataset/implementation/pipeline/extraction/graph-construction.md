# CAD graph construction

**Parent:** [`02c — Build CAD graph`](../02c-build-cad-graph.md).

**Purpose:** define the deterministic mapping from the extraction contract to
the CAD graph. Table schemas are in [`graph-persistence.md`](graph-persistence.md);
this document defines which rows and relations are created.

## Inputs

- `CadQueryAstExtractionResult` from
  [`README.md`](README.md);
- `CadQueryRuntimeExtractionResult` from `02b`;
- program metadata from `01d`.

Reject the pair if either hash or any required reference is missing.

## IDs

Extraction IDs are local identities. Graph IDs are UUIDv5 values derived by the
rules in [`graph-persistence.md`](graph-persistence.md).

| CAD graph entity category | `local_id` | From |
|---|---|---|
| `cadquery_program` | `program` | Program row. |
| `operation` | `operation_id` | Every call operation. |
| `feature` | `operation_id` | Every solid state producing operation. |
| `solid_state` | `state_id` | Every shape snapshot. |
| `face` | `entity_id` | Face entity row. |
| `edge` | `entity_id` | Edge entity row. |
| `vertex` | `entity_id` | Vertex entity row. |
| `edge_endpoint` | `<edge_local_id>:start` or `:end` | Edge endpoints. |
| `cadquery_profile` | `profile_id` | CadQuery profile in the AST extraction result. |
| `cadquery_workplane` | `workplane_id` | CadQuery workplane in the AST extraction result and measured. |
| `cadquery_path` | `path_id` | CadQuery path in the AST extraction result. |
| `cadquery_path_point` | `<path_local_id>:<ordinal>` | Path point in the AST extraction result. |
| `cadquery_path_segment` | `<path_local_id>:<ordinal>` | Path segment in the AST extraction result. |
| `region` | `<feature_local_id>:added` or `:removed` | Feature effect region. |
| `cadquery_selector_result` | `selector_result_id` | CadQuery selector result from the runtime extraction result. |

An alias has no CAD graph entity. It is consumed when resolving the target binding.

## CAD graph entity construction

1. Create one `cadquery_program` CAD graph entity with the program hashes, normalization
   version, extractor version, and CadQuery program runtime extraction result hash.
2. Create one `operation` CAD graph entity for every AST call operation. Use the AST extraction result's
   `operation_kind`, `method`, `order`, `source_line`, and `result_var`.
3. Create one `feature` CAD graph entity for every solid state producing operation. Use the
   `feature_kind` from the AST extraction result.
4. Create one `solid_state` CAD graph entity for every Shape snapshot. Set `is_final` on
   the last Shape snapshot in operation order.
5. Create face, edge, vertex, and edge-endpoint CAD graph entities from every state entity
   table.
6. Create CadQuery profile, CadQuery workplane, path, path-point, path-segment,
   and CadQuery selector-result CAD graph entities from the AST and runtime records.
7. Create `region` CAD graph entities for solid state producing operations that
   have a state:
   - `added` for an operation whose `feature_kind` is `add_material` or
     `construction`;
   - `removed` for an operation whose `feature_kind` is `remove_material`;
   - `modify` operations create no region.
   A first state with no before state creates only the region implied by its
   AST feature kind.

## Relation construction

Create relations in this order; all endpoints must exist.

### Program and provenance

- `before` and `after` for consecutive operations in `order`.
- `creates` from an operation to its feature.
- `creates` from an operation to its solid state.
- `uses` from a feature to every CadQuery profile and CadQuery workplane used by
  its operation.
- `derived_from` from a CadQuery profile to its CadQuery workplane.
- `derived_from` from every path point and path segment to its path.
- `derived_from` from a path to its CadQuery workplane, when present.

### Topology

- `has_face` from a solid state to every face in its entity table.
- `has_edge` from a face to every edge returned by the topology `face_has_edge`
  record.
- `has_vertex` from an edge to every vertex returned by the topology
  `edge_has_vertex` record.
- `adjacent_to` for every topology `face_adjacent_to_face` record.
- `endpoint_of` from each edge endpoint to its edge.

### Selection

- `selected_from` from a CadQuery selector result to its state.
- `selected_by` from every selected face, edge, or vertex to its CadQuery
  CadQuery selector result.

### Material change

- `adds_material` from a feature to its `added` region.
- `removes_material` from a feature to its `removed` region.
- `part_of` from each region to its feature.

Do not create a relation whose endpoint is missing. A missing endpoint rejects
the graph; it is not dropped.

## Emission rules

Per-entity measurements are emitted for every entity in their scope. A missing
row rejects the graph.

Pair relations and pair measurements are emitted only when the pair matches the
pair emission rule in [`graph-content.md` §4.1](../../../requirements/graph-content.md#41-emission-rules).
A pair that is not emitted produces no row. It is not recorded as missing, and it
must not be guessed.

### Named endpoints

A named endpoint is derived per solid state from the extraction records. A name
exists only when it resolves to exactly one entity in the state. Zero matches or
several matches means the name does not exist, and a pair that needs it is not
emitted.

| Mechanism | Derivation | Stored name |
|---|---|---|
| Face surface kind | The `face_surface_kind` of the face. | The `FaceSurfaceKind` value, for example `cylinder`. |
| Position | The face whose bounding box touches an extreme of the state bounding box on one program axis. | `min_x`, `max_x`, `min_y`, `max_y`, `min_z`, `max_z`. |
| Provenance | The face first appears in the state of one operation: its `fingerprint_sha256` is absent from the previous state's entity table. | The operation id. |

The first state has no previous state, so every face in it counts as new. The
stored name is the graph value. `04` renders prompt wording from it; the graph
stores no English.

A face can carry several names, and a name can resolve to no face. A name is not
a relation and creates no row. It is a lookup used by pair emission.

### Pair rows

For each pair relation or pair measurement, take the named endpoints of the state
and the candidate endpoints of the declared endpoint entity kind in the same
state, then:

1. drop a pair whose two endpoints are the same entity;
2. reduce to unordered pairs, so a pair of two named entities appears once;
3. emit one row per remaining pair, with the endpoints in canonical id order.

The row uses the relation or measurement id from
[`graph-persistence.md`](graph-persistence.md), which already includes the
program, the element name, and both endpoints. A measurement row carries the
value, unit, and tolerance; a relation row carries its evidence.

An empty candidate set emits no rows. It is not an error and not a gap.

### State size

The entity count of a solid state is its faces plus edges plus vertices. Regions
belong to features, not to the state, and are not counted.

When the count exceeds `max_state_entities`, reject the program: no graph is
emitted for it, and the failure records the state, the count, and the limit. Do
not truncate the state and do not emit a partial graph, because a task that
references the dropped entities would look unanswerable rather than invalid.

## Measurement construction

Use the measurement catalog in [`graph-persistence.md`](graph-persistence.md).
Every measurement carries `evidence_kind`, `evidence_rule`, and `evidence_refs`
from [`cadquery/features/evidence.md`](cadquery/features/evidence.md).

From the CadQuery program runtime extraction result:

- solid state: `volume`, `bounding_box`, `centroid`, `face_count`,
  `edge_count`, `vertex_count`, `validity`;
- face: `area`, `bounding_box`, `centroid`;
- edge: `length`, `bounding_box`, `centroid`;
- vertex: `centroid`;
- CadQuery selector result: `selected_count`;
- CadQuery workplane: `workplane_frame`;
- CAD feature solid state effect delta: `volume_change`, `bounding_box_change`, `topology_change`.

From the CadQuery program AST extraction result, create only exact derived measurements for operation
counts or literal facts that the catalog allows. Do not derive geometry from
method names.

A measurement `tolerance` is null unless the run policy or the record supplies
an override. Do not write a per-program tolerance policy.

## CadQuery selector mapping

- Copy `selector_id`, `selected_entity_category`, `state_id`, and
  `selected_entity_ids` from the runtime result.
- Create `selected_by` relations only for face, edge, and vertex entities.
- The `selected_count` measurement equals the number of membership edges.
- A selected entity ID that cannot be resolved in the state entity table rejects
  the graph.

## CadQuery workplane mapping

- Create one `cadquery_workplane` CAD graph entity for every CadQuery workplane in the AST extraction result.
- Attach the measured `workplane_frame` when the runtime result provides it.
- An AST frame that is `unknown` is not a measurement; do not invent one.
- A runtime frame without a CadQuery workplane in the AST extraction result rejects the graph.

## CAD feature solid state effect deltas

- Create one effect measurement set for every solid state producing operation with a
  captured effect.
- A solid state producing operation without an effect rejects the graph.
- A non-solid state producing operation has no effect measurements.

## Ordering and duplicate handling

- CAD graph entities, relations, and measurements are sorted by their graph keys
  before writing.
- Duplicate `node_id`, `relation_id`, or `measurement_id` is a graph error, not
  a merge.
- A duplicate extraction row is rejected; it is not resolved by last-write-wins.

## Validation

Reject before writing when:

- an AST operation has no runtime recording;
- a solid state producing operation has no state or effect;
- a CadQuery selector result has no state or a selected ID outside that state;
- a CadQuery workplane frame has no AST record;
- a measurement or relation endpoint is missing;
- a graph ID is not deterministic from its documented components;
- an extraction entity or measurement has an unknown schema version.
