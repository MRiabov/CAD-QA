# 01a — Read CADEvolve Parquet cache

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** read the prepared CADEvolve Parquet cache and keep CadQuery-looking
program records, without executing them.

## Input / output

- Input: the `cadevolve_sources.parquet` file from
  [`MRiabov/cadevolve-parquet`](https://huggingface.co/datasets/MRiabov/cadevolve-parquet).
- Output: extracted program records with path, collection metadata, and program
  text.

## Behavior

- Read rows from the Parquet cache.
- Use `normalized_code` as the program text.
- Preserve `source_id`, `normalized_archive_member_path`, `source_subtree`,
  `source_collection`, `path_family`, `source_feature_tags`, `generator_id`, and
  `normalized_source_code_hash`.
- Keep rows that look like CadQuery programs.
- Record rejected rows with a reason.
- Do not assign the final program hash; `01b` decides that.

## Open questions

- Which collection filters are required to avoid non-program records?
- What is the maximum program size accepted before rejection?
