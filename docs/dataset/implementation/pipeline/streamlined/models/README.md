# Pipeline typed model declarations

> **This folder is the single home for every typed model in the DAG.** The
> authoritative pipeline stage docs define behavior and field meaning;
> [`../../io-contracts.md`](../../io-contracts.md) owns each pipeline stage boundary.
> This folder owns the declaration: the field set, the owning language, the
> producer, and the consumers.

A pipeline stage doc names a typed model and the fields it reads or writes. It never redefines
them. A typed model appears in exactly one declaration file per language, named after its owning pipeline stage.
A Go and a Python declaration of the same wire shape are one contract with
two language forms, and their field names must agree.

## Why the declarations are here

The generator moves typed records between Go and Python without sharing process
memory. The two risks this folder exists to catch are:

- a field a pipeline stage reads but no producer declares, or a field a pipeline stage writes but
  its output typed model does not declare;
- a typed model that a pipeline stage uses outside its declared boundary, for example `04`
  reading `CadGraph`, or `03b` writing a release row.

The declarations are hand-checked against pipeline stage docs today. The shape is
deliberate: every typed model is a fenced `go` or `python` block, so a later check can
parse the fields without re-reading prose.

## Language rule

A typed model is declared in the language that owns its in-memory form:

| Language | pipeline stages | Reason |
|---|---|---|
| Go | `01a`, `01b`, `01c`, `01e`, `02c`, `03`, `04`, `05` | The default; these pipeline stages do not need Python execution semantics. |
| Python | `01d`, `02a`, `02b` | Normalization and CadQuery extraction need the Python AST and kernel. |

A Python-produced typed model that Go consumes is declared in Python; its Parquet
schema is the shared contract, and the Go reader mirrors the declared fields.
A Go-produced typed model is declared in Go even when a Python test reads it.

## Ownership and boundary audit

Each pipeline stage reads only the artifacts its own doc lists. The table is the
cross-boundary audit: a read outside it is a boundary defect, not an optimization.

| Pipeline stage | Allowed reads | Writes | Must not read |
|---|---|---|---|
| `01a` | CADEvolve cache | `ProgramMetadata` | program text, any later artifact |
| `01b` | `ProgramMetadata`, `SelectionPolicy` | `ProgramSelection` | program text, `CadGraph` |
| `01c` | `ProgramSelection` (with `ProgramSelectionDelta`, `SelectionPolicy`), cache revision | `ProgramPool` | `CadGraph`, task artifacts |
| `01d` | active `ProgramPool` rows | `NormalizedProgram` | `CadGraph`, task artifacts |
| `01e` | `NormalizedProgram`, `ProgramSelection`, `01d` failures, cache identity | `ExternalDatasetManifest` | `CadGraph`, release artifacts |
| `02a` | `NormalizedProgram` | `CadQueryAstExtractionResult` | `CadGraph`, task artifacts |
| `02b` | `NormalizedProgram`, `CadQueryAstExtractionResult`, cache | `CadQueryRuntimeExtractionResult` (`CadQueryRuntimeExtractionSuccess` or `FailureTombstone`) | `CadGraph`, task artifacts |
| `02c` | `CadQueryAstExtractionResult`, `CadQueryRuntimeExtractionResult` (or its `FailureTombstone`), `NormalizedProgram` | `CadGraph` | `TaskDefinition`, release artifacts |
| `03a` | `CadGraph`, `ProgramMetadata`, `ProgramSelection` (with `ProgramSelectionRow`, `SelectionPolicy`), the current `TaskQuotaPlan`, policy, `DeficitLedger`, `ProgramReassignmentRequest` | `TaskQuotaPlan`, `DeficitLedger` | `TaskDefinition`, release artifacts |
| `03b` | `CadGraph`, `TaskQuotaPlan` (with `QuotaTarget`, `ProgramCapabilityCensus`), `DeficitLedger` | `TaskDefinition`, `DeficitLedger` | `ReleaseTable`, `RenderConfig` |
| `03c` | `DeficitLedger`, `TaskQuotaPlan`, `ProgramMetadata`, `SelectionPolicy` | `ProgramReassignmentRequest`, `ProgramRequest`, `AcceptedMiss` | `TaskDefinition`, `ReleaseTable` |
| `04` | `TaskDefinition`, `NormalizedProgram`, `RenderConfig` | `ReleaseTable` | `CadGraph`, `TaskQuotaPlan`, failure partitions |
| `05` | `ReleaseTable`, `RenderConfig`, policy files, support tables, `GraphCompletenessReport`, failure partitions, `ExternalDatasetManifest`, `ExternalBenchmarkProgramSet`, run manifest, review ledger | `ReleaseArtifacts` | `CadGraph`, `TaskDefinition`, `TaskQuotaPlan` |

