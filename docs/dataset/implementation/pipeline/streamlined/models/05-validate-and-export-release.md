# 05 validate and export release — typed models

> Owning pipeline stage: `05` (Go).
> Contract: [`../../../05-validate-and-export-release.md`](../../05-validate-and-export-release.md).
> Checks: [`../../../05-validate-and-export-release/release-checks.md`](../../05-validate-and-export-release/release-checks.md).
> Manifest: [`../../../../requirements/release-dataset-contract.md`](../../../../requirements/release-dataset-contract.md).

## ReleaseArtifacts

```go
type ReleaseArtifacts struct { // the release directory, identity release_id
	ReleaseID     string          `json:"release_id"`
	ReleaseTable  ReleaseTable    `json:"-"`
	Failures      []FailureRecord `json:"-"`
	Manifest      ReleaseManifest `json:"-"`
	DatasetCard   string          `json:"-"`
	SupportTables []SupportTable  `json:"-"`
}
```

The release directory is staged under `release/.tmp-<release_id>/` and renamed
to `release/<release_id>/`; `release/current` is replaced by an atomic symlink
rename.

## ReleaseManifest

```go
type ReleaseManifest struct { // JSON: manifest.json
	ReleaseID                         string              `json:"release_id"`
	SchemaVersion                     int                 `json:"schema_version"`
	CreatedAt                         string              `json:"created_at"`
	ImplementationScope               ImplementationScope `json:"implementation_scope"`
	GeneratorVersion                  string              `json:"generator_version"`
	UpstreamDatasetVersion            string              `json:"upstream_dataset_version"`
	ExternalDatasetManifestSHA256     string              `json:"external_dataset_manifest_sha256"`
	ReleaseTableSHA256                string              `json:"release_table_sha256"`
	ExternalBenchmarkID               *string             `json:"external_benchmark_id"`
	ExternalBenchmarkRevision         *string             `json:"external_benchmark_revision"`
	ExternalBenchmarkSplit            *string             `json:"external_benchmark_split"`
	ExternalBenchmarkProgramSetSHA256 *string             `json:"external_benchmark_program_set_sha256"`
	TaskCount                         int                 `json:"task_count"`
	SplitCounts                       map[Split]int       `json:"split_counts"`
	ProgramFamilyCount                int                 `json:"program_family_count"`
	ProgramFamilySplitCounts          map[Split]int       `json:"program_family_split_counts"`
	TaskReasoningStepCounts           map[int]int         `json:"task_reasoning_step_counts"`
	WarmupTaskCount                   int                 `json:"warmup_task_count"`
	DistinctCADModelCount             int                 `json:"distinct_cad_model_count"`
	AnswerSetSHA256                   string              `json:"answer_set_sha256"`
	PromptTemplateVersion             string              `json:"prompt_template_version"`
	PromptsYAMLSHA256                 string              `json:"prompts_yaml_sha256"`
	ReleaseSeed                       RenderSeed          `json:"release_seed"`
	BalancePolicyVersion              int                 `json:"balance_policy_version"`
	BalancePolicySHA256               string              `json:"balance_policy_sha256"`
	ChecksPolicyVersion               int                 `json:"checks_policy_version"`
	ChecksPolicySHA256                string              `json:"checks_policy_sha256"`
	SupportTableVersions              map[string]string   `json:"support_table_versions"`
	SupportTableSHA256                map[string]string   `json:"support_table_sha256"`
	Checks                            []CheckReportRow    `json:"checks"`
	KnownMisses                       []KnownMiss         `json:"known_misses"`
	ReviewLedgerSHA256                string              `json:"review_ledger_sha256"`
	FailureCount                      int                 `json:"failure_count"`
}
```

`release_id` is `cadqarel:<sha256>` over the canonical JSON of
`generator_version`, `implementation_scope`,
`external_dataset_manifest_sha256`, `balance_policy_sha256`,
`prompt_template_version`, `prompts_yaml_sha256`, and `release_seed`.
`created_at` is not an input. The review gate records `review_ledger_sha256`
and excludes it from the identity. The external benchmark fields are validation
provenance and are excluded for the same reason.

## ExternalBenchmarkProgramSet (Parquet)

The release author supplies this file; no pipeline stage writes it. One row per
program in the declared benchmark split. The field names are the Parquet column
names.

```go
type ExternalBenchmarkProgramSet struct {
	BenchmarkProgramID    string  `json:"benchmark_program_id"`
	Split                 string  `json:"split"`
	NormalizationVersion  string  `json:"normalization_version"`
	NormalizedProgramText string  `json:"normalized_program_text"`
	ProgramSHA256         string  `json:"program_sha256"`
	ASTNormalizedSHA256   *string `json:"ast_normalized_sha256"` // P1; null at P0
	FinalShapeHash        *string `json:"final_shape_hash"`      // P1; null at P0
}
```

`program_sha256` and `normalized_program_text` use the `01d` definition, so an
equal text with a different hash is a corrupt set. `ast_normalized_sha256` and
`final_shape_hash` are the P1 same-CAD-model evidence (PRD Q7 Option B): the
hash after AST variable-name and formatting normalization, and the final state's
canonical shape hash from `02b`. The P1 audit requires them; at P0 they are null
and `05` compares `program_sha256` only. The file schema version is in the
Parquet metadata and is compared with
`component_versions.external_benchmark_program_set_schema`; the file hash is in
the run manifest. Neither is a column.

## CheckReport

```go
type CheckReport struct {
	Rows []CheckReportRow `json:"rows"`
}

type CheckReportRow struct {
	CheckID      string        `json:"check_id"`
	Arithmetic   string        `json:"arithmetic"` // coverage | count_floor | share_range | relative_range | share_target | set_equal
	Scope        string        `json:"scope"`      // a step count or "release"
	Dimension    string        `json:"dimension"`
	Value        string        `json:"value"`
	Observed     string        `json:"observed"`
	MinimumCount *int          `json:"minimum_count"`
	MaximumCount *int          `json:"maximum_count"`
	Outcome      string        `json:"outcome"`     // pass | miss | superseded | not_applicable | deferred
	Disposition  string        `json:"disposition"` // enforced | reported | deferred
	Detail       string        `json:"detail"`
}

type KnownMiss struct {
	CheckID string `json:"check_id"`
	Scope   string `json:"scope"`
	Value   string `json:"value"`
	Reason  string `json:"reason"`
	Owner   string `json:"owner"`
}
```

A report row whose check is not listed in `checks.yaml` is a defect. The rows
are sorted by check name, scope, and value before the manifest is written.

## SupportTable

```go
type SupportTable struct { // JSON: support/<dimension>-by-step.json
	Name          string                    `json:"name"`
	SchemaVersion string                    `json:"schema_version"`
	SHA256        string                    `json:"sha256"`
	Rows          map[int][]SupportedValue  `json:"rows"` // task reasoning step count → values
}

type SupportedValue struct {
	Dimension string `json:"dimension"`
	Value     string `json:"value"`
}
```

The five tables are `target-category-by-step.json`, `clue-type-by-step.json`,
`clue-reduction-form-by-step.json`, `answer-meaning-by-step.json`, and
`answer-format-by-step.json`. They are derived by the support-table derivation
and are not generator inputs.
