package shared

import (
	"bytes"
	"cmp"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"unicode/utf8"

	"github.com/google/uuid"
)

// PipelineStage is a pipeline stage name in the snake case used by the failure
// record. Only stages that write failure rows have a constant here.
type PipelineStage string

const (
	PipelineStage01dNormalizePrograms        PipelineStage = "01d_normalize_programs"
	PipelineStage02aExtractCadqueryAst       PipelineStage = "02a_extract_cadquery_ast"
	PipelineStage02bExecuteCadquery          PipelineStage = "02b_execute_cadquery"
	PipelineStage02cBuildCadGraph            PipelineStage = "02c_build_cad_graph"
	PipelineStage03bConstructTaskDefinitions PipelineStage = "03b_construct_task_definitions"
	PipelineStage05ValidateAndExportRelease  PipelineStage = "05_validate_and_export_release"
)

// FailureRecordNamespace is the UUID v5 namespace for failure_id values. It is
// derived from a fixed project URL so both languages compute the same ID
// without sharing a magic constant.
var FailureRecordNamespace = uuid.NewSHA1(
	uuid.NameSpaceURL,
	[]byte("https://github.com/MRiabov/CAD-QA/failure-record"),
)

// ProgramSpan is the optional start and end column of a rejected program input.
type ProgramSpan struct {
	StartColumn int64 `parquet:"start_column"`
	EndColumn   int64 `parquet:"end_column"`
}

// FailureRecord is one row of a pipeline stage failure partition. A rejection
// is data, not an exception: a pipeline stage records the row and continues.
type FailureRecord struct {
	FailureID       uuid.UUID     `parquet:"failure_id"`
	PipelineStage   PipelineStage `parquet:"pipeline_stage"`
	ProgramID       string        `parquet:"program_id"`
	TaskID          *string       `parquet:"task_id,optional"`
	InputSHA256     *string       `parquet:"input_sha256,optional"`
	ReasonCode      string        `parquet:"reason_code"`
	Detail          string        `parquet:"detail"`
	ProgramLine     *int64        `parquet:"program_line,optional"`
	ProgramSpan     *ProgramSpan  `parquet:"program_span,optional"`
	OccurrenceCount int64         `parquet:"occurrence_count"`
}

// FailureDedupeKey is the identity of a rejection. Two rows with the same key
// are the same rejection; their occurrence counts are summed on merge.
type FailureDedupeKey struct {
	PipelineStage PipelineStage
	ProgramID     string
	TaskID        *string
	InputSHA256   *string
	ReasonCode    string
}

// CanonicalJSON returns the dedupe key as canonical JSON: sorted keys, no
// spaces, no HTML escaping, UTF-8. The failure ID is a UUID v5 over these
// bytes.
func (k FailureDedupeKey) CanonicalJSON() ([]byte, error) {
	document := map[string]any{
		"input_sha256":   k.InputSHA256,
		"pipeline_stage": string(k.PipelineStage),
		"program_id":     k.ProgramID,
		"reason_code":    k.ReasonCode,
		"task_id":        k.TaskID,
	}
	return canonicalJSON(document)
}

// FailureID returns the deterministic UUID v5 of the dedupe key.
func (k FailureDedupeKey) FailureID() (uuid.UUID, error) {
	payload, err := k.CanonicalJSON()
	if err != nil {
		return uuid.Nil, err
	}
	return uuid.NewSHA1(FailureRecordNamespace, payload), nil
}

// DedupeKey returns the record's dedupe key.
func (r FailureRecord) DedupeKey() FailureDedupeKey {
	return FailureDedupeKey{
		PipelineStage: r.PipelineStage,
		ProgramID:     r.ProgramID,
		TaskID:        r.TaskID,
		InputSHA256:   r.InputSHA256,
		ReasonCode:    r.ReasonCode,
	}
}

// AssignFailureID sets FailureID from the record's dedupe key.
func (r *FailureRecord) AssignFailureID() error {
	failureID, err := r.DedupeKey().FailureID()
	if err != nil {
		return err
	}
	r.FailureID = failureID
	return nil
}

