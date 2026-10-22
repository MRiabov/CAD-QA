# CadQuery geometry classification

**Parent:** [`extraction/README.md`](../../README.md).

This document fixes the runtime API calls and mappings used to populate shape,
entity, and evidence fields. A failure in any required call is a
`geometry_capture` failure.

## Shape classification

Classify a returned value in this order:

1. `cadquery.Workplane` → `workplane`;
2. `cadquery.ShapeList` → `shape_list`;
3. Python `list` → `workplane_list` for `all`, otherwise `list`;
4. `int`, `float`, `bool`, `str` → `scalar`;
5. `None` → `none`;
6. `cadquery.Plane` → `plane`;
7. `cadquery.Vector` → `vector`;
8. `cadquery.Edge` → `edge`;
9. `cadquery.Wire` → `wire`;
10. any other `cadquery.Shape` subclass → `shape`.

`cadquery.Edge` and `cadquery.Wire` must be checked before the general shape
case because they are shape subclasses.

## Solid state

A state-producing result is a `Workplane` whose `val()` returns a shape, or a
shape returned directly by a shape constructor.

- `is_solid = len(shape.Solids()) >= 1`.
- `is_valid = shape.isValid()`.
- A `Compound` is valid as a state when it contains at least one solid.
- A `Shell`, `Face`, `Edge`, `Wire`, or empty `Compound` is not a state-producing
  result.

Use the returned shape once. Do not call `val()` a second time.

## Measurements

Use these calls and canonicalize the result:

| Field | Call |
|---|---|
| `volume` | `shape.Volume()` |
| `bbox_min`, `bbox_max` | `shape.BoundingBox()` |
| `centroid` | `shape.Center()` |
| `face_count` | `len(shape.Faces())` |
| `edge_count` | `len(shape.Edges())` |
| `vertex_count` | `len(shape.Vertices())` |

For an entity row:

| Entity | Centroid | Bounding box | Other |
|---|---|---|---|
| `face` | `face.Center()` | `face.BoundingBox()` | `face.Area()`, `face.normalAt()` |
| `edge` | `edge.Center()` | `edge.BoundingBox()` | `edge.Length()`, `edge.startPoint()`, `edge.endPoint()` |
| `vertex` | `vertex.toTuple()` | none | none |

`face.normalAt()` is called with its default center. A null or zero-length normal
is a `geometry_capture` failure.

## Face surface classification

Map `face.geomType()` case-insensitively:

| CadQuery value | `FaceSurfaceKind` |
|---|---|
| `PLANE` | `plane` |
| `CYLINDER` | `cylinder` |
| `CONE` | `cone` |
| `SPHERE` | `sphere` |
| `TORUS` | `torus` |
| `BSPLINE` | `bspline` |
| anything else | `other` |

The mapping is closed. Do not infer a face category from its normal or area.

## Curve classification

Map `edge.geomType()` case-insensitively:

| CadQuery value | `EdgeCurveKind` |
|---|---|
| `LINE` | `line` |
| `CIRCLE` | `circle` |
| `ELLIPSE` | `ellipse` |
| `HYPERBOLA` | `hyperbola` |
| `PARABOLA` | `parabola` |
| `BSPLINE` | `bspline` |
| anything else | `other` |

`is_closed = edge.IsClosed()`. A closed edge still records its start and end
points; they may be equal.

## Accessor and assembly results

- `val()` returns one shape or null.
- `vals()` returns a list of shapes.
- `all()` returns a list of CadQuery workplanes; record `workplane_list`.
- `first()` returns a CadQuery workplane.
- `Edges()` and `Solids()` are shape accessors. They return lists and are not
  graph-addressable.
- `Length()` is an edge accessor and returns a scalar.
- `wire()` returns a CadQuery workplane; it does not return a `Wire`.
- `newObject()` and `add()` return a CadQuery workplane but are not
  state-producing.
- `combine()` is state-producing because it resolves the stack.

## CadQuery workplane frames

For a captured CadQuery workplane:

- `origin = workplane.plane.origin`;
- `x_direction = workplane.plane.xDir`;
- `normal = workplane.plane.zDir`.

The frame is measured after the CadQuery workplane operation returns. It is not derived
from the static model.

## Failure behavior

Any exception from a required kernel call is a `geometry_capture` failure with
the operation ID and program span. Do not substitute zero, null, or a guessed
category. The failure kinds are listed in [`../../validation.md`](../../validation.md).
