// Package shared holds the typed artifacts and process plumbing that more than
// one Go pipeline stage imports.
//
// The package owns the Parquet write path, the failure record, the YAML policy
// loaders, and the Python worker bridge. It does not own the run directory or
// the orchestrator; those live in internal/run.
package shared

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/parquet-go/parquet-go"
)

// Parquet metadata keys written on every artifact produced by this package.
// The run manifest and the release manifest also record the schema version;
// the file metadata makes a single part self-describing.
const (
	ArtifactNameMetadataKey     = "cadqa.artifact"
	SchemaVersionMetadataKey    = "cadqa.schema_version"
	ArtifactIdentityMetadataKey = "cadqa.identity"
)

// ArtifactIdentity is the versioned identity of one typed artifact. Inputs are
// the named values that determine the artifact bytes, such as a cache revision
// and a metadata schema version. Key sorts the inputs, so two identities with
// the same inputs produce the same key regardless of map iteration order.
type ArtifactIdentity struct {
	Name          string
	SchemaVersion string
	Inputs        map[string]string
}

// Validate reports whether the identity is complete enough to write.
func (i ArtifactIdentity) Validate() error {
	if strings.TrimSpace(i.Name) == "" {
		return errors.New("artifact identity: name is empty")
	}
	if strings.TrimSpace(i.SchemaVersion) == "" {
		return errors.New("artifact identity: schema version is empty")
	}
	for key, value := range i.Inputs {
		if strings.TrimSpace(key) == "" {
			return errors.New("artifact identity: input name is empty")
		}
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("artifact identity: input %q is empty", key)
		}
	}
	return nil
}

// Key returns the canonical identity string: sorted name=value pairs joined by
// semicolons. An empty input map returns an empty string.
func (i ArtifactIdentity) Key() string {
	names := make([]string, 0, len(i.Inputs))
	for name := range i.Inputs {
		names = append(names, name)
	}
	sort.Strings(names)

	pairs := make([]string, 0, len(names))
	for _, name := range names {
		pairs = append(pairs, name+"="+i.Inputs[name])
	}
	return strings.Join(pairs, ";")
}

func (i ArtifactIdentity) writerOptions() []parquet.WriterOption {
	return []parquet.WriterOption{
		parquet.KeyValueMetadata(ArtifactNameMetadataKey, i.Name),
		parquet.KeyValueMetadata(SchemaVersionMetadataKey, i.SchemaVersion),
		parquet.KeyValueMetadata(ArtifactIdentityMetadataKey, i.Key()),
	}
}

// WriteParquetAtomic writes rows as one typed Parquet file. It writes a
// temporary file in the destination directory, fsyncs it, renames it into
// place, and fsyncs the directory. A reader never observes a partial file.
func WriteParquetAtomic[T any](
	path string,
	identity ArtifactIdentity,
	rows []T,
	options ...parquet.WriterOption,
) (err error) {
	if err := identity.Validate(); err != nil {
		return err
	}

	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("create artifact directory %s: %w", dir, err)
	}

	tmp, err := os.CreateTemp(dir, "."+filepath.Base(path)+".tmp-*")
	if err != nil {
		return fmt.Errorf("create temporary artifact for %s: %w", path, err)
	}
	tmpPath := tmp.Name()
	defer func() {
		if err != nil {
			_ = os.Remove(tmpPath)
		}
	}()

	writerOptions := append(identity.writerOptions(), options...)
	if err = parquet.Write(tmp, rows, writerOptions...); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("write Parquet %s: %w", path, err)
	}
	if err = tmp.Sync(); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("sync temporary artifact for %s: %w", path, err)
	}
	if err = tmp.Close(); err != nil {
		return fmt.Errorf("close temporary artifact for %s: %w", path, err)
	}
	if err = os.Rename(tmpPath, path); err != nil {
		return fmt.Errorf("rename temporary artifact into %s: %w", path, err)
	}
	if err = syncDirectory(dir); err != nil {
		return fmt.Errorf("sync artifact directory %s: %w", dir, err)
	}
	return nil
}

// ReadParquet reads a typed Parquet file. The row type may name a subset of the
// file schema, in which case only those columns are loaded.
func ReadParquet[T any](path string, options ...parquet.ReaderOption) ([]T, error) {
	rows, err := parquet.ReadFile[T](path, options...)
	if err != nil {
		return nil, fmt.Errorf("read Parquet %s: %w", path, err)
	}
	return rows, nil
}

// ReadArtifactMetadata returns the key/value metadata stored in a Parquet file.
func ReadArtifactMetadata(path string) (map[string]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open Parquet %s: %w", path, err)
	}
	defer file.Close()

	info, err := file.Stat()
	if err != nil {
		return nil, fmt.Errorf("stat Parquet %s: %w", path, err)
	}
	parquetFile, err := parquet.OpenFile(file, info.Size())
	if err != nil {
		return nil, fmt.Errorf("open Parquet metadata %s: %w", path, err)
	}

	metadata := make(map[string]string, len(parquetFile.Metadata().KeyValueMetadata))
	for _, entry := range parquetFile.Metadata().KeyValueMetadata {
		metadata[entry.Key] = entry.Value
	}
	return metadata, nil
}

func syncDirectory(dir string) error {
	handle, err := os.Open(dir)
	if err != nil {
		return err
	}
	defer handle.Close()
	return handle.Sync()
}
