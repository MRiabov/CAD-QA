package shared

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/google/uuid"
)

type artifactTestRow struct {
	ID   uuid.UUID   `parquet:"id"`
	Name string      `parquet:"name"`
	Span *SourceSpan `parquet:"span,optional"`
}

func TestArtifactIdentityKeySortsInputs(t *testing.T) {
	left := ArtifactIdentity{
		Name:          "program-metadata",
		SchemaVersion: "1",
		Inputs:        map[string]string{"b": "2", "a": "1"},
	}
	right := ArtifactIdentity{
		Name:          "program-metadata",
		SchemaVersion: "1",
		Inputs:        map[string]string{"a": "1", "b": "2"},
	}

	if got, want := left.Key(), "a=1;b=2"; got != want {
		t.Fatalf("identity key = %q, want %q", got, want)
	}
	if left.Key() != right.Key() {
		t.Fatalf("identity key depends on map order: %q != %q", left.Key(), right.Key())
	}
}

func TestArtifactIdentityRejectsEmptyFields(t *testing.T) {
	cases := map[string]ArtifactIdentity{
		"name":           {SchemaVersion: "1"},
		"schema_version": {Name: "artifact"},
		"input name":     {Name: "artifact", SchemaVersion: "1", Inputs: map[string]string{"": "1"}},
		"input value":    {Name: "artifact", SchemaVersion: "1", Inputs: map[string]string{"a": ""}},
	}
	for name, identity := range cases {
		t.Run(name, func(t *testing.T) {
			if err := identity.Validate(); err == nil {
				t.Fatal("expected a validation error")
			}
		})
	}
}

func TestWriteParquetAtomicRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "artifact.parquet")
	identity := ArtifactIdentity{
		Name:          "failure-record-test",
		SchemaVersion: "1",
		Inputs:        map[string]string{"cache_revision": "abc123"},
	}
	rows := []artifactTestRow{
		{
			ID:   uuid.MustParse("11111111-1111-5111-8111-111111111111"),
			Name: "one",
			Span: &SourceSpan{StartColumn: 1, EndColumn: 4},
		},
		{
			ID:   uuid.MustParse("22222222-2222-5222-8222-222222222222"),
			Name: "two",
		},
	}

	if err := WriteParquetAtomic(path, identity, rows); err != nil {
		t.Fatalf("write artifact: %v", err)
	}

	read, err := ReadParquet[artifactTestRow](path)
	if err != nil {
		t.Fatalf("read artifact: %v", err)
	}
	if len(read) != len(rows) {
		t.Fatalf("read %d rows, want %d", len(read), len(rows))
	}
	if read[0].ID != rows[0].ID || read[0].Name != rows[0].Name {
		t.Fatalf("first row = %+v, want %+v", read[0], rows[0])
	}
	if read[0].Span == nil || *read[0].Span != *rows[0].Span {
		t.Fatalf("first span = %+v, want %+v", read[0].Span, rows[0].Span)
	}
	if read[1].Span != nil {
		t.Fatalf("second span = %+v, want nil", read[1].Span)
	}

	metadata, err := ReadArtifactMetadata(path)
	if err != nil {
		t.Fatalf("read artifact metadata: %v", err)
	}
	if got := metadata[ArtifactNameMetadataKey]; got != identity.Name {
		t.Fatalf("artifact name metadata = %q, want %q", got, identity.Name)
	}
	if got := metadata[SchemaVersionMetadataKey]; got != identity.SchemaVersion {
		t.Fatalf("schema version metadata = %q, want %q", got, identity.SchemaVersion)
	}
	if got := metadata[ArtifactIdentityMetadataKey]; got != identity.Key() {
		t.Fatalf("identity metadata = %q, want %q", got, identity.Key())
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read artifact directory: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("artifact directory has %d entries, want 1: %v", len(entries), entries)
	}
}
