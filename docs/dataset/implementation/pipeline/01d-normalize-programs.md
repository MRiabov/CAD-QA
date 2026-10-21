# 01d — Normalize programs

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** produce canonical program text, a stable program ID, and the hash
used by graph build, overlap checks, and release grouping.

## Input / output

- Input: the selected program pool from `01c`.
- Output: normalized program records with `program_id`, canonical text,
  normalization version, and `cadevolve_program_family_id`.

## Behavior

- Apply a deterministic, semantics-preserving normalization to the selected
  program pool. Full-cache normalization is not required for a release.
- Record the normalization version.
- Compute the normalized program hash.
- Assign a stable program ID from the normalized identity.
- Record normalization failures with a reason.
- Do not run CadQuery.

## Why it exists

The C tier carries upstream normalization; P does not. Neither is our contract.
The step may pass most records through unchanged, but it still stamps the version
and hash that define our program identity.
