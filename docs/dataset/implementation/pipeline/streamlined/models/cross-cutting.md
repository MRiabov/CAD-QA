# Cross-cutting typed models

> Owners: the orchestrator (`run-contract.md`) and every rejecting pipeline stage
> (`failure-record.md`).
> Contracts: [`../../../run-contract.md`](../../../run-contract.md),
> [`../../../failure-record.md`](../../../failure-record.md).

## Shared scalars

```go
type Sha256 string // 64 lowercase hexadecimal characters

type ImplementationScope string

const (
	ScopeP0 ImplementationScope = "p0"
	ScopeP1 ImplementationScope = "p1"
	ScopeP2 ImplementationScope = "p2"
)

type PipelineStage string

const (
	Stage01a PipelineStage = "01a_read_cadevolve_metadata"
	Stage01b PipelineStage = "01b_select_program_pool"
	Stage01c PipelineStage = "01c_fetch_program_pool"
	Stage01d PipelineStage = "01d_normalize_programs"
	Stage01e PipelineStage = "01e_write_external_dataset_manifest"
	Stage02a PipelineStage = "02a_extract_cadquery_ast"
	Stage02b PipelineStage = "02b_execute_cadquery"
	Stage02c PipelineStage = "02c_build_cad_graph"
	Stage03b PipelineStage = "03b_construct_task_definitions"
	Stage05  PipelineStage = "05_validate_and_export_release"
)
```

`PipelineStage` is the set of pipeline stages that write a failure partition. `03a` and
`03c` write control records and a plan, not failures; `04` must not reject.

## FailureRecord (Parquet)

```go
type FailureRecord struct {
	FailureID       uuid.UUID   `parquet:"failure_id"`        // UUIDv5 of the dedupe key
	PipelineStage   PipelineStage `parquet:"pipeline_stage"`
	ProgramID       string      `parquet:"program_id"`
	TaskID          *string     `parquet:"task_id"`
	InputSHA256     *Sha256     `parquet:"input_sha256"`
	ReasonCode      string      `parquet:"reason_code"`
	Detail          string      `parquet:"detail"`            // at most 500 characters, deterministic
	SourceLine      *int        `parquet:"source_line"`
	SourceSpan      *SourceSpan `parquet:"source_span"`
	OccurrenceCount int         `parquet:"occurrence_count"`  // at least 1
}
```

The dedupe key is `(pipeline_stage, program_id, task_id, input_sha256,
reason_code)`. `failure_id` is `uuid5(namespace, canonical JSON of the key)`; the
namespace is the UUIDv5 of `https://github.com/MRiabov/CAD-QA/failure-record`
under the URL namespace. A row carries no timestamp, host, attempt index, or
pipeline stage version.

## RunManifest (JSON)

