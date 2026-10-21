# 01b — Normalize programs

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** produce canonical program text, a stable program ID, and the hash
used by graph build, overlap checks, and release grouping.

## Input / output

- Input: raw program records.
- Output: normalized program records with `program_id`, canonical text, and
  normalization version.

## Behavior

- Apply a deterministic, semantics-preserving normalization.
- Record the normalization version.
- Compute the normalized program hash.
- Assign a stable program ID from the normalized identity.
- Record normalization failures with a reason.
- Do not run CadQuery.

## Why it exists

Upstream normalization is not guaranteed. The step may pass most CADEvolve
records through unchanged, but it still stamps the version and hash that define
our program identity.
