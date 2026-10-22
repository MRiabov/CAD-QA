# Method signatures

**Parent:** [`extraction/README.md`](../../README.md).

This document is the closed P0/P1 call contract. It complements the operation
classification in [`pipeline.md`](pipeline.md). `02a` accepts a call only when
the receiver binding, argument names, and arity match this table.

## Notation

- `WP` means a CadQuery workplane binding.
- `SH` means a shape binding created by `val`, `first`, `findSolid`, a shape
  constructor, or `cq.Workplane(obj=...)` is not accepted.
- `EDGE` and `WIRE` mean the constructor binding from `cq.Edge.*` and
  `cq.Wire.*`.
- `MODULE` means the `cq` alias.
- Required arguments are bare; optional arguments are in brackets.
- `EXPR` is any accepted [`AstExpression`](../features/expressions.md).
- `CALLABLE` is the narrow filter lambda.
- Unknown keyword arguments, excess positional arguments, and missing required
  arguments reject the program.
- Argument value categories are not evaluated during AST extraction. A category
  mismatch is a runtime failure in `02b`.

## Constructors

| Call form | Receiver | Required | Optional | Result | Operation | State |
|---|---|---|---|---|---|---|
| `cq.Workplane(inPlane, origin)` | `MODULE` | `inPlane` | `origin` | `workplane` | `workplane` | no |
| `cq.Workplane(cq.Plane(...))` | `MODULE` | `plane` | none | `workplane` | `workplane` | no |
| `cq.Plane(origin, xDir, normal)` | expression only | `origin` | `xDir`, `normal` | `plane` | expression | no |
| `cq.Vector(...)` | expression only | none | 2 or 3 numbers | `vector` | expression | no |
| `cq.Edge.makeLine(v1, v2)` | `MODULE` | `v1`, `v2` | none | `edge` | `path` | no |
| `cq.Edge.makeSpline(listOfVector)` | `MODULE` | `listOfVector` | `tangents`, `periodic`, `parameters`, `scale`, `tol` | `edge` | `path` | no |
| `cq.Edge.makeCircle(radius)` | `MODULE` | `radius` | `pnt`, `dir`, `angle1`, `angle2`, `orientation` | `edge` | `path` | no |
| `cq.Wire.makePolygon(listOfVertices)` | `MODULE` | `listOfVertices` | `forConstruction`, `close` | `wire` | `path` | no |
| `cq.Wire.assembleEdges(listOfEdges)` | `MODULE` | `listOfEdges` | none | `wire` | `path` | no |
| `cq.Solid.makeSphere(radius)` | `MODULE` | `radius` | `pnt`, `dir`, `angleDegrees1`, `angleDegrees2`, `angleDegrees3` | `shape` | `solid` | yes |
| `cq.Solid.fuse(self, ...)` | `MODULE` | `self` | `*toFuse`, `glue`, `tol` | `shape` | `assembly` | yes |
| `cq.Compound.fuse(self, ...)` | `MODULE` | `self` | `*toFuse`, `glue`, `tol` | `shape` | `assembly` | yes |
| `cq.NearestToPointSelector(pnt)` | expression only | `pnt` | none | `selector` | expression | no |

`cq.Workplane(..., obj=...)` is rejected. The P0/P1 CadQuery programs do not use
a non-null `obj`, and accepting it would make the initial state ambiguous.

## CadQuery workplane methods

| Method | Receiver | Required | Optional | Result | Operation | State |
|---|---|---|---|---|---|---|
| `workplane` | `WP` | none | `offset`, `invert`, `centerOption`, `origin` | `workplane` | `workplane` | no |
| `workplaneFromTagged` | `WP` | `name` | none | `workplane` | `workplane` | no |
| `transformed` | `WP` | none | `rotate`, `offset` | `workplane` | `workplane` | no |
| `center` | `WP` | `x`, `y` | none | `workplane` | `sketch` | no |
| `translate` | `WP` | `vec` | none | `workplane` | `transform` | yes |
| `rotate` | `WP` | `axisStartPoint`, `axisEndPoint`, `angleDegrees` | none | `workplane` | `transform` | yes |
| `mirror` | `WP` | none | `mirrorPlane`, `basePointVector`, `union` | `workplane` | `transform` | yes |
| `tag` | `WP` | `name` | none | `workplane` | `modifier` | no |
| `toPending` | `WP` | none | none | `workplane` | `modifier` | no |

