# AST extraction algorithm

**Parent:** [`extraction/README.md`](../README.md).

This document defines the deterministic `02a` passes. It is the implementation
contract; the field docs define record shapes.

## Pass order

`02a` runs these passes in order. A failure stops the program; no later pass
runs and no partial static model is emitted.

1. Parse the normalized text with the pinned Python `ast`.
2. Validate the module shape and the single import.
3. Walk top-level assignments in order and build bindings.
4. Build expression trees and classify each assignment.
5. Derive workplanes, profiles, paths, selectors, and aliases.
6. Validate the static model.
7. Emit the static model and the instrumented program.

## Module validation

Accept exactly this module shape:

```text
import cadquery as cq

<top-level assignment>
<top-level assignment>
...
```

Rules:

- The first non-empty statement is `import cadquery as cq`.
- Exactly one import exists; `import cadquery`, other aliases, and
  `from cadquery ...` are rejected.
- Every remaining statement is `ast.Assign` with exactly one target, and the
  target is an `ast.Name`.
- String or constant expression statements, docstrings, `pass`, `assert`,
  `del`, `global`, `nonlocal`, and annotated assignments are rejected.
- No function, class, lambda outside the filter predicate, loop, conditional,
  `try`, `with`, comprehension, generator, `yield`, `await`, `raise`, `match`,
  `eval`, `exec`, dynamic import, attribute assignment, or augmented assignment.
- No target name may be assigned twice. Rebinding is rejected because it makes
  receiver history ambiguous.
- The last assignment target must be `result`.
- At least one assignment exists.

## Assignment forms

A top-level assignment is one of:

| Form | Meaning | Identity |
|---|---|---|
| `name = call(...)` | CadQuery operation | `op:<order:06d>` |
| `name = other_name` | Name alias | `alias:<order:06d>` |
| `name = other_name[expr]` | Subscript alias | `alias:<order:06d>` |

`order` is the zero-based index of the assignment in the module body. The alias
record carries the same `order`; it does not consume an operation ID.

A call assignment must have exactly one top-level CadQuery call. These are
rejected:

- `name = a.b().c()` and any other call whose receiver is a call;
- `name = (lambda: ... )()`;
- `name = f(g())` unless `f` is the special `list` form and `g` is `vals`;
- starred call arguments and `**kwargs`;
- calls on a name that is not a known binding;
- calls whose callee is a call, subscript, or other non-name/non-attribute
  expression.

Nested constructor and accessor calls are allowed only in the forms in
"Expression subset" below.

## Bindings

`02a` maintains an ordered binding table:

| Binding kind | Created by | Used for |
|---|---|---|
| `module` | `cq` | Qualified constructor names. |
| `workplane` | `cq.Workplane`, CadQuery workplane methods, sketch/path/solid/boolean/assembly/modifier/transform methods, selectors. | Receiver of later operations. |
| `shape` | `val`, `first`, `findSolid`, `cq.Solid.makeSphere`. | Shape accessors. |
| `shape_list` | `vals`, `all`, `Edges`. | `list(...)` and CadQuery selector membership. |
| `edge` | `cq.Edge.*`. | Path construction. |
| `wire` | `cq.Wire.*`. | Path construction. |
| `scalar` | `Length`. | Measurements and filter predicates. |
| `list` | `list(vals())`. | Accessor results. |
| `none` | `val` when the runtime value is absent. | Final-state handling. |

A CadQuery workplane binding also carries:

- `workplane_id`: the current static CadQuery workplane, if known;
- `selected_category`: `face`, `edge`, `vertex`, or null;
- `frame_status`: `explicit`, `derived`, or `unknown`.

A binding is never inferred from a variable name. It is determined by the
assignment that created it and the operation classification table below.

## Receiver resolution

The receiver is the `value` of the callee attribute. For `wpN.faces(">Z")`, the
receiver is the `Name` `wpN`; for `cq.Workplane("XY")`, the receiver is `cq`.