`05` reads `answer_evidence` only through the release row. It does not read the
task definition: the release carries the answer-equivalent count and shared
answer that the check needs.

## Typed model index

| File | Models |
|---|---|
| [`01-external-dataset-etl.md`](01-external-dataset-etl.md) | `ProgramMetadata`, `SelectionPolicy`, `ProgramSelection`, `ProgramSelectionDelta`, `ExclusionRow`, `ProgramPool`, `NormalizedProgram`, `ExternalDatasetManifest`. |
| [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md) | `02a` AST and `02b` runtime typed models, enums, and shared primitives. |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | `02c` `CadGraph`, `GraphCompletenessReport`, graph entity/relation/measurement tables, and attribute enums. |
| [`03-task-generation.md`](03-task-generation.md) | `ProgramCapabilityCensus`, `TaskQuotaPlan`, `DeficitLedger`, `TaskDefinition`, control records, answer typed models (`AnswerValue`, `AnswerTolerance`, `AnswerEvidence`). |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | `RenderConfig`, `PromptTemplateSet`, `ReleaseTable`, `ReleaseRow`. |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | `ReleaseArtifacts`, `ReleaseManifest`, `CheckReport`, `SupportTable`. |
| [`cross-cutting.md`](cross-cutting.md) | `FailureRecord`, `RunManifest`, `StageCompletionMarker`, `TolerancePolicy`, shared enums. |

## Declaration conventions

- Field types are the Go or Python type, not a Parquet physical type. A Parquet
  schema is owned by the extraction schema docs; this folder declares the
  in-memory shape.
- `*T` in Go and `T | None` in Python mean an optional field.
- A tagged union is a struct with a discriminator and one non-null group per
  variant, matching the Parquet tagged-union rule (`DS-ADR-03`).
- A typed model marked `// Parquet` is persisted; a typed model marked `// JSON` is a small
  control document; a typed model with neither is in-memory only.
- UUID fields are `uuid.UUID` in Go and `UUID4`/`UUID5` in Python. Graph-local
  IDs are UUIDv5; a random ID is never used.
- A field name here is the name pipeline stage docs and the release contract use.
  Renaming one is a schema change, not an edit.

## Hand-check

The audit is one pass per pipeline stage, in DAG order:

1. Read that pipeline stage's READ blocks in `../streamlined/`.
2. For each typed model, find its declaration here and confirm every named field.
3. For each WRITE, confirm the typed model declares the field and the field is not
   owned by a later pipeline stage.
4. Confirm the read is in that pipeline stage's allowed-read row above, and the
   write is in its allowed-writes column.

A disagreement is a doc defect in one of the two files; fix the authoritative
doc and this folder together.

## Audit result

The first pass covered every pipeline stage in DAG order. It found and fixed these
boundary defects:

