package shared

import (
	"os"
	"path/filepath"
	"testing"
)

// repositoryRoot walks up from the test working directory until it finds the
// repository's pyproject.toml. Tests read the real root policy files; they do
// not copy them.
func repositoryRoot(t *testing.T) string {
	t.Helper()

	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("get working directory: %v", err)
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "pyproject.toml")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("repository root not found from test working directory")
		}
		dir = parent
	}
}

// pythonExecutable returns the project virtual environment interpreter when it
// exists, and otherwise falls back to python3.
func pythonExecutable(t *testing.T, root string) string {
	t.Helper()

	candidate := filepath.Join(root, ".venv", "bin", "python")
	if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
		return candidate
	}
	return "python3"
}
