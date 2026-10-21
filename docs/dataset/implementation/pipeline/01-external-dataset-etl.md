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

## Dataset semantics

CADEvolve-3L has three tiers:

- **CADEvolve-G** — 7,945 parametric generators. The cache does not contain this
  tier; it is not ingested.
- **CADEvolve-P** — executable programs sampled from the generators, with
  arbitrary code style and paired geometry.
- **CADEvolve-C** — the canonicalized, normalized, binarized versions used for
  training. Canonicalization unifies the flat program template and temporaries,
  centers the shape at its bounding-box center, scales the longest bounding-box
  side to 200 units, and binarizes numeric literals.

The Parquet cache contains 1,998,810 programs:

| Tier | Collections | Programs |
|---|---|---|
| P | ABC-P 875,592; ShapeNet-P 119,437; CADEvolve-P-core 74,623 | 1,069,652 |
| C | ABC-C 763,062; ShapeNet-C 105,200; CADEvolve-C-core 60,896 | 929,158 |

P and C are separate program populations: they have no program-hash overlap.
They are not duplicates of each other. P preserves arbitrary code style and
original pose/scale; C is canonical, centered, and scaled. The selection policy
must choose P, C, or an explicit mix, and must not treat the tiers as
interchangeable. P and C versions of one generator or mesh family share a split
group; split assignment never crosses groups.

## Input scale

The Parquet cache contains 1,998,810 programs. A release does not need all of
them. The 2026-10-19 regeneration used 1,300 programs; smaller runs used a
smaller subset. Normalizing the full cache is not a release requirement. `01b`
selects the pool; `01d` normalizes only that pool.

## Why normalization is a step

The P tier carries arbitrary code style; the C tier carries upstream
canonicalization. Neither is our contract. Program identity, overlap checks, and
reproducibility depend on our own canonical text and normalization version. The
step may be close to a no-op for C records; it is still a real contract boundary.

## Not here

This pipeline stage does not build graphs, enumerate tasks, or write release rows.