// Validate reports whether the row satisfies the failure-record contract.
func (r FailureRecord) Validate() error {
	if r.FailureID == uuid.Nil {
		return errors.New("failure record: failure_id is zero")
	}
	if !r.PipelineStage.valid() {
		return fmt.Errorf("failure record: unknown pipeline stage %q", r.PipelineStage)
	}
	if r.ProgramID == "" {
		return errors.New("failure record: program_id is empty")
	}
	if r.ReasonCode == "" {
		return errors.New("failure record: reason_code is empty")
	}
	if r.Detail == "" {
		return errors.New("failure record: detail is empty")
	}
	if utf8.RuneCountInString(r.Detail) > 500 {
		return fmt.Errorf("failure record: detail is %d characters, maximum is 500", utf8.RuneCountInString(r.Detail))
	}
	if r.OccurrenceCount < 1 {
		return fmt.Errorf("failure record: occurrence_count is %d, minimum is 1", r.OccurrenceCount)
	}
	if r.TaskID != nil && *r.TaskID == "" {
		return errors.New("failure record: task_id is set but empty")
	}
	if r.InputSHA256 != nil && *r.InputSHA256 == "" {
		return errors.New("failure record: input_sha256 is set but empty")
	}
	if r.ProgramLine != nil && *r.ProgramLine < 1 {
		return fmt.Errorf("failure record: program_line is %d, minimum is 1", *r.ProgramLine)
	}
	if r.ProgramSpan != nil && r.ProgramSpan.StartColumn > r.ProgramSpan.EndColumn {
		return fmt.Errorf(
			"failure record: source span starts at %d and ends at %d",
			r.ProgramSpan.StartColumn,
			r.ProgramSpan.EndColumn,
		)
	}
	return nil
}

// MergeFailureRecords groups rows by failure_id, sums occurrence_count, and
// requires every other column to agree. The result is sorted by pipeline stage,
// program, task (nulls first), and reason.
func MergeFailureRecords(records []FailureRecord) ([]FailureRecord, error) {
	merged := make(map[uuid.UUID]FailureRecord, len(records))
	for _, record := range records {
		if err := record.Validate(); err != nil {
			return nil, err
		}
		existing, ok := merged[record.FailureID]
		if !ok {
			merged[record.FailureID] = record
			continue
		}
		if !sameFailureColumns(existing, record) {
			return nil, fmt.Errorf("failure %s: columns disagree", record.FailureID)
		}
		existing.OccurrenceCount += record.OccurrenceCount
		merged[record.FailureID] = existing
	}

	result := make([]FailureRecord, 0, len(merged))
	for _, record := range merged {
		result = append(result, record)
	}
	slices.SortFunc(result, compareFailureRecords)
	return result, nil
}

func (s PipelineStage) valid() bool {
	switch s {
	case PipelineStage01dNormalizePrograms,
		PipelineStage02aExtractCadqueryAst,
		PipelineStage02bExecuteCadquery,
		PipelineStage02cBuildCadGraph,
		PipelineStage03bConstructTaskDefinitions,
		PipelineStage05ValidateAndExportRelease:
		return true
	default:
		return false
	}
}

func sameFailureColumns(left, right FailureRecord) bool {
	return left.FailureID == right.FailureID &&
		left.PipelineStage == right.PipelineStage &&
		left.ProgramID == right.ProgramID &&
		equalPointer(left.TaskID, right.TaskID) &&
		equalPointer(left.InputSHA256, right.InputSHA256) &&
		left.ReasonCode == right.ReasonCode &&
		left.Detail == right.Detail &&
		equalPointer(left.ProgramLine, right.ProgramLine) &&
		equalPointer(left.ProgramSpan, right.ProgramSpan)
}

func compareFailureRecords(left, right FailureRecord) int {
	if order := cmp.Compare(left.PipelineStage, right.PipelineStage); order != 0 {
		return order
	}
	if order := cmp.Compare(left.ProgramID, right.ProgramID); order != 0 {
		return order
	}
	switch {
	case left.TaskID == nil && right.TaskID != nil:
		return -1
	case left.TaskID != nil && right.TaskID == nil:
		return 1
	case left.TaskID != nil && right.TaskID != nil:
		if order := cmp.Compare(*left.TaskID, *right.TaskID); order != 0 {
			return order
		}
	}
	return cmp.Compare(left.ReasonCode, right.ReasonCode)
}

func equalPointer[T comparable](left, right *T) bool {
	if left == nil || right == nil {
		return left == nil && right == nil
	}
	return *left == *right
}

// canonicalJSON marshals a map with sorted keys, no spaces, and no HTML
// escaping. It is the shared definition of canonical JSON for small control
// documents; 03b construct task definitions uses the same rules.
func canonicalJSON(document any) ([]byte, error) {
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(document); err != nil {
		return nil, err
	}
	return bytes.TrimSuffix(buffer.Bytes(), []byte("\n")), nil
}

// CanonicalJSON exposes the canonical JSON encoder to pipeline stages that
// serialize small typed control documents.
func CanonicalJSON(document any) ([]byte, error) {
	return canonicalJSON(document)
}
