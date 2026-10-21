# Pipeline stage 05 — Validate and export release

**Purpose:** validate the release and write the consumer artifacts.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

Consumer contract:
[`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).
Artifact ownership: [`../artifacts.md`](../artifacts.md).

## Scope

- Validate the release table schema and row counts.
- Check that the prompt is answer-free.
- Check that task and answer rows are 1:1.
- Check split isolation by CADEvolve program family.
- Check released values against the task reasoning step support tables.
- Check the transfer overlap: exact normalized program text at P0; the P1
  same-CAD-model check is Q1 below.
- Write `release.parquet`, `failures.parquet`, `manifest.json`, and
  `dataset-card.md`.
- Copy the generated task reasoning step support JSON files into `support/` and
  record their hashes in the manifest.

## Language and parallelism

- **Go:** validation, manifest, and export.
- Independent validation checks are parallel per row, program, or program family.
- The final release write, manifest assembly, and support-table copy are single
  writer steps.
- Parallel validation results are reduced into one summary before export.

## Open questions

- **Q1** (P1). How is same-CAD-model transfer overlap checked: AST-normalized
  program hash, CadQuery shape comparison, or both?

## Not here

Task generation, answer resolution, choice generation, and release planning.