```go
type RunManifest struct { // JSON: run.json
	RunID               string             `json:"run_id"`        // cadqarun:<sha256>
	RunNumber           int               `json:"run_number"`    // local sequence, not in run_id
	SchemaVersion       int               `json:"schema_version"`
	GeneratorVersion    string            `json:"generator_version"`
	ImplementationScope ImplementationScope `json:"implementation_scope"`
	ExternalDataset     ExternalDatasetRef `json:"external_dataset"`
	Selection           SelectionRef       `json:"selection"`
	PlanSeed            int64             `json:"plan_seed"`
	ReleaseSeed         int64             `json:"release_seed"`
	JournalShardCount   int               `json:"journal_shard_count"` // default 16
	ExternalBenchmark   *ExternalBenchmark `json:"external_benchmark"`
	ComponentVersions   ComponentVersions `json:"component_versions"`
	ExecutionEnvironment ExecutionEnvironment `json:"execution_environment"` // audit, not run_id
	TolerancePolicy     TolerancePolicy   `json:"tolerance_policy"`
	TolerancePolicyVersion int            `json:"tolerance_policy_version"`
	TolerancePolicySHA256  Sha256         `json:"tolerance_policy_sha256"`
	PolicyFiles         PolicyFiles       `json:"policy_files"`
}

type ExternalDatasetRef struct {
	URI           string `json:"uri"`
	Revision      string `json:"revision"`
	SchemaVersion string `json:"schema_version"`
}

type SelectionRef struct {
	Policy    SelectionPolicy `json:"policy"`
	PolicySHA256 Sha256       `json:"policy_sha256"`
}

type ExternalBenchmark struct {
	URI              string `json:"uri"`
	ID               string `json:"id"`
	Revision         string `json:"revision"`
	Split            string `json:"split"`
	ProgramSetSHA256 Sha256 `json:"program_set_sha256"`
}

type ComponentVersions struct {
	MetadataReader           string `json:"metadata_reader"`
	Selection                string `json:"selection"`
	Fetcher                  string `json:"fetcher"`
	Normalization            string `json:"normalization"`
	ExternalDatasetManifestSchema string `json:"external_dataset_manifest_schema"`
	ExternalBenchmarkProgramSetSchema string `json:"external_benchmark_program_set_schema"`
	ASTExtractor             string `json:"ast_extractor"`
	RuntimeExtractor         string `json:"runtime_extractor"`
	Canonicalization         string `json:"canonicalization"`
	GraphBuilder             string `json:"graph_builder"`
	Planner                  string `json:"planner"`
	Constructor              string `json:"constructor"`
	DeficitController        string `json:"deficit_controller"`
	Renderer                 string `json:"renderer"`
	Exporter                 string `json:"exporter"`
	GraphSchema              string `json:"graph_schema"`
	TaskDefinitionSchema     string `json:"task_definition_schema"`
	ReleaseSchema            string `json:"release_schema"`
	CadQuery                 string `json:"cadquery"`
	OCP                      string `json:"ocp"`
	Python                   string `json:"python"`
	Go                       string `json:"go"`
}

type PolicyFiles struct {
	Balance   PolicyFileRef `json:"balance"`
	Checks    PolicyFileRef `json:"checks"`
	Prompts   PolicyFileRef `json:"prompts"`
	Tolerance PolicyFileRef `json:"tolerance"`
}

type PolicyFileRef struct {
	Version int    `json:"version"`
	SHA256  Sha256 `json:"sha256"`
}
```

`run_id` is `cadqarun:<sha256>` over the canonical JSON of every field except
`run_id`, `run_number`, and `execution_environment`. A changed declared input,
component version, or policy hash is a new run directory. The execution
environment enters the `02b` unit identity, not `run_id`.

`ExecutionEnvironment` is declared in
[`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).
It names an environment class, not a machine: no hostname, PID, container ID,
kernel version, CPU typed model, or timestamp.

## StageCompletionMarker (JSON: pipeline stage.json)

```go
type StageCompletionMarker struct {
	PipelineStage       PipelineStage `json:"pipeline_stage"`
	StageIdentitySHA256 Sha256        `json:"stage_identity_sha256"`
	PartsSHA256         Sha256        `json:"parts_sha256"`
	PartCount           int           `json:"part_count"`
	RowCount            int64         `json:"row_count"`
	FailurePartsSHA256  *Sha256       `json:"failure_parts_sha256"`
	FailureCount        int           `json:"failure_count"`
	Outputs             map[string]string `json:"outputs"`
	Complete            bool          `json:"complete"` // always true
}
```

## TolerancePolicy

```go
type TolerancePolicy struct {
	Millimetre       Tolerance `json:"millimetre"`
	SquareMillimetre Tolerance `json:"square_millimetre"`
	CubicMillimetre  Tolerance `json:"cubic_millimetre"`
	Degree           Tolerance `json:"degree"`
	Radian           Tolerance `json:"radian"`
	Unitless         Tolerance `json:"unitless"`
}
```

`Tolerance` and `ToleranceKind` are declared in
[`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).
The policy is resolved once per run, stored in the run manifest, and is part of
every graph artifact identity. A measurement `tolerance` of null inherits the
policy entry for its `unit`; a non-null value overrides it.

## Boundary notes

- `FailureRecord` is written by `01d`, `02a`, `02b`, `02c`, `03b`, and `05`.
  `04` does not write one.
- `RunManifest` is written by the orchestrator before the first pipeline stage; no pipeline stage
  edits it.
- `StageCompletionMarker` is written by the orchestrator after each pipeline stage that
  writes an artifact; `03c` has no marker.
- `TolerancePolicy` is read by `02c`; answer-scoring `AnswerTolerance` is a
  different typed model owned by `03b`.
