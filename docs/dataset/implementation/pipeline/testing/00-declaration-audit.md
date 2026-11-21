# Typed model declarations — test contract (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../streamlined/models/README.md`](../streamlined/models/README.md), with the
declarations in [`../streamlined/models/`](../streamlined/models/).

## Tests

`test_models_every_reference_resolves` — parse every fenced `go` and `python`
block in `../streamlined/models/` into a typed model index: typed model name, field names,
and the owning pipeline stage. Parse every `READ:` and `WRITE:` block in
`../streamlined/`. For each `Model → field, field` bullet, the typed model is in the
index and every field is declared on that typed model or on a nested typed model it names.
An undeclared typed model or field fails and names the streamlined doc and the bullet.

`test_models_stage_reads_are_allowed` — for every streamlined pipeline stage doc, every
typed model in its `READ:` block appears in that pipeline stage's allowed-read row in
`../streamlined/models/README.md`. A nested typed model reachable through a declared
field, or a variant alias of a declared aggregate, counts as named by the row. A read
outside the row fails and names the owning pipeline stage and the typed model.

`test_models_stage_writes_are_allowed` — the same rule for `WRITE:` blocks and the
allowed-writes column. A write outside the row fails and names the owning pipeline stage and
the typed model.

`test_models_have_one_home` — a typed model name is declared in exactly one
declaration file per language. A Go and a Python declaration of the same wire
shape are one contract with two language forms; the test also checks that their
field names agree. A duplicate in one language fails, because two homes make a
field change ambiguous.

`test_models_parquet_is_typed` — every `// Parquet` typed model has a struct or list
field for a nested record, never a JSON string. A `STRING` field whose name ends
in `_json` fails unless it is the documented `structured` answer payload.

**TDD pin:** pins the typed model index, the field resolution, the boundary audit, the
one-home rule, and the typed-Parquet rule before the parser exists.

## Current state

`draft`. The declarations are hand-checked; the parser is not written. The
findings from the hand-check are in
[`../streamlined/models/README.md#audit-result`](../streamlined/models/README.md#audit-result).

## What this does not prove

- That a declared field is used correctly at runtime. That is that pipeline stage's
  integration test.
- That the Parquet bytes match the declaration. That is the schema test in
  [`../extraction/README.md`](../extraction/README.md).
