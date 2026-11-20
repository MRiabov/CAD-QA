# 01a read CADEvolve metadata — metadata projection

> Authoritative: `../01a-read-cadevolve-metadata.md`

READ:
- `cadevolve_sources.parquet` at the pinned cache revision → `source_id, normalized_archive_member_path, source_subtree, source_collection, path_family, source_feature_tags, generator_id, normalized_source_code_hash`
- do not read `normalized_code`

TRANSFORM:
- stream the metadata columns by row group or shard; no program-text download
- read every row; no "looks like CadQuery" filter and no program-size cutoff
- emit one `ProgramMetadata` per cache row; copy every metadata value unchanged
- keep `path_family` and `source_feature_tags` as cache metadata; do not map either to a CAD-QA term here

WRITE:
- program metadata Parquet `(cache revision, metadata schema version)` → `ProgramMetadata`
- no rejection rows; every row in the pinned cache is accepted
