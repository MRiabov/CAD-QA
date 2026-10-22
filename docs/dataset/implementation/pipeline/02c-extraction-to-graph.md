# 02c — Extraction-to-graph mapping

**Parent:** [`02c-build-cad-graph.md`](02c-build-cad-graph.md).

**Purpose:** define the deterministic mapping from the extraction contract to
the CAD graph. Table schemas are in [`02c-build-cad-graph.md`](02c-build-cad-graph.md);
this document defines which rows and relations are created.

## Inputs

- `StaticCadQueryModel` from
  [`extraction/README.md`](extraction/README.md);
- `ExecutionResult` from `02b`;
- program metadata from `01d`.

Reject the pair if either hash or any required reference is missing.

## IDs

Extraction IDs are local identities. Graph IDs are UUIDv5 values derived by the
rules in [`02c-build-cad-graph.md`](02c-build-cad-graph.md).

| Graph node category | `local_id` | From |
|---|---|---|
| `cadquery_program` | `program` | Program row. |
| `operation` | `operation_id` | Every call operation. |
| `feature` | `operation_id` | Every state-producing operation. |
| `solid_state` | `state_id` | Every shape snapshot. |
| `face` | `entity_id` | Face entity row. |
| `edge` | `entity_id` | Edge entity row. |
| `vertex` | `entity_id` | Vertex entity row. |
| `edge_endpoint` | `<edge_local_id>:start` or `:end` | Edge endpoints. |
| `cadquery_profile` | `profile_id` | Static CadQuery profile. |
| `cadquery_workplane` | `workplane_id` | Static and measured CadQuery workplane. |
| `cadquery_path` | `path_id` | Static path. |
| `cadquery_path_point` | `<path_local_id>:<ordinal>` | Static path point. |
| `cadquery_path_segment` | `<path_local_id>:<ordinal>` | Static path segment. |
| `region` | `<feature_local_id>:added` or `:removed` | Feature effect region. |
| `cadquery_selector_result` | `selector_result_id` | Runtime CadQuery CadQuery selector result. |

An alias has no graph node. It is consumed when resolving the target binding.

## Graph node construction

1. Create one `cadquery_program` graph node with the program hashes, normalization
   version, extractor version, and execution result hash.
2. Create one `operation` graph node for every static call operation. Use the static
   `operation_kind`, `method`, `order`, `source_line`, and `result_var`.
3. Create one `feature` graph node for every state-producing operation. Use the
   static `feature_kind`.
4. Create one `solid_state` graph node for every Shape snapshot. Set `is_final` on
   the last Shape snapshot in operation order.
5. Create face, edge, vertex, and edge-endpoint graph nodes from every state entity
   table.
6. Create CadQuery profile, CadQuery workplane, path, path-point, path-segment,
   and CadQuery selector-result nodes from the static and runtime records.
7. Create `region` nodes from state-producing operations that have a state:
   - `added` for an operation whose `feature_kind` is `add_material` or
     `construction`;
   - `removed` for an operation whose `feature_kind` is `remove_material`;
   - `modify` operations create no region.
   A first state with no before state creates only the region implied by its
   static feature kind.

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

## Measurement construction

Use the measurement catalog in [`02c-build-cad-graph.md`](02c-build-cad-graph.md).
Every measurement carries `evidence_kind`, `evidence_rule`, and `evidence_refs`
from [`extraction/cadquery/evidence.md`](extraction/cadquery/evidence.md).

From the execution result:

- solid state: `volume`, `bounding_box`, `centroid`, `face_count`,
  `edge_count`, `vertex_count`, `validity`;
- face: `area`, `bounding_box`, `centroid`;
- edge: `length`, `bounding_box`, `centroid`;
- vertex: `centroid`;
- CadQuery selector result: `selected_count`;
- CadQuery workplane: `workplane_frame`;
- operation effect: `volume_change`, `bounding_box_change`, `topology_change`.

From the static model, create only exact derived measurements for operation
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

- Create one `cadquery_workplane` graph node for every static CadQuery workplane.
- Attach the measured `workplane_frame` when the runtime result provides it.
- A static frame that is `unknown` is not a measurement; do not invent one.
- A runtime frame without a static CadQuery workplane rejects the graph.

## Operation effects

- Create one effect measurement set for every state-producing operation with a
  captured effect.
- A state-producing operation without an effect rejects the graph.
- A non-state-producing operation has no effect measurements.

## Ordering and duplicate handling

- Nodes, relations, and measurements are sorted by their graph keys before
  writing.
- Duplicate `node_id`, `relation_id`, or `measurement_id` is a graph error, not
  a merge.
- A duplicate extraction row is rejected; it is not resolved by last-write-wins.

## Validation

Reject before writing when:

- a static operation has no runtime recording;
- a state-producing operation has no state or effect;
- a CadQuery selector result has no state or a selected ID outside that state;
- a CadQuery workplane frame has no static record;
- a measurement or relation endpoint is missing;
- a graph ID is not deterministic from its documented components;
- an extraction entity or measurement has an unknown schema version.