- If the receiver is a `Name`, it must resolve to an earlier binding.
- If the receiver is `cq`, it may only be used for an allowed constructor.
- If the receiver is any other expression, the assignment is a chained call and
  is rejected in P0/P1.
- `receiver_var` is the receiver name when the receiver is a `Name`; otherwise
  null.
- The receiver expression is retained as a `StaticExpression` tree for review
  and `02c` provenance.

A call whose callee is a plain name, such as `list(...)`, has no receiver.

## Expression subset

`StaticExpression` accepts:

- constant `int`, `float`, `str`, `bool`, and `None`;
- unary `-` and `+` over a numeric constant or numeric expression;
- `Name`, `Attribute`, and `Subscript`;
- `Call` with positional and keyword arguments, no `*args` or `**kwargs`;
- `List`, `Tuple`, and `Dict`;
- the narrow filter `Lambda`.

Nested calls are limited to:

- `cq.Plane(...)`, `cq.Vector(...)`;
- `cq.Edge.makeLine`, `cq.Edge.makeSpline`, `cq.Edge.makeCircle`;
- `cq.Wire.makePolygon`, `cq.Wire.assembleEdges`;
- `cq.NearestToPointSelector(...)`;
- `e.Length()` inside the filter predicate;
- `vals()` inside the special `list(...)` form.

Any other nested call rejects the program. Expressions are never evaluated
during `02a`.

The filter predicate is exactly:

```text
lambda e: e.Length() < <numeric expression>
lambda e: e.Length() <= <numeric expression>
```

The parameter must be `e`; the attribute must be `Length`; the comparator must
be `<` or `<=`; the right side must be a numeric expression. No other lambda is
accepted.

## Operation classification

The method mapping is closed. Every allowlisted method appears in exactly one
row group below.

### Constructors and workplanes

| Method | `operation_kind` | `result_kind` | State-producing | Notes |
|---|---|---|---|---|
| `Workplane` | `workplane` | `workplane` | no | New static CadQuery workplane; named or custom. |
| `workplane` | `workplane` | `workplane` | no | Derived frame from receiver. |
| `workplaneFromTagged` | `workplane` | `workplane` | no | Frame resolved at runtime. |
| `transformed` | `workplane` | `workplane` | no | Frame resolved at runtime. |

### Sketch, CadQuery profile, and path

| Method | `operation_kind` | `result_kind` | State-producing | Notes |
|---|---|---|---|---|
| `center`, `circle`, `rect`, `ellipse`, `polygon`, `slot2D`, `offset2D`, `pushPoints` | `sketch` | `workplane` | no | CadQuery profile or sketch record. |
| `moveTo`, `lineTo`, `hLine`, `vLine`, `threePointArc`, `polyline`, `close`, `line`, `spline`, `splineApprox` | `path` | `workplane` | no | Path record. |
| `makeLine`, `makeSpline`, `makeCircle`, `makePolygon`, `assembleEdges` | `path` | `edge` or `wire` | no | Constructor path record. |

`makeLine`, `makeSpline`, `makeCircle`, `makePolygon`, and `assembleEdges` are
qualified constructors: `cq.Edge.makeLine`, `cq.Edge.makeSpline`,
`cq.Edge.makeCircle`, `cq.Wire.makePolygon`, and `cq.Wire.assembleEdges`.

### Solid features

| Method | `operation_kind` | `result_kind` | State-producing | `feature_kind` | `solid_kind` |
|---|---|---|---|---|---|
| `box`, `cylinder`, `sphere` | `solid` | `workplane` | yes | `add_material` | `primitive` |
| `makeSphere` | `solid` | `shape` | yes | `add_material` | `primitive` |
| `extrude` | `solid` | `workplane` | yes | `add_material` | `extrude` |
| `loft` | `solid` | `workplane` | yes | `add_material` | `loft` |
| `sweep` | `solid` | `workplane` | yes | `add_material` | `sweep` |
| `revolve` | `solid` | `workplane` | yes | `add_material` | `revolve` |
| `twistExtrude` | `solid` | `workplane` | yes | `add_material` | `twist` |
| `text` | `solid` | `workplane` | yes | `add_material` | `text` |

