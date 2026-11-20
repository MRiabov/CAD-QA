# 01c fetch program pool — safety pool

> Authoritative: `../01c-fetch-program-pool.md`

READ:
- `ProgramSelection` from `01b` → active IDs, reserve IDs, `ProgramSelectionDelta`
- pinned cache revision

TRANSFORM:
- fetch active and reserve rows with Parquet column projection and range reads
- fetch a delta as a delta; do not refetch the original pool
- preserve the `01a` metadata columns, including `tier`, `source_collection`, `cadevolve_program_family_id`
- mark each fetched row `active` or `reserve`; a reserve row is fetched but not normalized and not graphed
- selected ID missing from the pinned cache → record the ID with the revision and backfill the active slot from reserve in deterministic order
- fewer than 1000 active usable programs after backfill → fail the run
- never drop a missing ID silently and never fetch an unpinned revision

WRITE:
- program pool Parquet `(selection identity, cache revision)` → fetched rows with `active | reserve`
- missing-ID record with the pinned cache revision
