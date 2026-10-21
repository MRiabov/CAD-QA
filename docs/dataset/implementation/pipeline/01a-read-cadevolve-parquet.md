# 01a — Read CADEvolve Parquet cache

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** read the prepared CADEvolve Parquet cache and expose its program
records, without executing them.

## Input / output

- Input: the `cadevolve_sources.parquet` file from
  [`MRiabov/cadevolve-parquet`](https://huggingface.co/datasets/MRiabov/cadevolve-parquet).
- Output: program records with path, collection metadata, and program text.

The cache is already cleaned: all 1,998,810 rows are `.py` records, all import
CadQuery, and all have non-empty program text. There is no non-program-record
filter to apply.

## Behavior

- Read rows from the Parquet cache.
- Use `normalized_code` as the program text.
- Preserve `source_id`, `normalized_archive_member_path`, `source_subtree`,
  `source_collection`, `path_family`, `source_feature_tags`, `generator_id`, and
  `normalized_source_code_hash`.
- Read every row; do not apply a local "looks like CadQuery" heuristic.
- Record malformed rows with a reason.
- Do not assign the final program hash; `01b` decides that.

## Open questions

- What is the maximum accepted program length or operation count before the
  execution budget rejects it?