## Sketch and path methods

| Method | Receiver | Required | Optional | Result | Operation | State |
|---|---|---|---|---|---|---|
| `moveTo` | `WP` | none | `x`, `y` | `workplane` | `path` | no |
| `lineTo` | `WP` | `x`, `y` | `forConstruction` | `workplane` | `path` | no |
| `hLine` | `WP` | `distance` | `forConstruction` | `workplane` | `path` | no |
| `vLine` | `WP` | `distance` | `forConstruction` | `workplane` | `path` | no |
| `threePointArc` | `WP` | `point1`, `point2` | `forConstruction` | `workplane` | `path` | no |
| `polyline` | `WP` | `listOfXYTuple` | `forConstruction`, `includeCurrent` | `workplane` | `path` | no |
| `close` | `WP` | none | none | `workplane` | `path` | no |
| `line` | `WP` | `xDist`, `yDist` | `forConstruction` | `workplane` | `path` | no |
| `spline` | `WP` | `listOfXYTuple` | `tangents`, `periodic`, `parameters`, `scale`, `tol`, `forConstruction`, `includeCurrent`, `makeWire` | `workplane` | `path` | no |
| `splineApprox` | `WP` | `points` | `tol`, `minDeg`, `maxDeg`, `smoothing`, `forConstruction`, `includeCurrent`, `makeWire` | `workplane` | `path` | no |
| `wire` | `WP` | none | `forConstruction` | `workplane` | `path` | no |
| `circle` | `WP` | `radius` | `forConstruction` | `workplane` | `sketch` | no |
| `rect` | `WP` | `xLen`, `yLen` | `centered`, `forConstruction` | `workplane` | `sketch` | no |
| `ellipse` | `WP` | `x_radius`, `y_radius` | `rotation_angle`, `forConstruction` | `workplane` | `sketch` | no |
| `polygon` | `WP` | `nSides`, `diameter` | `forConstruction`, `circumscribed` | `workplane` | `sketch` | no |
| `slot2D` | `WP` | `length`, `diameter` | `angle` | `workplane` | `sketch` | no |
| `offset2D` | `WP` | `d` | `kind`, `forConstruction` | `workplane` | `sketch` | no |
| `pushPoints` | `WP` | `pntList` | none | `workplane` | `sketch` | no |

## Solid, boolean, and assembly methods

