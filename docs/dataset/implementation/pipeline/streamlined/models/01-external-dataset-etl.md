# 01 external dataset ETL — typed models

> Owning pipeline stages: `01a`, `01b`, `01c`, `01d`, `01e`.
> Contracts: [`../../../01-external-dataset-etl.md`](../../01-external-dataset-etl.md).
> Field meaning: the `01a`–`01e` docs.

`01a`, `01b`, `01c`, and `01e` are Go. `01d` is Python, because normalization
needs the Python AST and Ruff.

## Shared enums

```go
type Tier string

const (
	TierC Tier = "C"
	TierP Tier = "P"
)

type SourceCollection string

const (
	CollectionABCC          SourceCollection = "ABC-C"
	CollectionCADEvolveCore SourceCollection = "CADEvolve-C-core"
	CollectionShapeNetC     SourceCollection = "ShapeNet-C"
)

type FeatureTag string

const (
	TagVoidCut             FeatureTag = "void_cut"
	TagKernelFaceSelector  FeatureTag = "kernel_face_selector"
	TagKernelEdgeSelector  FeatureTag = "kernel_edge_selector"
	TagKernelVertexSelector FeatureTag = "kernel_vertex_selector" // diagnostic, no quota
	TagProfilePolyline     FeatureTag = "profile_polyline"
	TagPathCurve           FeatureTag = "path_curve"
)

type ExclusionReason string

const (
	ExclusionDuplicateHash ExclusionReason = "duplicate_hash"
	ExclusionFamilyCap     ExclusionReason = "family_cap"
	ExclusionOutOfScopeTier ExclusionReason = "out_of_scope_tier"
	ExclusionNotSelected   ExclusionReason = "not_selected"
)

type ProgramPoolStatus string

const (
	PoolActive  ProgramPoolStatus = "active"
	PoolReserve ProgramPoolStatus = "reserve"
)

type ManifestStatus string

const (
	ManifestComplete   ManifestStatus = "complete"
	ManifestIncomplete ManifestStatus = "incomplete"
)
```

## 01a — ProgramMetadata (Parquet)

```go
type ProgramMetadata struct {
	SourceID                     string           `parquet:"source_id"`
	NormalizedArchiveMemberPath  string           `parquet:"normalized_archive_member_path"`
	SourceSubtree                string           `parquet:"source_subtree"`
	SourceCollection             SourceCollection `parquet:"source_collection"`
	PathFamily                   string           `parquet:"path_family"`
	SourceFeatureTags            []FeatureTag     `parquet:"source_feature_tags"`
	GeneratorID                  string           `parquet:"generator_id"`
	NormalizedSourceCodeHash     string           `parquet:"normalized_source_code_hash"`
}
```

`01a` writes no `tier` and no `cadevolve_program_family_id`; `01b` derives both.

## 01b — SelectionPolicy, ProgramSelection

```go
type SelectionScope struct {
	Tiers       []Tier             `parquet:"tiers"`
	Collections []SourceCollection `parquet:"collections"`
}

type CountRange struct {
	Min int `parquet:"min"`
	Max int `parquet:"max"`
}

type SelectionPolicy struct { // run manifest + selection artifact
	Version           int            `parquet:"version"`
	Scope             SelectionScope `parquet:"scope"`
	Seed              int64          `parquet:"seed"`
	ActiveCount       int            `parquet:"active_count"`
	ReserveCount      CountRange     `parquet:"reserve_count"`
	FamilyCap         int            `parquet:"family_cap"`
	CollectionMinimum int            `parquet:"collection_minimum"`
	FeatureTagMinimum int            `parquet:"feature_tag_minimum"`
	TagList           []FeatureTag   `parquet:"tag_list"`
	UsableFloor       int            `parquet:"usable_floor"`
}
```

`SelectionPolicy` is carried in the run manifest with `policy_sha256`.

