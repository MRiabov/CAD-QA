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
- `args` and `kwargs`, as typed literal values;
- `operation_kind`: CadQuery workplane, sketch, solid, CadQuery selector,
  boolean, modifier, or transform.

`StaticWorkplane` records its origin, x direction, and normal.
`StaticProfile` records its CadQuery profile kind and dimensions or points.
`StaticPath` records its CadQuery path kind, points, or curve expression.
`StaticSelector` records the CadQuery selector expression and the variable it
selects from.

## Accepted subset

The P0/P1 input is the CADEvolve-C programs, so the accepted subset is deliberately
narrow:

- module-level `import cadquery as cq`;
- module-level assignments;
- literals, names, attributes, subscripts, and calls;
- calls on CadQuery objects, including chained calls;
- CadQuery selectors written as strings or selector calls;
- no function or class definitions;
- no loops, conditionals, comprehensions, lambdas, `try`, or `with`;
- no `eval`, `exec`, dynamic imports, file access, or network access.

A program outside this subset is rejected as a whole. The static model is never
partial: a rejected program records the reason and produces no operations.

## Behavior

- Parse the normalized program with the Python AST.
- Resolve names to earlier assignments in program order.
- Preserve call order and program line numbers.
- Record CadQuery workplanes, profiles, paths, and selectors.
- Do not execute CadQuery and do not produce geometry measurements.

## Open questions

- Which CadQuery methods form the supported allowlist? The allowlist must cover
  the operations in `graph-content.md` and reject everything else.
- Should P2 support arbitrary Python control flow in P-tier programs, or keep
  the canonical-flat restriction and reject non-flat programs?
- Should an unresolved selector string be rejected at static extraction, or
  deferred to execution and recorded as a failure tombstone?
