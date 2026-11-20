# 01e write external dataset manifest — control metadata

> Authoritative: `../01e-write-external-dataset-manifest.md`

READ:

- `NormalizedProgram` from `01d`
- `ProgramSelection` from `01b` → policy version, seed, active count, reserve count, exclusions
- `01d` failure partition → rejection counts and reasons
- pinned cache → revision, URI, schema version

TRANSFORM:

- selection counts: active, reserve, and one count per exclusion reason
- program counts: one per `tier`, `source_collection`, and `cadevolve_program_family_id`, over normalized rows only
- count normalized programs and distinct `program_id`
- summarize input and output hashes
- sum rejection counts by reason from the `01d` partition
- `status = complete` when every selection target is met and no rejection is recorded, else `incomplete`
- `created_at` is not an input to any hash; two runs over the same inputs differ only in `created_at`
- write no release rows and no release manifest

WRITE:

- `manifest.json` `(external dataset version)` → `manifest_version, created_at, status, cache_revision, cache_uri, cache_schema_version, selection policy version, seed, active count, reserve count, exclusions, counts by tier, counts by collection, counts by family, normalized program count, distinct program count, normalization_version, input and output hash summary, rejection counts and reasons`
