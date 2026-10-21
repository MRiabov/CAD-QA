# Pipeline stage 06 — Validate and export release

**Purpose:** validate the selected release and write the consumer artifacts.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

Consumer contract:
[`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).
Artifact ownership: [`../artifacts.md`](../artifacts.md).

## Scope

- Validate the release table schema and row counts.
- Check that the prompt is answer-free.
- Check that task and answer rows are 1:1.
- Check split isolation by CADEvolve program family.
- Check the transfer overlap: exact normalized program text at P0; the P1
  same-CAD-model check is Q1 below.
- Write `release.parquet`, `failures.parquet`, `manifest.json`, and
  `dataset-card.md`.
- Copy the embedded support JSON files into `support/` and record their hashes in
  the manifest.

## Open questions

- **Q1** (P1). How is same-CAD-model transfer overlap checked: AST-normalized
  program hash, CadQuery shape comparison, or both?

## Not here

Task generation, answer resolution, choice generation, and release selection.
