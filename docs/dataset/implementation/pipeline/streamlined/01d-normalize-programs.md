# 01d normalize programs — canonical text and identity

> Authoritative: `../01d-normalize-programs.md`

READ:

- active rows of `ProgramPool` → program text, `cadevolve_program_family_id`; `program_id` is derived from `program_sha256`

TRANSFORM:

- decode the text as UTF-8; invalid input rejects
- normalize line endings to `\n`; strip a byte-order mark
- parse with the pinned Python `ast` version; a syntax error rejects
- reconstruct text with `ast.unparse`
- format with the pinned `ruff format` version and pinned Ruff config; no `ruff check --fix`, no import sorting, no semantic rewrite
- ensure exactly one trailing newline; encode as UTF-8
- `program_sha256` = SHA-256 over those exact bytes
- `program_id` = `cadqaprog:<program_sha256>`
- `raw_program_sha256` = SHA-256 over the original selected text; provenance only
- `normalization_version` pins the Python version and `ast.unparse` behavior, the Ruff version, the Ruff config hash, and the algorithm version
- identical normalized bytes → identical `program_id`; record the duplicate
- a rejection writes a failure row with reason `invalid_utf8 | syntax_error | format_failure`, the subject program, and `source_line` when known; never emit a partial program
- reserve rows are not normalized until `03a` promotes them

WRITE:

- normalized program Parquet `(program_sha256, normalization_version)` → `program_id, canonical_text, normalization_version, program_sha256, raw_program_sha256, cadevolve_program_family_id`
- failure partition `01d_normalize_programs`
