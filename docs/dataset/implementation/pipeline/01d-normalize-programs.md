# 01d — Normalize programs

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** produce canonical program text, a stable program ID, and the hash
used by graph build, overlap checks, and release grouping.

## Input / output

- Input: the active rows of the program pool from `01c`. Reserve rows are
  normalized only when `03a` allocate task quotas promotes them.
- Output: normalized program records with `program_id`, `canonical_text`,
  normalization version, `program_sha256`, `raw_program_sha256`, and
  `cadevolve_program_family_id`.

## Normalization algorithm

Normalization uses the Python AST and Ruff in this order:

1. Decode the cache text as UTF-8; reject invalid input.
2. Normalize line endings to `\n` and strip a byte-order mark.
3. Parse with a pinned Python `ast` version. A syntax error rejects the program.
4. Reconstruct program text with `ast.unparse`.
5. Format with a pinned `ruff format` version and pinned Ruff config.
6. Ensure exactly one trailing newline.
7. Encode as UTF-8.
8. Compute `program_sha256` over those exact bytes.
9. Set `program_id` to `cadqaprog:<program_sha256>`.

Use `ruff format` only. Do not run `ruff check --fix`, import sorting, or any
rewrite that could change semantics.

## What normalization drops

- **Comments are dropped.** `ast.unparse` does not preserve them. The prompt
  contract accepts normalized program text, not the original comment stream.
- Program formatting, quote style, and parenthesization may change.
- Variable names are not renamed. P1 duplicate detection may apply a separate
  AST variable-name normalization; that is not this program identity.
- Statement order is preserved.

## Canonical bytes

`program_sha256` is SHA-256 over the final UTF-8 bytes after line-ending
normalization, Ruff formatting, and the single trailing newline. The hash input
is not the original cache text and not a JSON serialization.

`raw_program_sha256` is SHA-256 over the original selected text as received from
the cache. It is provenance, not program identity.

Two records with identical normalized bytes have the same `program_id`. `01d`
records the duplicate; later stages must not treat the records as distinct
programs.

## Normalization version

`normalization_version` pins:

- Python version and `ast.unparse` behavior;
- Ruff version;
- Ruff configuration hash;
- this normalization algorithm version.

A change to any pin is a new normalization version and produces new program
identities.

## Failures

Record a normalization failure as a
[`failure record`](../failure-record.md) with the subject program, the reason,
and `source_line` when available. Do not emit a partial normalized program.

The reason set is closed:

| Reason | Meaning |
|---|---|
| `invalid_utf8` | The cache text does not decode as UTF-8. |
| `syntax_error` | The pinned Python `ast` rejects the text. |
| `format_failure` | The pinned Ruff version fails on the parsed text. |

## Why it exists

The C tier carries upstream normalization; P does not. Neither is our contract.
This step stamps our own canonical text, version, and hash. It may pass most C
records through with small formatting changes; that is expected.

## Not here

It does not run CadQuery, build graphs, or resolve program families.
