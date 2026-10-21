# 01c — Fetch program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** fetch the safety pool from the external dataset cache.

## Input / output

- Input: the selection artifact from `01b`, including supplemental selection
  deltas, plus the pinned cache revision.
- Output: a Parquet program pool with fetched rows marked active or reserve.

## Behavior

- Fetch the active and reserve rows. A supplemental delta is fetched as a delta;
  do not refetch the original pool. A larger C shortlist, or the full C tier, is
  allowed when review needs it.
- Use Parquet column projection and HF range reads. Fetching is cheap relative
  to normalization and execution.
- Do not normalize unselected rows.
- Preserve the metadata columns selected by `01a`, including the tier,
  collection, and `cadevolve_program_family_id`.
- Record selected IDs that are missing from the cache.
- Do not normalize or execute CadQuery.

## Missing IDs

A selected ID that is missing from the pinned cache is a cache revision or
integrity error, not a normal rejection.

- Record the missing ID with the pinned cache revision.
- Backfill the active slot from the reserve list in deterministic order.
- If fewer than 1,000 active programs remain usable, fail the run.
- Do not silently drop the ID or fetch from an unpinned revision.
