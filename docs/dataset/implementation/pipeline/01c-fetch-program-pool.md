# 01c — Fetch program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** fetch the selected program rows from the external dataset cache.

## Input / output

- Input: the selection artifact from `01b` plus the pinned cache revision.
- Output: a Parquet program pool containing only the selected program rows.

## Behavior

- Read only the selected rows and the columns needed for normalization.
- Use Parquet column projection and HF range reads; do not download the full
  cache.
- Preserve the metadata columns selected by `01a`, including the tier and collection.
- Record selected IDs that are missing from the cache.
- Do not normalize or execute CadQuery.

## Open questions

- Does the cache row-group layout make selected-row fetches cheap enough, or is
  a sorted/indexed pool artifact needed?
- What is the rejection policy for a selected ID missing from the pinned cache?