```go
type ProgramSelectionRow struct {
	SourceID                  string           `parquet:"source_id"`
	Tier                      Tier             `parquet:"tier"`
	SourceCollection          SourceCollection `parquet:"source_collection"`
	CadevolveProgramFamilyID  string           `parquet:"cadevolve_program_family_id"`
	Status                    ProgramPoolStatus `parquet:"status"`
	DeltaID                   *string          `parquet:"delta_id"`
}

type ProgramSelectionDelta struct {
	DeltaID       string   `parquet:"delta_id"`
	RequestID     string   `parquet:"request_id"`
	PolicyVersion int      `parquet:"policy_version"`
	AddedIDs      []string `parquet:"added_ids"`
	Reason        string   `parquet:"reason"`
}

type ExclusionRow struct {
	SourceID         string          `parquet:"source_id"`
	SourceCollection SourceCollection `parquet:"source_collection"`
	Reason           ExclusionReason `parquet:"reason"`
}

type ProgramSelection struct { // Parquet
	Policy           SelectionPolicy         `parquet:"policy"`
	Seed             int64                   `parquet:"seed"`
	ActiveIDs        []string                `parquet:"active_ids"`
	ReserveIDs       []string                `parquet:"reserve_ids"`
	Rows             []ProgramSelectionRow   `parquet:"rows"`
	Deltas           []ProgramSelectionDelta `parquet:"deltas"`
	Exclusions       []ExclusionRow          `parquet:"exclusions"`
	CollectionCounts map[SourceCollection]int `parquet:"collection_counts"`
	FamilyCounts     map[string]int          `parquet:"family_counts"`
}
```

`CollectionCounts` and `FamilyCounts` are counts over the selected rows; the
artifact carries them so `01e` does not re-derive them. A `Map` in Parquet is a
typed key-value list, not a JSON string.

## 01c — ProgramPool

```go
type ProgramPoolRow struct {
	ProgramMetadata                            // embedded cache metadata
	ProgramText              string           `parquet:"program_text"` // normalized_code
	Tier                     Tier             `parquet:"tier"`
	CadevolveProgramFamilyID string           `parquet:"cadevolve_program_family_id"`
	Status                   ProgramPoolStatus `parquet:"status"`
	DeltaID                  *string          `parquet:"delta_id"`
}

type MissingProgramID struct {
	SourceID      string `parquet:"source_id"`
	CacheRevision string `parquet:"cache_revision"`
}

type ProgramPool struct { // Parquet
	Rows       []ProgramPoolRow  `parquet:"rows"`
	MissingIDs []MissingProgramID `parquet:"missing_ids"`
}
```

A reserve row is present and marked `reserve`; it has no `NormalizedProgram`
until `03a` promotes it.

## 01d — NormalizedProgram (Python, Parquet)

```python
from pydantic import BaseModel, Field


class NormalizedProgram(BaseModel):
    """One canonical program. Identity is (program_sha256, normalization_version)."""

    program_id: str = Field(pattern=r"^cadqaprog:[0-9a-f]{64}$")
    canonical_text: str = Field(min_length=1)
    normalization_version: str = Field(min_length=1)
    program_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_program_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cadevolve_program_family_id: str = Field(min_length=1)
```

The normalization failure reason set is closed: `invalid_utf8`, `syntax_error`,
`format_failure`. A failure is a `FailureRecord`, not a partial
`NormalizedProgram`.

## 01e — ExternalDatasetManifest (JSON)

```go
type ExternalDatasetManifest struct { // JSON, manifest.json
	ManifestVersion         int                   `json:"manifest_version"`
	CreatedAt               string                `json:"created_at"`
	Status                  ManifestStatus        `json:"status"`
	CacheRevision           string                `json:"cache_revision"`
	CacheURI                string                `json:"cache_uri"`
	CacheSchemaVersion      string                `json:"cache_schema_version"`
	SelectionPolicyVersion  int                   `json:"selection_policy_version"`
	Seed                    int64                 `json:"seed"`
	ActiveCount             int                   `json:"active_count"`
	ReserveCount            int                   `json:"reserve_count"`
	Exclusions              map[ExclusionReason]int `json:"exclusions"`
	CountsByTier            map[Tier]int          `json:"counts_by_tier"`
	CountsByCollection      map[SourceCollection]int `json:"counts_by_collection"`
	CountsByFamily          map[string]int        `json:"counts_by_family"`
	NormalizedProgramCount  int                   `json:"normalized_program_count"`
	DistinctProgramCount    int                   `json:"distinct_program_count"`
	NormalizationVersion    string                `json:"normalization_version"`
	InputHashSummary        string                `json:"input_hash_summary"`
	OutputHashSummary       string                `json:"output_hash_summary"`
	RejectionCounts         map[string]int        `json:"rejection_counts"`
	RejectionReasons        map[string]int        `json:"rejection_reasons"`
}
```

`created_at` is not an input to any hash. `Status` is `complete` only when every
selection target is met and no rejection is recorded.
