# AST workplanes

**Parent:** [`../algorithm/pipeline.md`](../algorithm/pipeline.md).

The static CadQuery workplane record describes the program's intended frame. The measured
frame is captured by [`../../cadquery/algorithm/runtime.md`](../../cadquery/algorithm/runtime.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `workplane_id` | string | AST | yes | `<operation_id>:<ordinal>`. | 02b, 02c |
| `operation_id` | string | AST | yes | Creating operation. | 02c |
| `workplane_kind` | WorkplaneKind | AST | yes | Named, custom, or face. | 02c |
| `named_plane` | NamedPlane or null | AST | no | `xy`, `yz`, or `xz`. | 02c |
| `origin` | Point3D or null | AST | no | Explicit or derived origin, when known. | review |
| `x_direction` | Vector3D or null | AST | no | Explicit or derived x direction, when known. | review |
| `normal` | Vector3D or null | AST | no | Explicit or derived normal, when known. | review |
| `frame_status` | `explicit`, `derived`, or `unknown` | AST | yes | Confidence in the static frame. | review, 02b |
| `derived_from_workplane_id` | string or null | AST | no | Receiver CadQuery workplane for a derived frame. | review |
| `source_selector_id` | string or null | AST | no | Face CadQuery selector that defines a face frame. | 02c |
| `offset` | double or null | AST | no | CadQuery workplane offset. | review |
| `tag` | string or null | AST | no | Tag used by `workplaneFromTagged` or `tag`. | review |
| `args` | list of StaticExpression | AST | yes | Unevaluated constructor or transform arguments. | review |
| `source_span` | SourceSpan | AST | yes | Creating call span. | review |

## Static derivation

- `cq.Workplane('XY'|'YZ'|'XZ', origin=...)` is explicit. The named-plane
  constants are `XY` x `(1, 0, 0)` / normal `(0, 0, 1)`, `YZ` x `(0, 1, 0)` /
  normal `(1, 0, 0)`, and `XZ` x `(1, 0, 0)` / normal `(0, -1, 0)`; the default
  origin is `(0, 0, 0)`.
- `cq.Workplane(cq.Plane(...))` is explicit only when `origin`, `xDir`, and
  `normal` are all present and literal or unary-literal expressions; otherwise
  unknown.
- `workplane(offset=...)` is derived when the receiver frame is known:
  `origin = receiver.origin + offset * receiver.normal`; x direction and normal
  are unchanged.
- `workplaneFromTagged(tag)` is unknown and carries `tag`.
- `transformed(...)` is unknown and carries its arguments.
- A CadQuery workplane derived from a face CadQuery selector is `workplane_kind = face` and
  unknown until runtime; it carries `source_selector_id`.

`frame_status = unknown` is valid. It means the static model does not claim a
frame, not that the program is invalid. `02b` always measures the executed frame.

## CadQuery workplane IDs

`workplane_id` uses the same local identity as `02c`:
`<operation_id>:<ordinal>`. P0/P1 has one CadQuery workplane per operation, so the ordinal
is zero. A future operation with several workplanes numbers them in program order.
