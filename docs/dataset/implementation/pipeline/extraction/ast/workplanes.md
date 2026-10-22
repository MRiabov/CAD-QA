# AST workplanes

**Parent:** [`extraction/README.md`](../README.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `workplane_id` | string | AST | yes | `wp:<operation_id>`. Stable within the program. | 02c |
| `operation_id` | string | AST | yes | Creating operation. | 02b, 02c |
| `workplane_kind` | WorkplaneKind | AST | yes | Named, custom, or face. | 02c |
| `named_plane` | NamedPlane or null | AST | no | `xy`, `yz`, or `xz` for a named plane. | 02c |
| `origin` | Point3 | AST | yes | Origin from the constructor. | 02c |
| `x_direction` | Vector3 | AST | yes | X direction from the constructor. | 02c |
| `normal` | Vector3 | AST | yes | Normal from the constructor. | 02c |
| `offset` | double or null | AST | no | CadQuery workplane offset. | 02c |
| `tag` | string or null | AST | no | Tag used by `workplaneFromTagged`. | 02c |
| `source_span` | SourceSpan | AST | yes | Span of the creating call. | review |

Extraction sources:

- `cq.Workplane('XY', origin=...)` → named plane.
- `cq.Workplane(cq.Plane(...))` → custom plane with origin, x direction, and normal.
- `.workplane(offset=...)` → derived frame from the receiver.
- `.workplaneFromTagged(tag)` → frame from a tag.
- `.transformed(...)` → frame with a transform applied.
- `.faces(...).workplane()` → face frame; the face entity ID is carried separately.

The runtime frame is measured in [`cadquery/states.md`](../cadquery/states.md).
