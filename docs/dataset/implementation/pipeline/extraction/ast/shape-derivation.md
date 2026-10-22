# CadQuery shape and path derivation

**Parent:** [`extraction/README.md`](../README.md).

This document fixes the derived fields for CadQuery profile and path records.
The accepted call forms and argument names are in
[`method-signatures.md`](method-signatures.md).

## Point and segment models

`Point2` has `x` and `y` doubles.

`Point3` has `x`, `y`, and `z` doubles.

`Vector3` has `x`, `y`, and `z` doubles.

`PathSegment` has:

| Field | Field type | Required | Meaning |
|---|---|---|---|
| `segment_kind` | `line`, `arc`, `spline`, or `other` | yes | Segment category. |
| `start` | Point2 or Point3 or null | no | Start point when fixed. |
| `end` | Point2 or Point3 or null | no | End point when fixed. |
| `control_points` | list of Point2 or Point3 | yes | Points supplied to the call; empty when none. |
| `center` | Point2 or Point3 or null | no | Arc or circle center when fixed. |
| `radius` | double or null | no | Arc or circle radius when fixed. |
| `start_angle` | double or null | no | Start angle in degrees when fixed. |
| `end_angle` | double or null | no | End angle in degrees when fixed. |
| `normal` | Vector3 or null | no | Plane normal for a 3D arc or circle. |
| `is_closed` | boolean | yes | Segment closes on itself. |

## Literal point extraction

A point expression is accepted as fixed only when it is:

- a two- or three-element list or tuple of numeric literals;
- a `cq.Vector` call whose arguments are numeric literals;
- a name that resolves to a literal point binding.

If a point contains a non-literal expression, `points` and the segment point
fields are omitted; the expression remains in the operation arguments. Do not
evaluate it statically.

## CadQuery profile derivation

`dimensions` uses the CadQuery argument name as the map key. Positional and
keyword forms bind to the same name.

| Method | `profile_kind` | `dimensions` keys | `points` | Closed |
|---|---|---|---|---|
| `circle` | `circle` | `radius` | none | yes |
| `rect` | `rectangle` | `xLen`, `yLen` | none | yes |
| `ellipse` | `ellipse` | `x_radius`, `y_radius`, `rotation_angle` | none | yes |
| `polygon` | `polygon` | `nSides`, `diameter` | none | yes |
| `slot2D` | `slot` | `length`, `diameter`, `angle` | none | yes |
| `offset2D` | `other` | `d`, `kind` | none | yes |
| `pushPoints` | `other` | none | `pntList` when literal | no |

`dimensions` contains every supplied argument after binding, including optional
arguments that are present. Omitted optional arguments are absent, not null.

`is_closed` is true for the closed profile methods. `pushPoints` is an open point
set.

The CadQuery workplane reference is the receiver binding's current `workplane_id`.
`profile_id` is `<operation_id>:<ordinal>`; the ordinal is program order within the
operation.

## Path derivation

`02a` maintains a path cursor for each CadQuery workplane binding:

- `cursor_start` is the point where the current path began;
- `cursor_end` is the current point;
- `segments` is the ordered segment list for the current path.

A path-producing operation creates one `StaticPath` record and appends one or
more `PathSegment` records. `path_id` is `<operation_id>:<ordinal>`.

| Method | `path_kind` | Segment | Points |
|---|---|---|---|
| `moveTo` | `line` | none | start point |
| `lineTo` | `line` | line | start to `(x, y)` |
| `hLine` | `line` | line | start to `(start.x + distance, start.y)` |
| `vLine` | `line` | line | start to `(start.x, start.y + distance)` |
| `threePointArc` | `arc` | arc | `point1`, `point2` |
| `polyline` | `polyline` | one line per adjacent pair | `listOfXYTuple` |
| `close` | `line` | line | current to `cursor_start` |
| `line` | `line` | line | current to `(current.x + xDist, current.y + yDist)` |
| `spline` | `spline` | spline | `listOfXYTuple` |
| `splineApprox` | `spline` | spline | `points` |
| `wire` | `other` | none | finalizes the pending path |
| `cq.Edge.makeLine` | `line` | line | `v1` to `v2` |
| `cq.Edge.makeSpline` | `spline` | spline | `listOfVector` |
| `cq.Edge.makeCircle` | `arc` | arc or full circle | `pnt`, `radius`, angles |
| `cq.Wire.makePolygon` | `polyline` | one line per adjacent pair | `listOfVertices` |
| `cq.Wire.assembleEdges` | `other` | one segment per edge | edge expressions |

For a path operation, `points` is the ordered point list used by the call.
`segments` is the ordered segment list. `is_closed` is true for `close`, a
`makePolygon` call with `close=True`, and a `makeCircle` call whose angular span
is a full 360 degrees.

For `cq.Wire.assembleEdges`, segment point fields may be omitted because the
edges are expressions. The edge expressions remain in the operation arguments.

## CadQuery workplane reference

The static CadQuery workplane reference is:

- the receiver binding's current `workplane_id` for a CadQuery workplane method;
- null for a standalone `cq.Edge.*` or `cq.Wire.*` constructor.

## Rejection

Reject when:

- a required argument is missing;
- an optional argument name is not in the method signature;
- a CadQuery profile or path method receives a receiver that is not a CadQuery workplane;
- a literal point has the wrong arity or a non-finite number;
- a `wire` call has no pending path on its receiver binding.
