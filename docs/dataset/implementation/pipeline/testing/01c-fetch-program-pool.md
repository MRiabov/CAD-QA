# 01c fetch program pool — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../01c-fetch-program-pool.md`](../01c-fetch-program-pool.md).

## Happy-path integration test (test-first, adversarial)

`test_01c_fetch_happy_path_adversarial` — fetches a selection from a cache
fixture and asserts the persisted program pool read back through the reader `01d`
normalize programs uses.

**Given** a `ProgramSelection` with 6 active and 2 reserve IDs, a usable floor of
5 active programs in its policy, and a cache fixture that holds every selected
row except one active ID, `a3`. A second cache file at a different revision holds
`a3`.

**When** `01c` fetches at the pinned revision.

**Then** assert the persisted pool:

- one row per fetched ID, each marked `active` or `reserve`;
- `a3`'s active seat is backfilled by the first reserve ID in deterministic
  order, so active still holds 6 and reserve holds 1;
- the missing `a3` is recorded with the pinned cache revision, and no row for it
  is written;
- the text of every fetched row equals the cache text byte for byte: the fixture
  carries comments, CRLF line endings, and a mixed quote style, and none of them
  change;
- no `program_id`, `program_sha256`, `raw_program_sha256`, or
  `normalization_version` column: identity and canonical text arrive at `01d`;
- the preserved metadata columns match `01a`'s values, including `tier`,
  `source_collection`, and `cadevolve_program_family_id`;
- the pool holds 8 rows against a cache of 20, so unselected rows are not
  fetched;
- the artifact's recorded identity is the selection identity plus the pinned
  revision.

`test_01c_projection` — the pool's column set is exactly the preserved metadata
plus `normalized_code` and the active or reserve role. A cache column outside
that set does not reach the pool, and the test asserts the column set rather than
the presence of individual columns.

`test_01c_delta_fetch` — a supplemental delta is fetched on its own. The fixture
for the delta read holds only the added IDs, so a fetch that re-reads the original
selection fails on a missing row. The pool afterwards holds the original rows plus
the delta rows, and the delta rows are marked as such.

`test_01c_reserve_rows_are_fetched_but_not_normalized` — reserve rows appear with
their original text and role `reserve`, and nothing about them is canonicalized.
Promoting one is `03a`'s decision and is recorded in the plan.

**TDD pin:** pins the backfill order, the byte-for-byte text, the column set, the
delta as a separate read, and the missing-ID record before `01c` exists.

## Failure-mode tests

- `test_01c_unpinned_revision_is_refused` — a fetch that would resolve `a3` from
  the other revision is refused, and the refusal names both revisions. Backfill
  is the only recovery.
- `test_01c_below_floor_fails` — usable active programs below the floor fail the
  run, and no pool artifact is left behind. The floor comes from the selection's
  policy, not from a constant in the fetch code.
- `test_01c_missing_id_is_not_a_failure_record` — a missing cache row produces
  the manifest entry and the backfill, and no failure record row, because it is
  an integrity error rather than a rejected program.
- `test_01c_no_partial_pool` — a fetch that fails on the second of three cache
  files leaves no pool artifact, not a shorter one.

## What this does not prove

- That the text normalizes. That is `01d-normalize-programs.md`.
- That the pool fills the task quota plan. That is
  `03c-resolve-deficits.md`.
- That the selection is right. That is
  [`01b-select-program-pool.md`](01b-select-program-pool.md).
