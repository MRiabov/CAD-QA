# 02a extract CadQuery AST — structure without execution

> Authoritative: `../02a-extract-cadquery-ast.md`
> Algorithm: `../extraction/ast/algorithm/pipeline.md`
> Models: `models/02-execute-cadquery-and-build-graph.md`

READ:

- `NormalizedProgram` → `program_id, program_sha256, normalization_version, canonical_text`

TRANSFORM:

- parse `canonical_text` with the Python AST
- run the algorithm passes in order
- resolve names to earlier assignments in program order
- preserve assignment order and program line numbers
- record operations, workplanes, profiles, paths, and selectors with canonical IDs
- enforce the accepted subset: module-level `import cadquery as cq`; module-level assignments; literals, names, attributes, subscripts, and calls; one CadQuery call per top-level assignment with no chained calls in P0/P1; face, edge, and vertex selectors; no `def`, `class`, loop, conditional, comprehension, `try`, or `with`; no lambda except the narrow `filter` predicate; no `eval`, `exec`, dynamic import, file access, or network access; allowlisted CadQuery methods only; `Edges` and `Solids` only as shape accessors on shape bindings
- enforce the AST invariants: exactly one `import cadquery as cq` and no other statement except top-level assignments; one `Name` target per assignment with no rebinding; one top-level call per call assignment with no starred arguments; every receiver and input variable defined earlier in program order; `order` = zero-based assignment index; every solid state producing method carries `feature_kind` and `solid_kind`; every ID unique and in its documented format; every CadQuery selector has a face, edge, or vertex category; every CadQuery workplane reference resolves and carries an explicit frame status; the final assignment is `result`, a call or an alias
- record one `AstOperation` per call assignment: `operation_id, order, source_line, source_span, result_var, method, operation_kind, receiver, receiver_var, args, kwargs, input_vars, is_state_producing, feature_kind, solid_kind`; `operation_id = op:<order:06d>`
- record one `AstAlias` per non-call assignment: `alias_id, alias_kind, order, source_line, result_var, target_var, target_expression, source_span`; an alias consumes an assignment index and no operation ID
- record a CadQuery selector written as a string, as an implicit no-argument call, or as a `cq.NearestToPointSelector` call; do not resolve a CadQuery selector to an entity
- reject the whole program on the first failed validation with a reason from `syntax, import, module_shape, assignment_shape, unsupported_expression, unsupported_call, chained_call, unknown_method, unresolved_name, duplicate_target, missing_result, invalid_id, invalid_reference, internal`; the row carries that reason's disposition from `../extraction/validation.md`; the result is never partial
- report the earliest failure in this order: syntax and module shape; import; assignment shape and chained calls; unknown method and unsupported expression; unresolved name and duplicate target; missing final `result`; AST reference and ID validation
- do not execute CadQuery and do not produce geometry measurements

WRITE:

- `CadQueryAstExtractionResult` `(program_sha256, extractor version)` → `program_id, program_sha256, normalization_version, imports, operations, workplanes, profiles, paths, selectors`
- `ast_*` Parquet tables; no geometry measurements
- failure partition `02a_extract_cadquery_ast`
