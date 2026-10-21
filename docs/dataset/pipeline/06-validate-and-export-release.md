# Pipeline stage 06 — Validate and export release

**Purpose:** validate the selected release and write the consumer artifacts.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

Consumer contract:
[`../requirements/release-dataset-contract.md`](../requirements/release-dataset-contract.md).

## Scope

- Validate the release table schema and row counts.
- Check that the prompt is answer-free.
- Check that task and answer rows are 1:1.
- Check split isolation by program.
- Check the transfer overlap: exact normalized program text at P0; same-CAD-model
  check at P1.
- Write `release.parquet`, `manifest.json`, `dataset-card.md`, and
  `failures.jsonl`.

## Not here

Task generation, answer resolution, choice generation, and release selection.
