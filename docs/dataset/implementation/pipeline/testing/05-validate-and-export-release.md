# 05 validate and export release — adversarial integration test (TDD)

**Parent:** [`../00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../../05-validate-and-export-release.md`](../05-validate-and-export-release.md),
with the checks in
[`../../05-validate-and-export-release/release-checks.md`](../05-validate-and-export-release/release-checks.md),
the columns in
[`../../../../requirements/release-dataset-contract.md`](../../../requirements/release-dataset-contract.md),
and the merge rules in [`../../../failure-record.md`](../../failure-record.md).

This folder mirrors the authoritative `05` folder. The test contract for this pipeline stage is here; the
coverage and balance check tests are in [`release-checks.md`](05-validate-and-export-release/release-checks.md).

## Happy-path integration test (test-first, adversarial)

`test_05_export_happy_path_adversarial` — validates and exports a small release
and asserts the artifacts read back the way a dataset consumer reads them.

**Given** a release table of 12 tasks from 4 programs in 3 families, with 10 in
train, 1 in validation, and 1 in test, and at least one row per answer format. A
`release-checks.yaml` fixture names three checks: one enforced and passing, one reported
and missing, and one not applicable. An external dataset manifest, the five
support tables, a fixed generator version, and the three failure partitions.

**When** `05` validates and exports.

**Then** assert the artifacts:

- `release.parquet` has 12 rows, every column the contract marks required, and
  unique `task_id`;
- `prompt_sha256` matches the test's recomputation from `prompt` for every row,
  and no `prompt` contains its gold answer value;
- `clue_types` equals the clue type sequence of `clue_reduction_form_profile`;
- every multiple-choice row has at least five entries, labels contiguous from
  `A`, answer values distinct under `same_answer`, `gold_answer.label` among the
  labels, and that label's answer value equal to `answer_evidence.answer_equivalent_answer`;
- every other row has an empty `choices` pool;
- each CADEvolve program family appears in exactly one split;
- `failures.parquet` groups by `failure_id`, sums `occurrence_count`, keeps the
  other columns including `disposition` equal, and is sorted by pipeline stage,
  program, task, and reason;
- the counts reconcile at every chain step: the count entering equals the count
  leaving plus the failures recorded there, and the step reports those failures
  by disposition;
- `manifest.json` carries `release_id` as `cadqarel:<sha256>` over the release
  inputs, `release_table_sha256` over the finished file bytes, the declared
  `generator_version`, `upstream_dataset_version` and
  `external_dataset_manifest_sha256` copied verbatim, the balance and check
  policy versions and hashes, the prompt template version and `prompts.yaml`
  hash, the release seed, and the support table versions and hashes;
- the manifest records the benchmark identity, revision, split, and
  program-set hash, and its `release_id` does not change when only the benchmark
  set changes;
- the manifest's `checks` rows are sorted by check name, scope, and value, so a
  different parallel schedule produces the same bytes;
- `support/` holds the five files byte-identical to their inputs;
- every number in `dataset-card.md` equals the manifest's value;
- `manifest.json` is the last file written, so a directory without it is not a
  release.

`test_05_multiple_choice_pool` — five doctored pools each block and name the
check: a repeated answer value under `same_answer`, a gap in the labels, a label
outside `A` to `G`, a gold label absent from the pool, and a correct label whose
value disagrees with the evidence set.

`test_05_answer_hash_is_not_recomputed` — changing a non-answer column leaves
`answer_sha256` unchanged, and changing the answer text changes
`release_table_sha256` while leaving `answer_sha256` unchanged. A second answer
serializer in `05` would break the first assertion.

`test_05_release_id_is_stable` — a re-export over the same inputs keeps
`release_id` and changes only `created_at`; a changed `release-checks.yaml` version
changes the recorded checks policy version and hash but not `release_id`. The
test recomputes the id from the documented inputs.

**TDD pin:** pins the projection rechecks, the choice-pool recheck, split
isolation, the failure merge, the count reconciliation, the manifest fields, the
sorted check rows, and the manifest-last rule before `05` exists.

## Failure-mode tests

- `test_05_missing_column` — a release table without `clue_reduction_form_profile`
  blocks and names the column; no manifest is written.
- `test_05_count_mismatch` — a step with 10 entering, 8 leaving, and 1 failure
  blocks and names the step and the three counts, because a failure row cannot
  report its own absence.
- `test_05_transfer_overlap_p0` — a benchmark program's exact normalized text in
  the release blocks, naming the benchmark program and the release tasks; the
  same family with different text does not block.
- `test_05_benchmark_set_mismatch` — a file whose hash differs from
  `external_benchmark.program_set_sha256`, a schema-version mismatch, a split
  other than the declared one, and a normalization-version mismatch each block
  as an input error before the check runs; no manifest is written.
- `test_05_review_gate` — a review sample missing one answer format blocks, and a
  failed review records its reason and blocks. The pack is not a release file.
- `test_05_no_partial_release` — a block after `release.parquet` is written leaves
  no `manifest.json`, no `dataset-card.md`, and no `support/`, so the directory is
  not a release.

## What this does not prove

- That the prompt renders correctly. That is
  [`../04-render-prompt-and-choices.md`](../04-render-prompt-and-choices.md).
- That the plan is balanced. That is
  [`../03-task-generation/03a-allocate-task-quotas/README.md`](../03-task-generation/03a-allocate-task-quotas/README.md).
- That the release trains well. That is a training experiment.
- That the P1 same-CAD-model audit finds every equivalent program. It reads the
  CAD graph, so it is not part of `05`; `05` proves only the P0 exact-text
  overlap.
