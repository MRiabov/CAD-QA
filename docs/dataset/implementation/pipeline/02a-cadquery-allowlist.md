# 02a — CadQuery allowlist

**Parent:** [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md).

**Purpose:** state exactly which CadQuery calls the P0/P1 CADEvolve-C programs
may use and how each maps into the static model.

The allowlist is closed. An unlisted method or constructor rejects the whole
program; there is no best-effort fallback.

## Call rules

- The only accepted import is `import cadquery as cq`.
- Root assignments are `wpN = <expression>` or `result = <expression>`.
- `cq.Workplane`, `cq.Plane`, and `cq.Vector` may appear as nested constructor
  expressions.
- P0/P1 use one CadQuery call per top-level assignment. Chained calls are a P2
  extension; the CADEvolve-C corpus uses flat assignments.
- Arguments and keyword arguments are `StaticExpression` trees, not literals.
- `filter` accepts one narrow lambda form:
  `filter(lambda e: e.Length() < <number>)` or `<=`.
- `list(...)` is accepted only as `list(<accessor>.vals())`.
- Complements, arbitrary lambdas, user functions, imports, loops, conditionals,
  `try`, `with`, comprehensions, `eval`, and `exec` are rejected.

## Constructors and workplanes

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `cq.Workplane` | `StaticWorkplane` plus `StaticOperation` | `workplane` | Start or replace a CadQuery workplane state. |
| `workplane`, `workplaneFromTagged` | `StaticWorkplane` plus `StaticOperation` | `workplane` | Derive a CadQuery workplane from the current solid or tag. |
| `transformed` | `StaticWorkplane` plus `StaticOperation` | transform | Change the CadQuery workplane frame. |
| `center` | `StaticOperation` | sketch | Move the sketch cursor. |
| `translate`, `rotate`, `mirror` | `StaticOperation` | transform | Move or mirror the current shape. |
| `tag` | `StaticOperation` | modifier | Attach a named tag; no geometry change. |
| `toPending` | `StaticOperation` | modifier | Move selected entities to pending state. |

## Sketch, CadQuery profile, and path

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `moveTo`, `lineTo`, `hLine`, `vLine`, `threePointArc`, `polyline`, `close`, `line`, `spline`, `splineApprox` | `StaticPath`; also feeds `StaticProfile` when used as a sketch boundary | path | Build a 2D path or sketch boundary. |
| `circle`, `rect`, `ellipse`, `polygon`, `slot2D`, `offset2D`, `pushPoints` | `StaticProfile` or pending-point record | sketch | Build or position a 2D profile. |
| `cq.Edge.makeLine`, `cq.Edge.makeSpline`, `cq.Edge.makeCircle`, `cq.Wire.makePolygon`, `cq.Wire.assembleEdges` | `StaticPath` | path | Build a path object for a sweep or other path operation. |

## Solid features

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `box`, `cylinder`, `sphere`, `extrude`, `loft`, `sweep`, `revolve`, `twistExtrude`, `text` | `StaticOperation` | solid | Create a solid state. |
| `cq.Solid.makeSphere` | `StaticOperation` | solid | Create a solid state. |

## Boolean and assembly

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `union`, `cut`, `intersect` | `StaticOperation` | boolean | Combine two solid states. |
| `combine`, `newObject`, `add`, `fuse` | `StaticOperation` | assembly | Combine or collect existing solid states. |

## Modifiers

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `cutBlind`, `cutThruAll`, `hole`, `cskHole`, `cboreHole` | `StaticOperation` | modifier | Remove material from the current solid state. |
| `fillet`, `chamfer`, `shell`, `split`, `clean`, `rarray` | `StaticOperation` | modifier | Change topology or repeat a feature. |

## Selectors

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `faces`, `edges`, `vertices` | `StaticSelector` | CadQuery selector | Select graph entities from the current shape. |
| `filter` | `StaticSelector` with a narrow lambda predicate | CadQuery selector | Filter selected entities by `e.Length()` comparison. |
| `cq.NearestToPointSelector` | `StaticSelector` | CadQuery selector | Select by proximity. |

## Accessors

Accessors do not create a solid state. They expose shape lists, individual
shapes, or measurements for later clues and answers.

| Method or constructor | Static mapping | Operation kind | Effect |
|---|---|---|---|
| `val`, `vals`, `all`, `first`, `Edges`, `findSolid`, `Length` | `StaticOperation` | accessor | Read a shape, list, or scalar. |
| `list(<accessor>.vals())` | `StaticExpression` | accessor | Convert a shape list to a Python list. |

## Expressions and special forms

`StaticExpression` covers literal, name, attribute, subscript, call, list, tuple,
dict, and the narrow `lambda` predicate used by `filter`.

`cq.Plane` and `cq.Vector` are expression constructors, not operations. Their
nested calls are preserved in the expression tree and are not evaluated during
static extraction.

## Rejection

Reject the whole program when:

- a method or constructor is not in this allowlist;
- a lambda is not the narrow `filter` predicate;
- `list` is used for anything other than `vals()`;
- an argument contains an unsupported expression;
- a required graph mapping is absent.

`combineSolids` is observed in CADEvolve-C but is not a CadQuery 2.7 method. It is
not in the allowlist and is not rewritten as `combine`; a program that calls it is
rejected at static extraction. This affected 701 CADEvolve-C-core, 41 ABC-C, and
3 ShapeNet-C programs in the local cache.

`wires`, `solids`, `wire`, and `Solids` are observed but rejected in P0/P1
because `02c` has no wire or solid entity category. The unique affected set is
1,391 of 60,896 CADEvolve-C-core, 6,172 of 763,062 ABC-C, and 646 of 105,200
ShapeNet-C programs: 8,209 of the 929,158 C programs (0.88%). They are not
recorded as partial CadQuery selector results.

The deterministic assignment, receiver, expression, and classification rules are
in [`extraction/ast/algorithm.md`](extraction/ast/algorithm.md). CadQuery selector kinds
`implicit`, `string`, `call`, and `filter` are all defined there.

The allowlist version changes whenever a method, call form, or mapping changes.
