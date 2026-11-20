# 01c fetch program pool — safety pool

> Authoritative: `../01c-fetch-program-pool.md`

READ:

- `ProgramSelection` from `01b` → active IDs, reserve IDs, `ProgramSelectionDelta`, `SelectionPolicy`
- pinned cache revision

TRANSFORM:

- fetch active and reserve rows with Parquet column projection and range reads
- fetch a delta as a delta; do not refetch the original pool
- preserve the `01a` metadata columns, including `tier`, `source_collection`, `cadevolve_program_family_id`
- mark each fetched row `active` or `reserve`; a reserve row is fetched but not normalized and not graphed
- mark the row's `delta_id`: null for a row of the original selection, the request ID for a row of a `ProgramSelectionDelta`
- selected ID missing from the pinned cache → record the ID with the revision and backfill the active slot from reserve in deterministic order
- fewer than `policy.usable_floor` (1000) active rows after backfill → fail the run; the post-execution floor is `03a`'s `program_floor_short` deficit
- never drop a missing ID silently and never fetch an unpinned revision

WRITE:

- program pool Parquet `(selection identity, cache revision)` → fetched rows with `active | reserve` and `delta_id`
- missing-ID record with the pinned cache revision
