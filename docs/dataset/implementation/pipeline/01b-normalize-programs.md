# 01b — Normalize programs

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** produce canonical program text, a stable program ID, and the hash
used by graph build, overlap checks, and release grouping.

## Input / output

- Input: extracted program records from the Parquet cache.
- Output: normalized program records with `program_id`, canonical text, and
  normalization version.

## Behavior

- Apply a deterministic, semantics-preserving normalization to the selected
  program pool. Full-cache normalization is not required for a release.
- Record the normalization version.
- Compute the normalized program hash.
- Assign a stable program ID from the normalized identity.
- Record normalization failures with a reason.
- Do not run CadQuery.

## Why it exists

The Parquet cache carries upstream normalization, but it is not our contract.
The step may pass most records through unchanged, but it still stamps the version
and hash that define our program identity.
