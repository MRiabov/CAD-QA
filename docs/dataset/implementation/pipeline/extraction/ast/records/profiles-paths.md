# AST profiles and paths

**Parent:** [`../algorithm/pipeline.md`](../algorithm/pipeline.md).

## CadQuery profile

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `profile_id` | string | AST | yes | `{operation_id}:{ordinal}`. | 02c |
| `operation_id` | string | AST | yes | Creating operation. | 02b, 02c |
| `profile_kind` | ProfileKind | AST | yes | Rectangle, circle, ellipse, polygon, slot, or other. | 02c |
| `dimensions` | map of string to StaticExpression | AST | yes | Unevaluated dimensions. | 02c |
| `points` | list of Point2D | AST | no | CadQuery profile points, when fixed. | 02c |
| `is_closed` | boolean | AST | yes | Closed boundary flag. | 02c |
| `workplane_id` | string or null | AST | no | CadQuery workplane used. | 02c |
| `source_span` | SourceSpan | AST | yes | Span of the creating call. | review |

## CadQuery path

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `path_id` | string | AST | yes | `{operation_id}:{ordinal}`. | 02c |
| `operation_id` | string | AST | yes | Creating operation. | 02b, 02c |
| `path_kind` | PathKind | AST | yes | Line, polyline, spline, arc, helix, or other. | 02c |
| `points` | list of Point3D | AST | no | Fixed control or sample points. | 02c |
| `segments` | list of PathSegment | AST | no | Segment records. | 02c |
| `is_closed` | boolean | AST | yes | Closed path flag. | 02c |
| `workplane_id` | string or null | AST | no | CadQuery workplane used. | 02c |
| `source_span` | SourceSpan | AST | yes | Span of the creating call. | review |

## Mapping

- CadQuery profile methods: `circle`, `rect`, `ellipse`, `polygon`, `slot2D`, `offset2D`,
  `pushPoints`.
- Path methods: `moveTo`, `lineTo`, `hLine`, `vLine`, `threePointArc`,
  `polyline`, `close`, `line`, `spline`, `splineApprox`.
- Path constructors: `cq.Edge.makeLine`, `cq.Edge.makeSpline`,
  `cq.Edge.makeCircle`, `cq.Wire.makePolygon`, `cq.Wire.assembleEdges`.

A closed CadQuery profile may be used as a CadQuery profile. A path used by a sweep or
other path operation is a CadQuery path. Both records may reference the same
operation.

The derivation tables, point models, and literal-point rules are in
[`CadQuery shape and path derivation`](../algorithm/shape-derivation.md).
`profile_id` and `path_id` use `<operation_id>:<ordinal>`; the ordinal is the
program order within the operation. `workplane_id` is the receiver binding's
current CadQuery workplane, or null for a standalone constructor path.
