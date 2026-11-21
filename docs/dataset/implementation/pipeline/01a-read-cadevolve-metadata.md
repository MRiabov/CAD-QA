# 01a — Read CADEvolve metadata

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** read the metadata columns of the prepared CADEvolve Parquet cache,
without downloading program text or executing anything.

## Input / output

- Input: the `cadevolve_sources.parquet` file from
  [`MRiabov/cadevolve-parquet`](https://huggingface.co/datasets/MRiabov/cadevolve-parquet).
- Output: program metadata records with path, collection, path family, geometry
  tags, generator, and upstream hash, plus the `cache_revision` and
  `cache_schema_version` they were read at.

The run manifest declares the expected external dataset revision. `01a` verifies
the observed `cache_revision` against it; a mismatch stops the run before any
part is written. See
[`../run-contract.md`](../run-contract.md#2-run-identity-and-the-run-manifest).

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
  `01b` derives `cadevolve_program_family_id` from it.
- `source_feature_tags` is cache metadata, not a CADEvolve paper term. Its values
  include `void_cut`, `kernel_face_selector`, `kernel_edge_selector`,
  `profile_polyline`, `path_curve`, and `kernel_vertex_selector`.
- Read every metadata row; do not apply a local "looks like CadQuery" heuristic.
- Do not normalize or execute CadQuery.
