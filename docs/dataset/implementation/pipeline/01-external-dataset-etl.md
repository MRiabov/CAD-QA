# Pipeline stage 01 — External dataset ETL

**Purpose:** turn the CADEvolve Parquet cache into normalized program records and a
manifest that later pipeline stages can consume.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Sub-steps

| Step | Responsibility | Doc |
|---|---|---|
| `01a` | Read external dataset metadata. | [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) |
| `01b` | Select the deterministic program pool. | [`01b-select-program-pool.md`](01b-select-program-pool.md) |
| `01c` | Fetch the selected program rows. | [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) |
| `01d` | Normalize program text, assign stable IDs and hashes. | [`01d-normalize-programs.md`](01d-normalize-programs.md) |
| `01e` | Write counts, provenance, hashes, and rejects. | [`01e-write-external-dataset-manifest.md`](01e-write-external-dataset-manifest.md) |

## Input scale

The Parquet cache contains 1,998,810 programs. A release does not need all of
them. The 2026-10-19 regeneration used 1,300 programs; smaller runs used a
smaller subset. Normalizing the full cache is not a release requirement. `01b`
selects the pool; `01d` normalizes only that pool.

## Why normalization is a step

The prepared Parquet cache already carries normalized code and a hash, but that
is an upstream fact we do not control. Program identity, overlap checks, and
reproducibility depend on our own canonical text and normalization version. The
step may be close to a no-op for most records; it is still a real contract
boundary.

## Not here

This pipeline stage does not build graphs, enumerate tasks, or write release rows.
