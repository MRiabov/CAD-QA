# Dataset pipeline — executable end to end

> Authoritative: `../00-end-to-end.md`
> pipeline stage interfaces: `../io-contracts.md`
> Models: `models/README.md`

This is the executable read order for the whole DAG. It mirrors the
authoritative end-to-end document; a pipeline stage's own doc owns its contract.

## Execution order

```text
01a read metadata → 01b select pool → 01c fetch pool → 01d normalize → 01e write manifest

02a extract AST → 02b execute CadQuery → 02c build graph     (per program, from 01d)

03a allocate quotas → 03b construct definitions → 03c resolve deficits
  03c fast loop: 03a → 03b
  03c slow loop: 01b → 01c → 01d → 02a/02b/02c → 03a → 03b

04 render prompt and choices                                   (from 03b + 01d)

05 validate and export release                                 (from 04)
```

## pipeline stage boundaries

| Pipeline stage | Reads | Writes |
|---|---|---|
| `01` | CADEvolve Parquet cache | `NormalizedProgram`, `ExternalDatasetManifest` |
| `02` | `NormalizedProgram` | `CadGraph` |
| `03` | `CadGraph`, `TaskQuotaPlan`, `DeficitLedger` | `TaskDefinition`, `DeficitLedger`, control records |
| `04` | `TaskDefinition`, `NormalizedProgram`, `RenderConfig` | `ReleaseTable` |
| `05` | `ReleaseTable`, `RenderConfig`, policy files, the task reasoning step support table, failure partitions | `ReleaseArtifacts` |

## Rules

- A run is incremental. The run manifest, Parquet parts, flush rule, cache, and resume rule are in `../../run-contract.md`; a sub-step's WRITE block names its durable part, and a rerun reads the committed parts before computing.
- A pipeline stage reads only the artifacts its doc lists. It does not reach into another pipeline stage's private intermediate state.
- A rejection is data: it becomes a failure row or a deficit entry, never an exception across a pipeline stage boundary.
- The same inputs, versions, and `journal_shard_count` produce byte-identical parts and the same `run_id`.
- The task reasoning step support table is derived outside this folder. `03a` derives it, writes it as a run artifact, and records its hash in the plan; `05` reads that table, verifies the hash, and does not copy it into the release.