| Method | Receiver | Required | Optional | Result | Operation | State |
|---|---|---|---|---|---|---|
| `box` | `WP` | `length`, `width`, `height` | `centered`, `combine`, `clean` | `workplane` | `solid` | yes |
| `cylinder` | `WP` | `height`, `radius` | `direct`, `angle`, `centered`, `combine`, `clean` | `workplane` | `solid` | yes |
| `sphere` | `WP` | `radius` | `direct`, `angle1`, `angle2`, `angle3`, `centered`, `combine`, `clean` | `workplane` | `solid` | yes |
| `extrude` | `WP` | `until` | `combine`, `clean`, `both`, `taper` | `workplane` | `solid` | yes |
| `loft` | `WP` | none | `ruled`, `combine`, `clean` | `workplane` | `solid` | yes |
| `sweep` | `WP` | `path` | `multisection`, `sweepAlongWires`, `makeSolid`, `isFrenet`, `combine`, `clean`, `transition`, `normal`, `auxSpine` | `workplane` | `solid` | yes |
| `revolve` | `WP` | none | `angleDegrees`, `axisStart`, `axisEnd`, `combine`, `clean` | `workplane` | `solid` | yes |
| `twistExtrude` | `WP` | `distance`, `angleDegrees` | `combine`, `clean` | `workplane` | `solid` | yes |
| `text` | `WP` | `txt`, `fontsize`, `distance` | `combine`, `clean`, `font`, `fontPath`, `kind`, `halign`, `valign` | `workplane` | `solid` | yes |
| `union` | `WP` | none | `toUnion`, `clean`, `glue`, `tol` | `workplane` | `boolean` | yes |
| `cut` | `WP` | `toCut` | `clean`, `tol` | `workplane` | `boolean` | yes |
| `intersect` | `WP` | `toIntersect` | `clean`, `tol` | `workplane` | `boolean` | yes |
| `combine` | `WP` | none | `clean`, `glue`, `tol` | `workplane` | `assembly` | yes |
| `newObject` | `WP` | `objlist` | none | `workplane` | `assembly` | no |
| `add` | `WP` | `obj` | none | `workplane` | `assembly` | no |
| `cutBlind` | `WP` | `until` | `clean`, `both`, `taper` | `workplane` | `modifier` | yes |
| `cutThruAll` | `WP` | none | `clean`, `taper` | `workplane` | `modifier` | yes |
| `hole` | `WP` | `diameter` | `depth`, `clean` | `workplane` | `modifier` | yes |
| `cskHole` | `WP` | `diameter`, `cskDiameter`, `cskAngle` | `depth`, `clean` | `workplane` | `modifier` | yes |
| `cboreHole` | `WP` | `diameter`, `cboreDiameter`, `cboreDepth` | `depth`, `clean` | `workplane` | `modifier` | yes |
| `fillet` | `WP` | `radius` | none | `workplane` | `modifier` | yes |
| `chamfer` | `WP` | `length` | `length2` | `workplane` | `modifier` | yes |
| `shell` | `WP` | `thickness` | `kind` | `workplane` | `modifier` | yes |
| `split` | `WP` | none | positional and keyword expressions | `workplane` | `modifier` | yes |
| `clean` | `WP` | none | none | `workplane` | `modifier` | yes |
| `rarray` | `WP` | `xSpacing`, `ySpacing`, `xCount`, `yCount` | `center` | `workplane` | `modifier` | yes |

`newObject` and `add` are stack assembly operations. They may produce an empty
CadQuery workplane, so they are not solid state producing. `combine` is solid state producing
because it resolves the stack into one shape.

## Selectors and accessors

| Method | Receiver | Required | Optional | Result | Operation | State |
|---|---|---|---|---|---|---|
| `faces` | `WP` | none | `selector`, `tag` | `workplane` | `cadquery_selector` | no |
| `edges` | `WP` | none | `selector`, `tag` | `workplane` | `cadquery_selector` | no |
| `vertices` | `WP` | none | `selector`, `tag` | `workplane` | `cadquery_selector` | no |
| `filter` | `WP` | `f` | none | `workplane` | `cadquery_selector` | no |
| `val` | `WP` | none | none | `shape` or `none` | `accessor` | no |
| `vals` | `WP` | none | none | `shape_list` | `accessor` | no |
| `all` | `WP` | none | none | `workplane_list` | `accessor` | no |
| `first` | `WP` | none | none | `workplane` | `accessor` | no |
| `findSolid` | `WP` | none | `searchStack`, `searchParents` | `shape` | `accessor` | no |
| `Edges` | `SH` | none | none | `shape_list` | `accessor` | no |
| `Solids` | `SH` | none | none | `shape_list` | `accessor` | no |
| `Length` | `EDGE` | none | none | `scalar` | `accessor` | no |

`faces`, `edges`, and `vertices` accept only a string, `cq.NearestToPointSelector`,
or no CadQuery selector. `wires` and `solids` are not accepted CadQuery selectors.

`Edges` and `Solids` are shape accessors. They do not create graph entities and
are not graph-addressable. They are allowed only as value or assembly input.

## Special list form

`list(<accessor>.vals())` is accepted only when `<accessor>` is a `WP` with a
face, edge, or vertex selection. The result is a Python `list`.

## Rejection summary

Reject when:

- the receiver binding does not match the table;
- a required argument is missing;
- an unknown keyword argument is present;
- a positional count is outside the table;
- `cq.Workplane` has a non-null `obj`;
- `wires` or `solids` is used as a CadQuery selector;
- `Edges` or `Solids` is used on a CadQuery workplane instead of a shape.