`makeSphere` is the qualified constructor `cq.Solid.makeSphere`.

### Boolean, assembly, modifiers, transforms

| Method | `operation_kind` | `result_kind` | State-producing | `feature_kind` | `solid_kind` |
|---|---|---|---|---|---|
| `union` | `boolean` | `workplane` | yes | `add_material` | `boolean` |
| `cut` | `boolean` | `workplane` | yes | `remove_material` | `boolean` |
| `intersect` | `boolean` | `workplane` | yes | `modify` | `boolean` |
| `combine` | `assembly` | `workplane` | yes | `construction` | `assembly` |
| `newObject` | `assembly` | `workplane` | yes | `construction` | `assembly` |
| `add`, `fuse` | `assembly` | `workplane` | yes | `add_material` | `assembly` |
| `cutBlind`, `cutThruAll`, `hole`, `cskHole`, `cboreHole` | `modifier` | `workplane` | yes | `remove_material` | `modifier` |
| `fillet`, `chamfer`, `shell`, `split`, `clean`, `rarray` | `modifier` | `workplane` | yes | `modify` | `modifier` |
| `translate`, `rotate`, `mirror` | `transform` | `workplane` | yes | `modify` | `transform` |
| `tag`, `toPending` | `modifier` | `workplane` | no | `modify` | `modifier` |

### Selectors and accessors

| Method | `operation_kind` | `result_kind` | State-producing | Notes |
|---|---|---|---|---|
| `faces`, `edges`, `vertices` | `cadquery_selector` | `workplane` | no | Faces, edges, or vertices only. |
| `filter` | `cadquery_selector` | `workplane` | no | Receiver must carry a face/edge/vertex category. |
| `val` | `accessor` | `shape` or `none` | no | |
| `vals`, `all` | `accessor` | `shape_list` | no | |
| `first` | `accessor` | `shape` or `none` | no | |
| `findSolid` | `accessor` | `shape` | no | |
| `Length` | `accessor` | `scalar` | no | Also allowed inside filter. |
| `list` | `accessor` | `list` | no | Special `list(<accessor>.vals())` form only. |

`wires`, `solids`, `wire`, `Solids`, and `combineSolids` are not in the P0/P1
contract. `combineSolids` is not a CadQuery 2.7 method. The others have no graph
entity category; they are rejected rather than recorded as partial selections.

### Special list form

`list(<accessor>.vals())` is accepted only when `<accessor>` is a CadQuery workplane
binding with a face/edge/vertex selection. It produces a Python `list` of shapes.
Any other `list` use is rejected.

## Static derivation

### Workplanes

A `Workplane` constructor creates a `StaticWorkplane`:

- `cq.Workplane("XY"|"YZ"|"XZ", origin=...)`:
  - named plane;
  - `origin` defaults to `(0, 0, 0)` when absent;
  - named-plane constants:
    - `XY`: x `(1, 0, 0)`, normal `(0, 0, 1)`;
    - `YZ`: x `(0, 1, 0)`, normal `(1, 0, 0)`;
    - `XZ`: x `(1, 0, 0)`, normal `(0, -1, 0)`.
- `cq.Workplane(cq.Plane(...))`:
  - custom plane;
  - explicit frame only when `origin`, `xDir`, and `normal` are all present and
    literal or unary-literal expressions. `cadquery.Plane` defaults `xDir` to
    null, so a missing `xDir` gives `frame_status = unknown`.

`workplane(offset=...)` derives from the receiver frame when the receiver frame
is known: `origin = receiver.origin + offset * receiver.normal`; x direction and
normal are unchanged. Otherwise it records `frame_status = unknown`.

