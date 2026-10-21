# 01a — Read CADEvolve metadata

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** read the metadata columns of the prepared CADEvolve Parquet cache,
without downloading program text or executing anything.

## Input / output

- Input: the `cadevolve_sources.parquet` file from
  [`MRiabov/cadevolve-parquet`](https://huggingface.co/datasets/MRiabov/cadevolve-parquet).
- Output: program metadata records with path, collection, path family, geometry
  tags, generator, and upstream hash.

The cache is already cleaned: all 1,998,810 rows are `.py` records, all import
CadQuery, and all have non-empty program text. There is no non-program-record
filter to apply, and no program-size cutoff: the corpus executed without
significant trouble during the last dataset regeneration.

## Behavior

- Read metadata columns with column projection and streaming/range reads.
- Do not download `normalized_code`; `01c` fetches it only for selected rows.
- Preserve `source_id`, `normalized_archive_member_path`, `source_subtree`,
  `source_collection`, `path_family`, `source_feature_tags`, `generator_id`, and
  `normalized_source_code_hash`.
- The `path_family` column is a CADEvolve path label, not a CAD-QA domain term.
  `01b` derives `cadevolve_split_group_id` from it.
- Read every metadata row; do not apply a local "looks like CadQuery" heuristic.
- Do not normalize or execute CadQuery.
