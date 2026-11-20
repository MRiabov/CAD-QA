# Pipeline stage 05 — Validate and export release

**Purpose:** validate the release and write the consumer artifacts.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

Consumer contract:
[`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).
Artifact ownership: [`../artifacts.md`](../artifacts.md).

## Scope

- Validate the release table schema and row counts.
- Check that the prompt is answer-free.
- Check `task_id` uniqueness and exactly one answer set per row.
- Recheck split isolation by CADEvolve program family on the final release
  table. `03a` assigns the split; `03b` stamps it; `04` carries it.
- Check released values against the task reasoning step support tables.
- Check the transfer overlap: exact normalized program text at P0; the P1
  same-CAD-model check is PRD Q7.
- Record the external benchmark identity and revision in `manifest.json`. No
  program from that benchmark appears in training or evaluation (R-16).
- Write the visual review pack and hold the review gate before export. The owner
  reviews a sample covering every clue type, answer meaning, and answer format
  (R-17); a failed review blocks the export and records the reason.
- Write `release.parquet`, `failures.parquet`, `manifest.json`, and
  `dataset-card.md`.
- Copy the generated task reasoning step support JSON files into `support/` and
  record their hashes in the manifest.
- Record the prompt template version and `prompts.yaml` hash in the manifest.

## Language and parallelism

- **Go:** validation, manifest, and export.
- Independent validation checks are parallel per row, program, or program family.
- The final release write, manifest assembly, and support-table copy are single
  writer steps.
- Parallel validation results are reduced into one summary before export.

## Review gate

`05` writes a visual review pack for a sample of the release. The sample covers
every clue type, every answer meaning, and every answer format.

Each sampled task carries:

- the prompt text;
- one render of the final solid state with the target and every clue-bound
  entity highlighted in a distinct colour and labelled with its clue number;
- the gold answer.

The reviewer checks that each highlighted entity is the one the clue names, that
the answer matches the geometry, and that the wording is clear. The render does
the work that re-deriving the task would otherwise take.

The pack reads the bound entity ids from the release row's evidence, so the
release projection must carry them.

The pack is internal and not a release file. A failed review blocks the export;
the defect is fixed and the task re-reviewed.

## Not here

Task generation, answer resolution, choice generation, and task quota planning.
