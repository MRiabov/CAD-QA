package shared

import (
	"path/filepath"
	"strings"
	"testing"
)

func testFailureRecord() FailureRecord {
	taskID := "cadqatask:one"
	inputSHA := "abc123"
	sourceLine := int64(7)
	record := FailureRecord{
		PipelineStage:   Stage01dNormalizePrograms,
		ProgramID:       "cadqaprog:one",
		TaskID:          &taskID,
		InputSHA256:     &inputSHA,
		ReasonCode:      "syntax_error",
		Detail:          "unexpected token",
		SourceLine:      &sourceLine,
		SourceSpan:      &SourceSpan{StartColumn: 3, EndColumn: 9},
		OccurrenceCount: 1,
	}
	if err := record.AssignFailureID(); err != nil {
		panic(err)
	}
	return record
}

func TestFailureIDIsDeterministicVersion5(t *testing.T) {
	first := testFailureRecord()
	second := testFailureRecord()

	if first.FailureID != second.FailureID {
		t.Fatalf("failure id is not deterministic: %s != %s", first.FailureID, second.FailureID)
	}
	if got := first.FailureID.Version(); got != 5 {
		t.Fatalf("failure id version = %d, want 5", got)
	}
	if got := FailureRecordNamespace.Version(); got != 5 {
		t.Fatalf("failure record namespace version = %d, want 5", got)
	}

	changed := testFailureRecord()
	changed.ReasonCode = "format_failure"
	if err := changed.AssignFailureID(); err != nil {
		t.Fatalf("assign changed failure id: %v", err)
	}
	if changed.FailureID == first.FailureID {
		t.Fatal("failure id did not change with the reason code")
	}
}

func TestFailureDedupeKeyCanonicalJSONIsSorted(t *testing.T) {
	record := testFailureRecord()
	payload, err := record.DedupeKey().CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical json: %v", err)
	}

	text := string(payload)
	positions := []string{
		`"input_sha256"`,
		`"pipeline_stage"`,
		`"program_id"`,
		`"reason_code"`,
		`"task_id"`,
	}
	last := -1
	for _, key := range positions {
		index := strings.Index(text, key)
		if index < 0 {
			t.Fatalf("canonical json %s has no %s", text, key)
		}
		if index <= last {
			t.Fatalf("canonical json %s is not sorted at %s", text, key)
		}
		last = index
	}
	if strings.ContainsAny(text, " \n") {
		t.Fatalf("canonical json %s contains whitespace", text)
	}
}

func TestMergeFailureRecordsSumsOccurrencesAndSorts(t *testing.T) {
	first := testFailureRecord()
	first.OccurrenceCount = 2

	second := testFailureRecord()
	second.OccurrenceCount = 3

	otherTaskID := "cadqatask:zero"
	other := FailureRecord{
		PipelineStage:   Stage02aExtractCadqueryAst,
		ProgramID:       "cadqaprog:zero",
		TaskID:          &otherTaskID,
		ReasonCode:      "unsupported_call",
		Detail:          "call is outside the allowlist",
		OccurrenceCount: 1,
	}
	if err := other.AssignFailureID(); err != nil {
		t.Fatalf("assign other failure id: %v", err)
	}

	programOnly := FailureRecord{
		PipelineStage:   Stage02aExtractCadqueryAst,
		ProgramID:       "cadqaprog:zero",
		ReasonCode:      "parse_failure",
		Detail:          "ast parse failed",
		OccurrenceCount: 1,
	}
	if err := programOnly.AssignFailureID(); err != nil {
		t.Fatalf("assign program-only failure id: %v", err)
	}

	merged, err := MergeFailureRecords([]FailureRecord{other, first, second, programOnly})
	if err != nil {
		t.Fatalf("merge failure records: %v", err)
	}
	if len(merged) != 3 {
		t.Fatalf("merged %d records, want 3", len(merged))
	}
	if merged[0].FailureID != first.FailureID {
		t.Fatalf("first merged record = %s, want %s", merged[0].FailureID, first.FailureID)
	}
	if merged[0].OccurrenceCount != 5 {
		t.Fatalf("first occurrence count = %d, want 5", merged[0].OccurrenceCount)
	}
	if merged[1].TaskID != nil {
		t.Fatalf("program-only record has task id %q, want nil", *merged[1].TaskID)
	}
	if merged[2].TaskID == nil || *merged[2].TaskID != otherTaskID {
		t.Fatalf("last merged record task id = %v, want %q", merged[2].TaskID, otherTaskID)
	}
}

func TestMergeFailureRecordsRejectsDisagreeingColumns(t *testing.T) {
	first := testFailureRecord()
	second := testFailureRecord()
	second.Detail = "a different message"

	_, err := MergeFailureRecords([]FailureRecord{first, second})
	if err == nil {
		t.Fatal("expected a disagreeing-column error")
	}
}

func TestFailureRecordValidate(t *testing.T) {
	valid := testFailureRecord()
	if err := valid.Validate(); err != nil {
		t.Fatalf("valid record rejected: %v", err)
	}

	longDetail := valid
	longDetail.Detail = strings.Repeat("x", 501)
	if err := longDetail.Validate(); err == nil {
		t.Fatal("record with a 501-character detail was accepted")
	}

	zeroCount := valid
	zeroCount.OccurrenceCount = 0
	if err := zeroCount.Validate(); err == nil {
		t.Fatal("record with a zero occurrence count was accepted")
	}

	badSpan := valid
	badSpan.SourceSpan = &SourceSpan{StartColumn: 9, EndColumn: 3}
	if err := badSpan.Validate(); err == nil {
		t.Fatal("record with a reversed source span was accepted")
	}
}

func TestFailureRecordParquetRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "failures.parquet")
	identity := ArtifactIdentity{
		Name:          "failure-record",
		SchemaVersion: "1",
		Inputs:        map[string]string{"pipeline_stage": "01d_normalize_programs"},
	}
	records := []FailureRecord{testFailureRecord()}

	if err := WriteParquetAtomic(path, identity, records); err != nil {
		t.Fatalf("write failure records: %v", err)
	}
	read, err := ReadParquet[FailureRecord](path)
	if err != nil {
		t.Fatalf("read failure records: %v", err)
	}
	if len(read) != 1 {
		t.Fatalf("read %d records, want 1", len(read))
	}
	if read[0].FailureID != records[0].FailureID {
		t.Fatalf("failure id = %s, want %s", read[0].FailureID, records[0].FailureID)
	}
	if read[0].PipelineStage != records[0].PipelineStage {
		t.Fatalf("pipeline stage = %q, want %q", read[0].PipelineStage, records[0].PipelineStage)
	}
	if read[0].SourceSpan == nil || *read[0].SourceSpan != *records[0].SourceSpan {
		t.Fatalf("source span = %+v, want %+v", read[0].SourceSpan, records[0].SourceSpan)
	}
}

func TestMergeEmptyFailureRecords(t *testing.T) {
	merged, err := MergeFailureRecords(nil)
	if err != nil {
		t.Fatalf("merge empty records: %v", err)
	}
	if len(merged) != 0 {
		t.Fatalf("merged %d records, want 0", len(merged))
	}
}
