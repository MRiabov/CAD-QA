# 02a extract CadQuery AST — structure without execution

> Authoritative: `../02a-extract-cadquery-ast.md`

READ:
- `NormalizedProgram` → `program_id, program_sha256, normalization_version, canonical_text`

TRANSFORM:
- parse `canonical_text` with the Python AST
- run the passes in `../extraction/ast/algorithm/pipeline.md` in order
- resolve names to earlier assignments in program order
- preserve assignment order and program line numbers
- record operations, workplanes, profiles, paths, and selectors with canonical IDs
- enforce the accepted subset: module-level `import cadquery as cq`; module-level assignments; literals, names, attributes, subscripts, and calls; one CadQuery call per top-level assignment with no chained calls in P0/P1; face, edge, and vertex selectors; no `def`, `class`, loop, conditional, comprehension, `try`, or `with`; no lambda except the narrow `filter` predicate; no `eval`, `exec`, dynamic import, file access, or network access; allowlisted CadQuery methods only; `Edges` and `Solids` only as shape accessors on shape bindings
- reject the whole program on the first failed validation; the result is never partial
- do not execute CadQuery and do not produce geometry measurements

WRITE:
- `CadQueryAstExtractionResult` `(program_sha256, extractor version)` → `program_id, program_sha256, normalization_version, imports, operations, workplanes, profiles, paths, selectors`
- `ast_*` Parquet tables; no geometry measurements
- failure partition `02a_extract_cadquery_ast`
