# 01d normalize programs — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../01d-normalize-programs.md`](../01d-normalize-programs.md), with the failure
row schema in [`../../failure-record.md`](../../failure-record.md).

## Happy-path integration test (test-first, adversarial)

`test_01d_normalization_happy_path_adversarial` — normalizes the active rows of
the `01c` pool fixture with the real Python `ast` and the pinned Ruff version,
and asserts the persisted normalized program read back through the reader `02a`
extract CadQuery AST uses.

**Given** these active rows:

- `messy`: a BOM, CRLF line endings, comments, single quotes, redundant
  parentheses, unsorted imports, and an unused import;
- `messy_reformatted`: the same program, written with different formatting and
  no comments;
- `canonical`: text that is already in normalized form;
- `broken`: a program with a syntax error;
- `binary`: bytes that do not decode as UTF-8.

**When** `01d` normalizes them.

**Then** assert the persisted normalized program:

- `messy`'s text has `\n` line endings, no BOM, and no comments; quotes and
  parentheses are Ruff's output, and the unused import and the unsorted import
  order survive, because only `ruff format` runs and no lint fix does;
- the text ends with exactly one newline;
- `program_sha256` equals the SHA-256 the test recomputes over the stored text
  bytes, not a value copied from another field;
- `program_id` is `cadqaprog:<program_sha256>`;
- `raw_program_sha256` equals the SHA-256 of the pool text as received, so it
  differs from `program_sha256` for `messy` and equals it for `canonical`;
- `normalization_version` carries the Python version, the Ruff version, the Ruff
  configuration hash, and the algorithm version;
- `cadevolve_program_family_id` and the collection survive the step;
- `messy`, `messy_reformatted`, and `canonical` share one `program_id`, all three
  rows are written, and one of the duplicates is recorded against the other;
- `broken` and `binary` have no normalized row, and each has one failure record
  naming `syntax_error` with a `source_line` and `invalid_utf8` without one.

`test_01d_canonical_text_is_idempotent` — normalizing `canonical` a second time
returns the same bytes and the same `program_id`. Without this, `program_sha256`
is not an identity and every downstream artifact key is unstable.

`test_01d_reserve_rows_are_not_normalized` — a reserve row in the pool has no
normalized row. Promotion is `03a`'s decision.

`test_01d_duplicate_program_is_kept` — the duplicate record is not dropped at
`01d`. Both rows carry the same `program_id`, and the duplicate record says
which row it duplicates. Uniqueness by `program_id` is the reader's rule, not a
delete here.

**TDD pin:** pins the canonical bytes, the hash over stored bytes, the
`cadqaprog:` prefix, the no-lint rule, the shared identity of the three
variants, and the two failure reasons before `01d` exists.

## Failure-mode tests

- `test_01d_version_pin` — a changed Ruff version changes
  `normalization_version` and the artifact identity, and a cached result from the
  old version is not read. A re-run at the same version is byte-identical.
- `test_01d_no_partial_program` — a program that fails formatting writes no
  normalized row and no half-written text; the failure record is the only record
  of the attempt.
- `test_01d_failure_row_is_deterministic` — the same failure twice produces the
  same `failure_id` and `occurrence_count` 2, not two rows.
- `test_01d_never_executes` — a program that raises at import time still
  normalizes, because `01d` parses and formats but never imports or runs it.

## What this does not prove

- That the program is executable. That is `02b-execute-cadquery.md`.
- That the text is accepted by the AST subset. That is
  `02a-extract-cadquery-ast.md`.
- That the pool is complete. That is `01c-fetch-program-pool.md`.
