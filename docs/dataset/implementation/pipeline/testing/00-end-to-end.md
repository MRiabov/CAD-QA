# 00 end to end — full-pipeline test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../00-end-to-end.md`](../00-end-to-end.md) and
[`../io-contracts.md`](../io-contracts.md).

## The test

`test_pipeline_end_to_end` — runs every pipeline stage from `01a` read CADEvolve
metadata to `05` validate and export release on the fixture pool, through the
production entry point, and asserts the release artifacts read back through the
reader a dataset consumer uses.

**Given** a fixture pool of CADEvolve programs, their metadata, and typed packets
for the `01c` fetch that replace the network. Nothing else is mocked: CadQuery
and OCP execute, the graph is built, definitions are constructed, prompts are
rendered, and the release is exported.

**When** the chain runs once with a fixed `release_seed` in a temporary runs
root; it allocates `run0001`.

**Then** assert:

- every program in the pool either appears in the release or has one failure row
  naming its pipeline stage and reason, and the counts reconcile at every
  pipeline stage: the count entering one equals the count leaving it plus the
  failures recorded there;
- every release row has a non-empty answer-free `prompt` whose `prompt_sha256`
  recomputes from its bytes, one `answer_sha256`, and one answer set;
- the golden record's definition appears in the release, and its clue sequence,
  answer, and counts match the record;
- each CADEvolve program family sits in exactly one split, and no `task_id`
  appears twice;
- every multiple-choice row carries a `choices` pool whose correct label denotes
  the answer value in its evidence;
- `manifest.json` records the generator version, the scope, the balance and check
  policy versions and hashes, the prompt template version and `prompts.yaml`
  hash, and the release seed;
- `release.parquet`, `failures.parquet`, `manifest.json`, and `dataset-card.md`
  are all written, and no `support/` directory is written;
- `run0001/run.json` exists, its `run_number` is 1, and its `run_id` recomputes
  from the canonical manifest body without the `run_id`, `run_number`, and
  `execution_environment` fields;
- a second run with the same inputs and the same runs root reuses `run0001`,
  writes byte-identical `release.parquet` and the same `release_id`, executes no
  unit, writes no part, and leaves every pipeline stage completion marker
  unchanged.

**TDD pin:** pins the chain's count reconciliation, the golden definition in the
release, split isolation, and the manifest fields before any pipeline stage
exists.

## Failure-mode tests

- `test_pipeline_missing_template` — a `prompts.yaml` without a required template
  stops the run before any release row is written, and names the template.
- `test_pipeline_known_miss` — an enforced check miss blocks the export until it
  is recorded in `known_misses`; with the entry the export proceeds and the
  manifest carries the reason.
- `test_pipeline_no_partial_release` — a failure in `05` leaves no
  `release.parquet` behind, only the failure partition.
- `test_pipeline_resume_after_interrupt` — a `SIGINT` after a fixed number of
  `02b` units leaves committed parts and no `02b` pipeline stage completion
  marker. The next run executes only the remaining programs and completes the
  release. The execution counter proves the completed units were not retried.

## What this does not prove

- That the release meets its targets. That is the check policy, run by `05` and
  reported in the manifest.
- That a task is natural or well worded. That is the review gate.
- That the dataset trains well. That is a training experiment, not a test.
