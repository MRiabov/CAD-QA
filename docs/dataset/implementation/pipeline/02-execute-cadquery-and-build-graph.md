# Pipeline stage 02 — Execute CadQuery and build graph

**Purpose:** turn a normalized CadQuery program into the CAD graph that task
clues and answers can be checked against.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

**Extraction field contracts:** [`extraction/README.md`](extraction/README.md).

## Sub-steps

| Step | Responsibility | Doc |
|---|---|---|
| `02a` | Extract CadQuery AST structure without execution. | [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) |
| `02b` | Execute CadQuery and capture snapshots or a failure tombstone. | [`02b-execute-cadquery.md`](02b-execute-cadquery.md) |
| `02c` | Build graph entities, relations, measurements, and CAD graph evidence. | [`02c-build-cad-graph.md`](02c-build-cad-graph.md) |

## Sub-step contracts

| Sub-step | Input model | Output model | Persisted artifact |
|---|---|---|---|
| `02a` | `NormalizedProgram` | `CadQueryAstExtractionResult` | `ast_*` tables. |
| `02b` | `NormalizedProgram`, `CadQueryAstExtractionResult` | `CadQueryRuntimeExtractionResult` | `runtime_*` tables or a `FailureTombstone`. |
| `02c` | `CadQueryAstExtractionResult`, `CadQueryRuntimeExtractionResult`, `NormalizedProgram` | `CadGraph` | `nodes.parquet`, `relations.parquet`, `measurements.parquet`. |

The sub-step docs own the fields and algorithms. This table owns which model and
artifact crosses each sub-step boundary.

## Language and parallelism

- **Python:** `02a` AST extraction and `02b` CadQuery execution.
- **Go:** `02c` graph construction.
- Pipeline stage 02 is one fused pipeline: for each program, `02a`, then `02b`, then
  `02c`, before the next program in the shard starts. The three sub-steps are
  not independent parallel steps.
- The pass is the shard ([`run-contract.md`](../run-contract.md#45-concurrency)).
  A pass processes the programs of its shard one at a time in stable
  `program_sha256` order; the number of concurrent shards is a pipeline stage's
  concurrency bound, and `02b` adds the memory cap.
- `02b` forks one child at a time per active shard. The memory bound is per
  active shard, so the number of concurrent children is the number of active
  shards. Do not oversubscribe it.
- Parallel graph outputs are merged by `program_id`; graph construction does not
  mutate shared state.
- The per-sub-step parts and `stage.json` markers remain. A sub-step marker is
  written when every shard has finished that sub-step; a default resume skips
  `02a` for a program whose `02a` is complete.

## Why three steps

AST extraction is cheap and can succeed when execution fails. Execution is
expensive and cacheable. Graph assembly needs both. CAD graph evidence is part of
graph assembly, not a separate pipeline stage: a measurement without CAD graph
evidence is not a graph measurement.

A failure is a CadQuery program runtime extraction result, not a separate
pipeline stage: the execution boundary returns either snapshots or a failure
tombstone, and `02b` also writes one failure record row for the partition.
