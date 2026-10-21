# 01a — Extract CADEvolve export

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** read the CADEvolve export and keep CadQuery-looking program
records, without normalizing or executing them.

## Input / output

- Input: CADEvolve export, tar archive, or JSONL.
- Output: raw program records with path, collection metadata, and program text.

## Behavior

- Scan archive members or rows.
- Keep files that look like CadQuery programs.
- Preserve collection/path metadata used for provenance and grouping.
- Record rejected members with a reason.
- Do not assign the final program hash; normalization decides that.

## Open questions

- Which archive/collection filters are required to avoid non-program files?
- What is the maximum program size accepted before rejection?
