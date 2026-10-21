# 01c — Fetch program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** fetch the safety pool from the external dataset cache.

## Input / output

- Input: the selection artifact from `01b` plus the pinned cache revision.
- Output: a Parquet program pool with fetched rows marked active or reserve.

## Behavior

- Fetch the active and reserve rows. A larger C shortlist, or the full C tier,
  is allowed when review needs it.
- Use Parquet column projection and HF range reads. Fetching is cheap relative
  to normalization and execution.
- Do not normalize unselected rows.
- Preserve the metadata columns selected by `01a`, including the tier,
  collection, and `split_group_id`.
- Record selected IDs that are missing from the cache.
- Do not normalize or execute CadQuery.

## Open questions

- What is the rejection policy for a selected ID missing from the pinned cache?
