# 01e write external dataset manifest — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../01e-write-external-dataset-manifest.md`](../01e-write-external-dataset-manifest.md).

## Happy-path integration test (test-first, adversarial)

`test_01e_manifest_happy_path_adversarial` — writes the manifest for the
normalized program fixture and the selection fixture, and asserts every number
against an independent recomputation from the two artifacts.

**Given** the `01b` selection fixture: 10 cache rows, 6 active, 1 reserve, 3
exclusions across `duplicate_hash`, `family_cap`, and `out_of_scope_tier`. The
`01d` fixture for the 6 active rows produces 5 normalized rows with 4 distinct
`program_id`s, one duplicate pair, one `syntax_error` rejection, and a
`CADEvolve-C-core` collection shortfall of 1.

**When** `01e` writes the manifest.

**Then** assert the manifest:

- the selection counts are 6, 1, and one count per exclusion reason, and they
  equal the selection artifact rather than a recount of the normalized rows;
- the program counts are 5 normalized and 4 distinct, and the per-tier,
  per-collection, and per-family counts sum to 5, not to 6: reserve rows are
  counted in the selection, never in the program counts;
- the rejection count is 1 and its reason is `syntax_error`, matching the
  failure record for `01d`;
- `cache_revision`, `cache_uri`, and `cache_schema_version` equal the identity
  `01a` recorded;
- the input hash equals a hash the test recomputes over the selection file, and
  the output hash equals one over the normalized program file;
- `normalization_version` equals the one on the normalized rows;
- `status` is `incomplete`, because one collection fell short and one program was
  rejected.

`test_01e_status_is_complete_when_nothing_is_missing` — the same fixture with the
collection minimum lowered to 1 and the two failing programs replaced by valid
ones yields `status: complete`. The test changes only the inputs, not the code
path, so `status` is proven to be derived.

`test_01e_created_at_is_the_only_variable_field` — two runs over the same inputs
produce manifests that are equal after removing `created_at`, and the two
`created_at` values are the only difference. Every count, hash, and version is
identical.

`test_01e_counts_are_derived` — a hand-edited count in the normalized artifact
does not change the manifest: the test perturbs a row's family and asserts the
manifest follows the rows. A manifest that copies a count from the selection
artifact instead of the normalized rows fails this.

**TDD pin:** pins the split between selection counts and program counts, the
distinct count over `program_id`, the `complete` and `incomplete` statuses, and
the `created_at` exclusion from every hash before `01e` exists.

## Failure-mode tests

- `test_01e_missing_normalized_artifact` — the manifest is not written when the
  normalized artifact is absent, and the failure names it. A manifest that
  describes nothing is worse than no manifest.
- `test_01e_selection_and_program_counts_disagree` — a normalized row whose
  `source_id` is not in the selection fails the write, because the two artifacts
  describe different runs.
- `test_01e_rejection_without_reason` — a failure record with a reason outside
  `01d`'s closed set fails the write and names the reason.

## What this does not prove

- That the release manifest is right. That is
  `05-validate-and-export-release.md`.
- That the normalized text is right. That is
  [`01d-normalize-programs.md`](01d-normalize-programs.md).
- That the selection is right. That is
  [`01b-select-program-pool.md`](01b-select-program-pool.md).
