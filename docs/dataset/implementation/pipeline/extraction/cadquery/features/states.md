# CadQuery states

**Parent:** [`../algorithm/runtime.md`](../algorithm/runtime.md).

A state is the shape after a state-producing operation. States are recorded after
the instrumented assignment returns. The capture algorithm is in
[`../algorithm/runtime.md`](../algorithm/runtime.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `state_id` | string | CadQuery | yes | `state:<operation_id>`. | 02c |
| `operation_id` | string | AST | yes | Producing operation. | 02c |
| `shape_hash` | sha256 | CadQuery | yes | Canonical shape identity from the entity table. | 02c |
| `is_solid` | boolean | CadQuery | yes | Shape contains at least one solid. | 02c |
| `is_valid` | boolean | CadQuery | yes | Kernel validity result. | 02c |
| `volume` | double | CadQuery | yes | Volume in cubic millimetres. | 02c |
| `bbox_min` | Point3D | CadQuery | yes | Minimum bounding-box corner. | 02c |
| `bbox_max` | Point3D | CadQuery | yes | Maximum bounding-box corner. | 02c |
| `centroid` | Point3D | CadQuery | yes | Centroid in the program frame. | 02c |
| `face_count` | integer | CadQuery | yes | Face count. | 02c |
| `edge_count` | integer | CadQuery | yes | Edge count. | 02c |
| `vertex_count` | integer | CadQuery | yes | Vertex count. | 02c |
| `entity_table_ref` | string | CadQuery | yes | `entity:<state_id>`. | cadquery/solids |
| `source_span` | SourceSpan | AST | yes | Producing assignment span. | review |

The kernel calls for volume, bounding box, centroid, counts, validity, and
solid detection are in [`../algorithm/geometry-classification.md`](../algorithm/geometry-classification.md).

## Capture rules

- Record a state only for an operation classified `state-producing` and only
  when its runtime result contains a solid.
- A non-solid result for a state-producing operation is a `non_solid_result`
  failure.
- An invalid shape is recorded with `is_valid = false`; it cannot support an
  answer.
- A failed operation produces a failure tombstone, not a state.
- The final state is the last shape snapshot in operation order. If a program
  produces no state, execution fails with `no_state`.
- Counts and geometry are measured, not derived from program text.
- State identity is the canonical entity table plus `shape_hash`; raw BRep is not
  persisted.