| Finding | Fix |
|---|---|
| `03` module README took `ProgramMetadata` from `01b`. `01b` produces `ProgramSelection`; `01a` produces `ProgramMetadata`. | Split the input line into `ProgramMetadata` from `01a` and `ProgramSelection` from `01b`. |
| The `03a` input table omitted `ProgramSelection`, although `03a` reads tier and family from it. | Added `ProgramSelection` to the `03a` input typed model list. |
| The `03c` input table omitted `SelectionPolicy`, although `03c` reads `usable_floor`. | Added `SelectionPolicy` to the `03c` input typed model list. |
| The release row reused the definition's `AnswerEvidence`, which carries the full answer-equivalent set. The release carries the count and the shared answer. | Added `ReleaseAnswerEvidence` in the `04` typed models and used it on `ReleaseRow`. |
| The answer-scoring tolerance reused the graph measurement `Tolerance`, whose value is a binary float. The answer tolerance is canonical decimal text. | Added `AnswerTolerance` in the `03` typed models and used it on `TaskDefinition` and `ReleaseRow`. |
| `FamilyProfile` carried one probe success rate, but the plan allocates per family and quota target. | Added `QuotaTargetProbeSuccessRates`. |
| `SelectionPolicy` had no version, although `01e` and the manifest record `policy_version`. | Added `Version` to `SelectionPolicy`. |
| `ReleaseManifest` omitted `review_ledger_sha256`, which the `05` contract records and excludes from `release_id`. | Added `ReviewLedgerSHA256`; made the benchmark id and revision nullable for P0. |
| `02c` writes a `GraphCompletenessReport` per program, but no typed model declared it and `05` did not list it as an input. | Declared the report and its row models in the `02c` models; added it to the `05` inputs and to the `graph_completeness` check. |
| The runtime `ResultKind` used invented values; the instrumentation ABI defines `workplane`, `workplane_list`, `shape`, `shape_list`, `list`, `scalar`, `plane`, `vector`, `edge`, `wire`, and `none`. | Corrected `ResultKind` and named the instrumentation record `RecordedAssignment`. |
| `03a` keyed `program_census` by the graph part hash, a shard file hash. The run contract forbids a shard hash as a downstream identity input, because a sibling unit changes it. | Keyed the census by `graph_identity_sha256`. |
| `03a` read `tier` and `cadevolve_program_family_id` from `ProgramMetadata`, but `01a` writes neither. | Attributed them to `ProgramSelection.rows[]`; `ProgramMetadata` supplies the provenance columns. |
| `01d` read `program_id` from `ProgramPool`, but the pool has no program ID. | `01d` derives `program_id` from `program_sha256`; the pool supplies the text and family ID. |
| `03a/d` listed `planned_clue_occurrences` as a `TaskQuotaPlan` field. | The plan field is `clue_occurrences`; `planned_clue_occurrences` is the derivation's local value. |
| The `DeficitLedger` bullets attributed `coverage_infeasible` and `probe_deficit` to the ledger. | Named them as `AllocationDetail` and `DeficitClass` values on a `DeficitEntry`. |
| The graph attribute enums (`FaceSurfaceKind`, `EdgeCurveKind`, `EdgeEnd`, `ProfileKind`, `WorkplaneKind`, `NamedPlane`, `PathKind`, `PathSegmentKind`, `RegionSign`, `SelectorKind`) and `MeasurementValueKind` / `EvidenceRefKind` were `string` fields, so the closed value set lived only in prose. | Declared them as named Go string enums and typed the fields. Declared `TopologyRelationKind` and typed the runtime topology records. |

`Workplane` in the extraction docs is CadQuery's class, not a typed model in this
folder; it is not declared.

No pipeline stage reads a typed model outside its allowed-read row. The two reads that look
cross-boundary are intentional and are named in the row: `03b` reads the
program census from `TaskQuotaPlan`, and `05` reads the answer-equivalent count
from the release row, not from `TaskDefinition`.

The audit is hand-checked. [the declaration test](../../testing/00-declaration-audit.md)
is the test contract that will make it mechanical.
