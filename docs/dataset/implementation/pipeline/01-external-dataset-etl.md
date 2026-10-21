# Pipeline stage 01 — External dataset ETL

**Purpose:** turn the CADEvolve export into normalized program records and a
manifest that later pipeline stages can consume.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Sub-steps

| Step | Responsibility | Doc |
|---|---|---|
| `01a` | Extract CadQuery programs from the export. | [`01a-extract-cadevolve-export.md`](01a-extract-cadevolve-export.md) |
| `01b` | Normalize program text, assign stable IDs and hashes. | [`01b-normalize-programs.md`](01b-normalize-programs.md) |
| `01c` | Write counts, provenance, hashes, and rejects. | [`01c-write-external-dataset-manifest.md`](01c-write-external-dataset-manifest.md) |

## Why normalization is a step

CADEvolve may already provide normalized code, but that is an upstream fact we
do not control. Program identity, overlap checks, and reproducibility depend on
our own canonical text and normalization version. The step may be close to a
no-op for most records; it is still a real contract boundary.

## Not here

This pipeline stage does not build graphs, enumerate tasks, or write release rows.
