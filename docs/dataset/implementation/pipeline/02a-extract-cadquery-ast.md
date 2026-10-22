# 02a — Extract CadQuery AST

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** extract the static structure of a CadQuery program without running
it.

## Input / output

- Input: normalized program text.
- Output: `StaticCadQueryModel`.

## Static model

`StaticCadQueryModel` contains:

- `program_id`, `program_sha256`, and `normalization_version`;
- `imports`: the accepted CadQuery imports;
- `operations`: ordered `StaticOperation` records;
- `workplanes`: `StaticWorkplane` records;
- `profiles`: `StaticProfile` records;
- `paths`: `StaticPath` records;
- `selectors`: `StaticSelector` records;
- `diagnostics`: recoverable observations that do not reject the program.

`StaticOperation` contains:

- `operation_id`, stable within the program;
- `order`, `source_line`, and `result_var`;
- `receiver`, the variable or expression the call is made on;
- `method`, the CadQuery method name;
- `args` and `kwargs`, as `StaticExpression` trees;
- `operation_kind`: CadQuery workplane, sketch, path, solid, CadQuery selector,
  boolean, assembly, modifier, transform, or accessor.

`StaticExpression` is a typed expression tree, not a literal value. The
expression tree contains literal, name, attribute, subscript, call, list, tuple,
dict, and the narrow `filter` lambda. A call records the callee and its argument and keyword
expression trees. This represents nested constructors such as
`cq.Plane(origin=cq.Vector(28, 85, -71), normal=cq.Vector(1, 3, 0))` without
evaluating them.

`StaticWorkplane` records its origin, x direction, and normal.
`StaticProfile` records its CadQuery profile kind and dimensions or points.
`StaticPath` records its CadQuery path kind, points, or curve expression.
`StaticSelector` records the CadQuery selector expression and the variable it
selects from.

## Field contracts

The complete field sets, expression typing, instrumentation rewrite, and runtime
join keys are in [`extraction/README.md`](extraction/README.md). In particular:

- [`extraction/ast/algorithm.md`](extraction/ast/algorithm.md);
- [`extraction/ast/operations.md`](extraction/ast/operations.md);
- [`extraction/ast/expressions.md`](extraction/ast/expressions.md);
- [`extraction/ast/workplanes.md`](extraction/ast/workplanes.md);
- [`extraction/ast/profiles-paths.md`](extraction/ast/profiles-paths.md);
- [`extraction/ast/selectors.md`](extraction/ast/selectors.md);
- [`extraction/ast/instrumentation.md`](extraction/ast/instrumentation.md).

## Accepted subset

The P0/P1 input is the CADEvolve-C programs, so the accepted subset is deliberately
narrow:

- module-level `import cadquery as cq`;
- module-level assignments;
- literals, names, attributes, subscripts, and calls;
- one CadQuery call per top-level assignment; no chained calls in P0/P1;
- CadQuery selectors over faces, edges, or vertices only;
- CadQuery selectors written as strings, implicit no-argument calls, or `cq.NearestToPointSelector` calls;
- no function or class definitions;
- no loops, conditionals, comprehensions, `try`, or `with`;
- no lambdas except the narrow `filter` predicate;
- no `eval`, `exec`, dynamic imports, file access, or network access;
- no CadQuery method or constructor outside the allowlist;
- no wire or solid selector/accessor.

A program outside this subset is rejected as a whole. The static model is never
partial: a rejected program records the reason and produces no operations.

The closed method allowlist and its static mapping are in
[`02a-cadquery-allowlist.md`](02a-cadquery-allowlist.md).

## Behavior

- Parse the normalized program with the Python AST.
- Run the passes in [`extraction/ast/algorithm.md`](extraction/ast/algorithm.md)
  in order.
- Resolve names to earlier assignments in program order.
- Preserve assignment order and program line numbers.
- Record CadQuery workplanes, profiles, paths, and selectors with canonical IDs.
- Reject the program on the first failed validation.
- Do not execute CadQuery and do not produce geometry measurements.

## Open questions

- Should P2 support arbitrary Python control flow in P-tier programs, or keep
  the canonical-flat restriction and reject non-flat programs?

## Resolved questions

- **Method allowlist.** *Resolved 2026-10-21.* The closed CADEvolve-C allowlist is
  in [`02a-cadquery-allowlist.md`](02a-cadquery-allowlist.md). Unknown methods and
  call forms reject the whole program.
- **CadQuery selector timing.** *Resolved 2026-10-21.* Static extraction records
  the CadQuery selector expression and receiver. Evaluation happens in `02b` at
  the call point. Static extraction does not resolve selector strings.
- **P0/P1 selector scope.** *Resolved 2026-10-22.* Only face, edge, and vertex
  selectors are graph-addressable. Wire and solid selectors/accessors reject the
  program until `02c` models those entities.
- **Algorithm completeness.** *Resolved 2026-10-22.* The deterministic pass
  order, assignment rules, expression subset, binding classification, and method
  classification are in [`extraction/ast/algorithm.md`](extraction/ast/algorithm.md).
