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

## Sub-step contracts

| Sub-step | Input model | Output model | Persisted artifact |
|---|---|---|---|
| `01a` | CADEvolve Parquet cache | `ProgramMetadata` | Program metadata Parquet. |
| `01b` | `ProgramMetadata`, `SelectionPolicy` | `ProgramSelection` | Program selection Parquet. |
| `01c` | `ProgramSelection`, pinned cache revision | `ProgramPool` | Program pool Parquet. |
| `01d` | `ProgramPool` | `NormalizedProgram` | Normalized program Parquet. |
| `01e` | `NormalizedProgram`, `ProgramSelection` | `ExternalDatasetManifest` | `manifest.json`. |

The sub-step docs own the fields and algorithms. This table owns which model and
artifact crosses each sub-step boundary.

## Language and parallelism

- **Go:** `01a`, `01b`, `01c`, `01e`.
- **Python:** `01d` only, because normalization needs the Python tokenizer and AST.
- `01a` metadata reading is parallel over row groups or shards, up to `--jobs`.
- `01c` fetching is parallel over selected IDs or range reads, up to `--jobs`.
- `01d` normalization is parallel per shard, one program at a time through a
  Python worker pool, up to `--jobs`.
- `01b` selection and `01e` manifest writing are global reductions with a single
  writer; they are not parallel.
- Parallel outputs are merged by stable program ID.

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
original pose/scale; C is canonical, centered, and scaled. The selection policy is C only for P0 and P1, and C plus P for P2. C is scaled to a fixed
bounding-box extent; P preserves the original scale. P and C versions of one
generator or mesh family share a program family ID; split assignment never
crosses groups.

## Cache scope

The cache is a clean Parquet copy of the P and C program rows. It is not the
full paper corpus: it does not contain G or the 744,780 code-rewrite
augmentation, and its C count is lower than the paper's 1,002,002
post-canonicalization count. It is a valid program pool for CAD-QA; it is not a
claim of reproducing CADEvolve end to end.

## Fetch and processing budget

Fetching the 508 MB cache, or a larger C shortlist, is cheap. The expensive work
is normalization, execution, graph build, and task generation. Fetch a generous
safety pool; normalize and execute only the active pool. Do not materialize
derived artifacts for unselected programs.

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

## Local decisions

### ETL-1 — Start from the prepared CADEvolve Parquet cache

- **Status:** accepted (2026-10-21).
- **Context:** The raw CADEvolve release is a 4.7 GB tar archive. A prepared
  Parquet cache is published at `MRiabov/cadevolve-parquet`, contains the same
  program records in typed columns, and is about 508 MB. Archive extraction and
  row parsing are avoidable work.
- **Decision:** `01a` reads metadata from `cadevolve_sources.parquet` from
  `MRiabov/cadevolve-parquet`; `01b` selects the program pool; `01c` fetches only
  the selected rows; `01d` applies our own normalization version and program
  hash. The cache commit and conversion version are recorded in the external
  dataset manifest. The tar archive and JSONL are not primary inputs; they are
  provenance checks only.
- **Consequences:** No archive extraction in the normal path. The cache schema
  is part of the external input contract. A cache change is a new external
  dataset version, not an in-place update. Program identity remains ours.

### ETL-2 — CADEvolve P and C are separate program populations

- **Status:** accepted (2026-10-21).
- **Context:** CADEvolve-3L is a three-tier corpus. G contains parametric
  generators, P contains executable programs with arbitrary code style, and C
  contains canonicalized, centered, scaled, and binarized programs used for
  training. P and C have no program-hash overlap.
- **Decision:** The dataset treats P and C as separate program populations.
  P0 and P1 use C only; P2 adds P. `01b` never deduplicates P against C or
  assumes one is a duplicate. G is not ingested. The program pool records the
  tier mix.
- **Consequences:** Prompt style and geometry scale depend on the tier. C is
  canonical and normalized; P preserves arbitrary style and original pose/scale.
  Counts from P and C are not additive as if they were the same programs.

### ETL-3 — Split by CADEvolve program family

- **Status:** accepted (2026-10-21).
- **Context:** Splitting by CadQuery program is not enough. Different programs
  sampled from one CADEvolve generator share a code template and parameter
  family; P and C versions of one mesh or generator are also related. A
  program-level split can put near-duplicates in both training and evaluation.
- **Decision:** Split by `cadevolve_program_family_id`. For CADEvolve core, the
  family is the generator family taken from the path. For CADEvolve-predicted
  ABC/ShapeNet, the family is the mesh family. P and C versions of one family
  share an ID. Assign train, validation, and test at the family level; every
  task inherits the family split. The release table records
  `cadevolve_program_family_id`.
- **Consequences:** Split isolation is stricter than program isolation. Split
  sizes are balanced by family size, not program count. Unmatched P/C families
  become their own families. The cache's `generator_id` column is not the
  generator identity; derive the family from the CADEvolve `path_family` cache
  column.

### ETL-4 — P2 adds P for scale variation

- **Status:** accepted (2026-10-21).
- **Context:** C canonicalization scales the longest bounding-box side to 200
  units, so C programs do not vary in absolute scale. P preserves the original
  pose and scale and uses arbitrary code style.
- **Decision:** P0 and P1 use C only. P2 adds P. P and C versions of one
  generator or mesh family share a program family ID, so P2 cannot split
  them across train and test.
- **Consequences:** P0/P1 keep canonical prompts and simpler normalization. P2
  gains absolute scale variation and arbitrary code style. The CADEvolve program
  family mapping must cover both tiers before P2 is built.

## Not here

This pipeline stage does not build graphs, enumerate tasks, or write dataset release rows.
