# 01e — Write external dataset manifest

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** describe the normalized external dataset without producing release
rows.

## Input / output

- Input: normalized program records plus the selection artifact.
- Output: external dataset manifest.

## Manifest fields

`manifest.json` records:

- `manifest_version`, `created_at`, `status`;
- `cache_revision`, `cache_uri`, and `cache_schema_version`;
- selection policy version, seed, active count, reserve count, and exclusions;
- counts by tier, collection, and `cadevolve_program_family_id`;
- normalized program count and distinct program count;
- normalization version;
- input and output hash summary;
- rejection counts and reasons.

The manifest is small control metadata, so it is JSON. It is not the release
manifest defined in `../requirements/release-dataset-contract.md`.
