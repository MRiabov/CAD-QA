# 01c — Write external dataset manifest

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** describe the normalized external dataset without producing release
rows.

## Input / output

- Input: normalized program records.
- Output: external dataset manifest.

## Manifest content

- external dataset identity and version;
- program count and distinct program count;
- normalization version;
- hash summary;
- collection and path provenance;
- rejection counts and reasons.

## Open questions

- Which manifest fields are required for reproducible graph rebuilds?
- Should the manifest include a per-collection program count?