`workplaneFromTagged(tag)` records the tag and `frame_status = unknown`.
`transformed(...)` records its argument expressions and `frame_status = unknown`.
A subsequent `.workplane()` on a face selection records `workplane_kind = face`
and `frame_status = unknown` unless a later runtime frame is captured.

The static frame is intent, not a measurement. `02b` always measures the CadQuery workplane
frame from the executed `Workplane`; `02c` uses that measurement.

### Profiles

| Method | `profile_kind` | Dimensions | Closed |
|---|---|---|---|
| `circle` | `circle` | `radius` | yes |
| `rect` | `rectangle` | `width`, `height` | yes |
| `ellipse` | `ellipse` | `x_radius`, `y_radius` | yes |
| `polygon` | `polygon` | `n`, `diameter` | yes |
| `slot2D` | `slot` | `length`, `diameter` | yes |
| `offset2D` | `other` | `distance` | yes |
| `pushPoints` | `other` | `points` | no |

Dimensions are `StaticExpression` trees. `points` is present only when every
point is a literal or nested `cq.Vector`/tuple of literals. The CadQuery workplane is the
receiver binding's current `workplane_id`.

### Paths

| Method | `path_kind` | Points/segments |
|---|---|---|
| `moveTo`, `lineTo` | `line` | endpoint |
| `hLine`, `vLine` | `line` | endpoint parameter |
| `threePointArc` | `arc` | three points |
| `polyline` | `polyline` | point list |
| `close` | `line` | closing segment |
| `line` | `line` | endpoint |
| `spline`, `splineApprox` | `spline` | control or sample points |
| `cq.Edge.makeLine` | `line` | endpoints |
| `cq.Edge.makeSpline` | `spline` | control points |
| `cq.Edge.makeCircle` | `arc` | center/radius or points |
| `cq.Wire.makePolygon` | `polyline` | point list |
| `cq.Wire.assembleEdges` | `other` | edge list |

The path CadQuery workplane is the receiver binding's current `workplane_id` when the
receiver is a CadQuery workplane; otherwise null for a standalone constructor path.

### Selectors

`faces`, `edges`, and `vertices` create one `StaticSelector`:

- `selector_kind = implicit` when the call has no arguments;
- `selector_kind = string` when the first argument is a string literal;
- `selector_kind = call` when the first argument is
  `cq.NearestToPointSelector(...)`.

`filter` creates `selector_kind = filter` with a `FilterPredicate`. Its receiver
binding must already carry `selected_category`; the result inherits that
category. A `filter` without a prior face/edge/vertex selection rejects the
program.

The `selector_id` ordinal is zero for every P0/P1 selection operation; a future
operation with more than one CadQuery selector must number them in program order.

### Aliases

`name = other_name` records `alias_kind = name` with `target_var`.
`name = other_name[expr]` records `alias_kind = subscript` with
`target_expression` and the root `target_var` when the target resolves to a
binding. An alias copies the target binding's kind, CadQuery workplane ID,
selected category, frame status, and runtime state. It creates no state and no
graph operation.

## Static validation

After derivation:

- every ID is unique and follows the format in the parent README;
- every operation and alias `order` is the assignment index;
- every receiver and input variable resolves to an earlier binding;
- every CadQuery profile, path, and CadQuery selector references an existing operation;
- every CadQuery workplane reference resolves within the program;
- every state-producing method has `feature_kind` and `solid_kind`;
- every CadQuery selector has a known category;
- the final assignment targets `result`;
- no static field is null when the field docs require a value.

A failed check rejects the whole program with the first failing assignment and
the exact reason.

## What `02a` does not do

- It does not import or execute CadQuery.
- It does not evaluate expressions, selectors, or geometry.
- It does not compute measurements, entity IDs, or states.
- It does not assign graph UUIDs.
