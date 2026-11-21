# 04 render prompt and choices — typed models

> Owning pipeline stage: `04` (Go).
> Contract: [`../../../04-render-prompt-and-choices.md`](../../04-render-prompt-and-choices.md).
> Template schema: [`../../../prompt-templates.md`](../../../prompt-templates.md).
> Release columns: [`../../../../requirements/release-dataset-contract.md`](../../../../requirements/release-dataset-contract.md).

## Input — RenderConfig

`RenderConfig` is a control input, not an artifact. The same value is passed to
`04` and `05`.

```go
type RenderSeed int64

type RenderConfig struct {
	PromptTemplateSet PromptTemplateSet `json:"prompt_template_set"`
	ReleaseSeed       RenderSeed        `json:"release_seed"`
}

type PromptTemplateSet struct {
	Version   string                     `json:"version"`
	FileSHA256 string                    `json:"file_sha256"`
	Namespaces map[string]PromptNamespace `json:"namespaces"`
}

type PromptNamespace struct {
	Labels    map[string]map[string]string `json:"labels"`
	Templates map[string]PromptTemplate    `json:"templates"`
}

type PromptTemplate struct {
	Variants     []string                   `json:"variants"`
	Placeholders map[string]PlaceholderForm `json:"placeholders"`
}

type PlaceholderForm string

const (
	PlaceholderText         PlaceholderForm = "text"
	PlaceholderNumber       PlaceholderForm = "number"
	PlaceholderInteger      PlaceholderForm = "integer"
	PlaceholderBoolean      PlaceholderForm = "boolean"
	PlaceholderCoordinate   PlaceholderForm = "coordinate"
	PlaceholderReference    PlaceholderForm = "reference"
	PlaceholderList         PlaceholderForm = "list"
	PlaceholderNumberedList PlaceholderForm = "numbered_list"
	PlaceholderCode         PlaceholderForm = "code"
	// PlaceholderLabelPrefix is the form "label.<table>", where <table> names
	// a key in PromptNamespace.Labels.
	PlaceholderLabelPrefix = "label."
)
```

`RenderConfig` carries the validated `PromptTemplateSet` and the release seed.
The task render seed is `derive(release_seed, task_id)`; it is part of the `04`
version and is never stored as a release column.

## Output — ReleaseTable

```go
type ReleaseTable struct { // Parquet: release.parquet
	ReleaseID string       `parquet:"release_id"`
	Rows      []ReleaseRow `parquet:"rows"`
}

type ReleaseRow struct {
	TaskID                   string          `parquet:"task_id"`
	Split                    Split           `parquet:"split"`
	Subset                   Subset          `parquet:"subset"`
	Prompt                   string          `parquet:"prompt"`
	PromptSHA256             string          `parquet:"prompt_sha256"`
	ProgramID                string          `parquet:"program_id"`
	ProgramSHA256            string          `parquet:"program_sha256"`
	CadevolveProgramFamilyID string          `parquet:"cadevolve_program_family_id"`
	TaskReasoningStepCount   int             `parquet:"task_reasoning_step_count"`
	TargetCategory           TargetCategory  `parquet:"target_category"`
	ClueTypes                []ClueType      `parquet:"clue_types"`
	ClueOperandFormProfile   []ClueOperandFormEntry `parquet:"clue_operand_form_profile"`
	AnswerFormat             AnswerFormat    `parquet:"answer_format"`
	Choices                  []ReleaseChoice `parquet:"choices"`
	AnswerMeaning            AnswerMeaning   `parquet:"answer_meaning"`
	GeometryRequired         bool            `parquet:"geometry_required"`
	GoldAnswer               AnswerValue     `parquet:"gold_answer"`
	AnswerUnit               *string         `parquet:"answer_unit"`
	Tolerance                *AnswerTolerance `parquet:"tolerance"`
	ScoringRule              ScoringRule     `parquet:"scoring_rule"`
	AnswerSchemaVersion      string          `parquet:"answer_schema_version"`
	AnswerSHA256             string          `parquet:"answer_sha256"`
	AnswerEvidence           ReleaseAnswerEvidence `parquet:"answer_evidence"`
}

type ReleaseChoice struct {
	Label     string `parquet:"label"`
	Candidate string `parquet:"candidate"`
}

type ReleaseAnswerEvidence struct { // the release carries the count, not the full set
	EvidenceKind           EvidenceKind   `parquet:"evidence_kind"`
	EvidenceRule           string         `parquet:"evidence_rule"`
	EvidenceRefs           []EvidenceRef  `parquet:"evidence_refs"`
	AnswerEquivalentCount  int64          `parquet:"answer_equivalent_count"`
	AnswerEquivalentAnswer AnswerValue    `parquet:"answer_equivalent_answer"`
	PointProbe             *AnswerPointProbe `parquet:"point_probe"`
}
```

`AnswerValue`, `AnswerTolerance`, `AnswerEvidence`, `ClueType`,
`ClueOperandFormEntry`, `TargetCategory`, `AnswerFormat`, `AnswerMeaning`, and
`ScoringRule` are declared once in
[`03-task-generation.md`](03-task-generation.md). `04` copies them; it does not
redefine or re-serialize an answer value.

`ReleaseAnswerEvidence` is the release projection of the definition's
`AnswerEvidence`: it carries the answer-equivalent count and shared answer, not
the full set.

`Choices` is empty for every answer format other than multiple choice. The
answer value in `ReleaseChoice.Candidate` is canonical text, because the release
column carries the answer value as text while the prompt carries only the label.
