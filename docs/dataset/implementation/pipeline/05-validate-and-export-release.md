# Pipeline stage 05 — Validate and export release

**Purpose:** validate the release and write the consumer artifacts.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

Consumer contract:
[`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).
Artifact ownership: [`../artifacts.md`](../artifacts.md).
Coverage and balance checks:
[`05-validate-and-export-release/release-checks.md`](05-validate-and-export-release/release-checks.md).

## Inputs

- `ReleaseTable` from `04` render prompt and choices.
- The `RenderConfig` passed to `04` render prompt and choices.
- The five task reasoning step support tables.
- The root `balance.yaml` and the root `checks.yaml`.
- The external dataset manifest from `01e` write external dataset manifest.
- The pinned external benchmark program set, for the transfer overlap check.
- The per-pipeline-stage failure partitions.
- The run manifest, for the generator version, the release seed, the policy
  versions and hashes, and the tolerance policy hash.
- The review ledger from the [review pack](../devtools/review-pack.md).

## Scope

- Validate the release table schema and row counts.
- Check that the prompt is answer-free.
- Check `task_id` uniqueness and exactly one answer set per row.
- Check the release projection: recompute `prompt_sha256` from the `prompt`
  bytes, check `clue_types` against `clue_operand_form_profile`, check
  `gold_answer` against `answer_format`, and require `tolerance` for every
  non-exact answer. For a multiple-choice row, recheck the `choices` pool: at
  least five entries, labels contiguous from `A` with no repeat, answer values
  distinct under `same_answer`, `gold_answer.label` one of the labels, and that
  label's answer value equal to `answer_evidence.answer_equivalent_answer`.
  Every other row has an empty `choices` pool.
  `05` does not recompute `answer_sha256`;
  `release_table_sha256` covers the answer columns.
- Recheck split isolation by CADEvolve program family on the final release
  table. `03a` assigns the split; `03b` stamps it; `04` carries it.
- Run every check listed in the root `checks.yaml`, as the semantics in
  [`05-validate-and-export-release/release-checks.md`](05-validate-and-export-release/release-checks.md)
  define them, and block the export on a miss the owner has not accepted.
- Merge the per-pipeline-stage failure partitions and reconcile the counts
  (R-19).
- Check the transfer overlap: exact normalized program text at P0; the P1
  same-CAD-model check is PRD Q7.
- Record the external benchmark identity and revision in `manifest.json`. No
  program from that benchmark appears in training or evaluation (R-16).
- Hold the review gate before export against the review ledger (R-17): every
  required sampling cell needs a current pass, and a gap or a failed review
  blocks the export.
- Write `release.parquet`, `failures.parquet`, `manifest.json`, and
  `dataset-card.md`.
- Copy the five task reasoning step support JSON files into `support/` and
  record their schema versions and hashes in the manifest.
- Confirm the prompt template file validates against its
  [schema](../prompt-templates.md), then record the prompt template version,
  `prompts.yaml` hash, and `RenderConfig.release_seed` in the manifest. A
  missing, extra, or untyped placeholder blocks the export.
- Record the balance policy version and `balance.yaml` hash in the manifest,
  and the check policy version and `checks.yaml` hash next to them.

## Language and parallelism

- **Go:** validation, manifest, and export.
- Independent validation checks are parallel per row, program, or program family.
- The final release write, manifest assembly, and support-table copy are single
  writer steps.
- Parallel validation results are reduced into one summary before export, sorted
  by check name, scope, and value, so the manifest hash does not depend on the
  parallel schedule.

## Failure record

Each rejecting stage appends to its own failure partition. `05` merges them into
`failures.parquet`: group by `failure_id`, sum `occurrence_count`, require the
other columns to agree, and sort by pipeline stage, program, task, and reason.
The schema
and the merge rules are in [`../failure-record.md`](../failure-record.md).

`05` also reconciles the counts. For each chain step, the count entering the step
must equal the count leaving it plus the failures recorded at that step. A
mismatch blocks the export and names the step and the counts, because a failure
row cannot report its own absence.

## Balance policy

`05` reads the same root `balance.yaml` as `03a` allocate task quotas. It does
not hold balance numbers of its own.

- Validate the file: known keys only, `task_reasoning_step_share` and
  `release.splits` sum to 1 within `1e-9`, every share in `(0, 1]`,
  `release.share_tolerance` in `[0, 1)`, and `min <= max` when both are present.
- Record `version` and the file `sha256` in `manifest.json`.
- Compare the release against the file, with the checks in
  [`05-validate-and-export-release/release-checks.md`](05-validate-and-export-release/release-checks.md).
  `release.share_tolerance` and `release.distinct_answer_min` are read only here.

A release that departs from the requirement defaults is valid as long as it is
checked against the policy it names. The manifest makes the departure visible.

## Review gate

The [review pack](../devtools/review-pack.md) renders a sample and writes the
review ledger. `05` reads the ledger and never renders.

The sample is the cross product of clue type, answer meaning, answer format, and
task reasoning step count, restricted to the cells the support tables support and
the release contains. Steps 6–10 use at least 30 tasks per tier, or every task if
the tier has fewer; that is the same review the dataset PRD section 6.1
release gate requires.

Each sampled task carries:

- the prompt text;
- one render of the final solid state with the target and every clue-bound
  entity highlighted in a distinct colour and labelled with its clue number;
- the gold answer.

The reviewer checks that each highlighted entity is the one the clue names, that
the answer matches the geometry, and that the wording is clear. The render does
the work that re-deriving the task would otherwise take.

`05` blocks the export unless every required cell has a current `pass` whose
`(definition_sha256, prompt_sha256)` matches the release row. A `defect` blocks
until the task is re-reviewed. The ledger is internal and is not a consumer
artifact.

## Manifest and dataset card

The manifest fields are in the
[release contract](../../requirements/release-dataset-contract.md) section 7, and
the card outline is section 8. `05` owns both.

- Compute `release_id` from the release inputs before writing the manifest. It
  is the release identity, so it is computed once and never patched afterwards.
- Record `generator_version` from the generator's declared version constant. It
  is not derived from git, and a dirty working tree does not block the export.
- Compute `release_table_sha256` from the finished `release.parquet` file, and
  record it next to `release_id`. One is the identity, the other is byte
  integrity, and they change for different reasons.
- Record `review_ledger_sha256` from the review ledger. The ledger is excluded
  from the `release_id` inputs: it is review provenance, not a generation input,
  so re-reviewing a release does not change its identity.
- Copy `upstream_dataset_version` and `external_dataset_manifest_sha256` from the
  external dataset manifest. `05` does not reinterpret either value.
- Write the dataset card from the manifest. Every number in the card is copied,
  so a card that disagrees with the manifest is a defect, not a second opinion.
  The answer conventions are stated from the resolver rules in `03b` construct
  task definitions.

The manifest is the marker that the release is complete. `05` writes it last,
after the checks and the review gate pass, so a release directory without a
manifest is not a release. The run-level execution contract — the run manifest,
Parquet parts, pipeline stage completion markers, resume, and atomic directory
replacement — is [`../run-contract.md`](../run-contract.md). `05` writes the
release into `release/.tmp-<release_id>/` and renames it to
`release/<release_id>/`; `release/current` is replaced by an atomic symlink
rename. The orchestrator writes the `05` pipeline stage completion marker after
the release directory is durable. A failed export leaves the previous `current`
and no visible `release.parquet` in a new release directory.

## Not here

Task generation, answer resolution, choice generation, and task quota planning.
