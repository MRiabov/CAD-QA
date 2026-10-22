# CadQuery states

**Parent:** [`extraction/README.md`](../README.md).

A state is the shape after a state-producing operation. States are recorded after
the instrumented assignment returns.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `state_id` | string | CadQuery | yes | `state:<operation_id>`. | 02c |
| `operation_id` | string | AST | yes | Producing operation. | 02c |
| `shape_hash` | sha256 | CadQuery | yes | Canonical shape identity. | 02c |
| `is_solid` | boolean | CadQuery | yes | Shape is a solid or compound solid. | 02c |
| `is_valid` | boolean | CadQuery | yes | Kernel validity result. | 02c |
| `volume` | double | CadQuery | yes | Volume in cubic millimetres. | 02c |
| `bbox_min` | Point3 | CadQuery | yes | Minimum bounding-box corner. | 02c |
| `bbox_max` | Point3 | CadQuery | yes | Maximum bounding-box corner. | 02c |
| `centroid` | Point3 | CadQuery | yes | Centroid in the program frame. | 02c |
| `face_count` | integer | CadQuery | yes | Face count. | 02c |
| `edge_count` | integer | CadQuery | yes | Edge count. | 02c |
| `vertex_count` | integer | CadQuery | yes | Vertex count. | 02c |
| `entity_table_ref` | string | CadQuery | yes | Entity table for this state. | cadquery/solids |
| `source_span` | SourceSpan | AST | yes | Producing assignment span. | review |

## Capture rules

- Record a state only when the recorded result is a solid-producing CadQuery
  object.
- A state with an invalid shape is recorded but cannot support an answer.
- A failed operation produces a failure tombstone, not a state.
- The final state is the state of the final assignment that produces a shape.
- Counts and geometry are measured, not derived from program text.
