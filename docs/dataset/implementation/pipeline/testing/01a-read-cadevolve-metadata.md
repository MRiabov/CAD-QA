# 01a read CADEvolve metadata — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../01a-read-cadevolve-metadata.md`](../01a-read-cadevolve-metadata.md),
with the artifact identity in [`../../artifacts.md`](../../artifacts.md).

## Happy-path integration test (test-first, adversarial)

`test_01a_metadata_happy_path_adversarial` — reads a small CADEvolve cache
fixture and asserts the persisted program metadata read back through the reader
`01b` select program pool uses.

**Given** a cache fixture whose rows are:

- one row from each of `ABC-C`, `ShapeNet-C`, `CADEvolve-C-core`, and `ABC-P`,
  each carrying all eight metadata columns;
- a row whose `path_family` is empty;
- a row whose `source_subtree` is a value the tier derivation rejects;
- a row whose `normalized_code` does not import CadQuery.

**When** `01a` reads the fixture with the pinned `cache_revision`.

**Then** assert the persisted program metadata:

- one row per cache row, and `source_id`, `normalized_archive_member_path`,
  `source_subtree`, `source_collection`, `path_family`, `source_feature_tags`,
  `generator_id`, and `normalized_source_code_hash` equal the cache values, keyed
  by `source_id`;
- no `normalized_code` column and no other program text column;
- no `program_id`, `program_sha256`, `raw_program_sha256`, or
  `normalization_version` column: program identity arrives at `01d` normalize
  programs;
- the recorded `cache_revision` and `cache_schema_version` are the fixture's;
- a second read of the same revision is byte-identical.

Keying the comparison by `source_id` rather than by position is deliberate: the
row order after a parallel read is the reader's, and the test must not fix it.

`test_01a_no_local_filter` — the empty `path_family` row, the unknown
`source_subtree` row, and the non-CadQuery row all appear. Rejecting the unknown
subtree is `01b`'s decision and is recorded there; a metadata read that drops it
hides the rejection.

`test_01a_projection_never_reads_program_text` — the same rows written to a cache
file with no `normalized_code` column read to the same metadata. A reader that
requests the column fails on this fixture, so the test proves the projection.

`test_01a_row_group_merge` — the fixture written as one file, as two row groups,
and as two files all read to the same rows in the same order. Two files also
prove that a file boundary is not a row boundary: no row is split or repeated.

**TDD pin:** pins the eight preserved columns, the absence of program text and of
the `01d` identity fields, the pass-through of rows `01b` will reject, and the
one-file / two-row-group / two-file equivalence before `01a` exists.

## Failure-mode tests

- `test_01a_missing_required_column` — a cache missing `path_family` fails with a
  cache-schema failure naming the column, and writes no artifact.
- `test_01a_duplicate_source_id` — two rows share a `source_id`; the read fails
  and names the ID, because `source_id` keys both the parallel merge and the
  `01b` selection. No artifact is written.
- `test_01a_no_partial_artifact` — a truncated second file leaves no metadata
  artifact at all; the rows of the first file are not left behind as a shorter
  table.

## What this does not prove

- That the program text belongs to the metadata row. That is
  `01c-fetch-program-pool.md`.
- That the pool is selected or the tier is derived. That is
  `01b-select-program-pool.md`.
- That the artifact is identified for the release. That is
  `01e-write-external-dataset-manifest.md`.
