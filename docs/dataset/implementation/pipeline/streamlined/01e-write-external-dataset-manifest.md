# 01e write external dataset manifest — control metadata

> Authoritative: `../01e-write-external-dataset-manifest.md`

READ:
- `NormalizedProgram` from `01d`
- `ProgramSelection` from `01b` → policy version, seed, active count, reserve count, exclusions
- `01d` failure partition → rejection counts and reasons
- pinned cache → revision, URI, schema version

TRANSFORM:
- count programs by `tier`, `source_collection`, and `cadevolve_program_family_id`
- count normalized programs and distinct `program_id`
- summarize input and output hashes
- sum rejection counts by reason from the `01d` partition
- write no release rows and no release manifest

WRITE:
- `manifest.json` `(external dataset version)` → `manifest_version, created_at, status, cache_revision, cache_uri, cache_schema_version, selection policy version, seed, active count, reserve count, exclusions, counts by tier, counts by collection, counts by family, normalized program count, distinct program count, normalization_version, input and output hash summary, rejection counts and reasons`
