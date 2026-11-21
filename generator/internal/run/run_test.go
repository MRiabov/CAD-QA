package run

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func baseRunArgs() []string {
	return []string{
		"run",
		"--external-dataset", "cache",
		"--external-dataset-revision", "rev",
		"--selection-policy", "selection.yaml",
		"--plan-seed", "1",
		"--release-seed", "2",
	}
}

func fullRunArgs() []string {
	return append(baseRunArgs(),
		"--external-benchmark", "bench",
		"--external-benchmark-id", "bench-id",
		"--external-benchmark-revision", "bench-rev",
	)
}

func TestMainVersion(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), []string{"version"}, &stdout, &stderr)
	if code != ExitOK {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitOK, stderr.String())
	}
	if !strings.Contains(stdout.String(), "generator") {
		t.Fatalf("version output = %q", stdout.String())
	}
}

func TestMainUnknownCommand(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), []string{"nope"}, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d", code, ExitUsage)
	}
	if !strings.Contains(stderr.String(), "unknown command") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunRequiresExternalDataset(t *testing.T) {
	args := []string{"run"}
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d", code, ExitUsage)
	}
	if !strings.Contains(stderr.String(), "--external-dataset") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunRejectsNewRunWithRunDir(t *testing.T) {
	runDir := filepath.Join(t.TempDir(), "run0001")
	if err := os.Mkdir(runDir, 0o755); err != nil {
		t.Fatalf("create run directory: %v", err)
	}

	args := append(baseRunArgs(), "--new-run", "--run-dir", runDir)
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitUsage, stderr.String())
	}
	if !strings.Contains(stderr.String(), "incompatible") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunRejectsFromAfterTo(t *testing.T) {
	args := append(fullRunArgs(),
		"--from", "02a-extract-cadquery-ast",
		"--to", "01a-read-cadevolve-metadata",
	)
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitUsage, stderr.String())
	}
}

func TestRunRejectsUnknownForce(t *testing.T) {
	args := append(fullRunArgs(), "--force", "not-a-stage")
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitUsage, stderr.String())
	}
}

func TestRunRequiresExternalBenchmarkForRelease(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), baseRunArgs(), &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitUsage, stderr.String())
	}
	if !strings.Contains(stderr.String(), "--external-benchmark") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunReportsNotImplemented(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), fullRunArgs(), &stdout, &stderr)
	if code != ExitBlocked {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitBlocked, stderr.String())
	}
	if !strings.Contains(stderr.String(), "not implemented") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunRejectsInvalidScope(t *testing.T) {
	args := append(fullRunArgs(), "--scope", "p9")
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d", code, ExitUsage)
	}
}

func TestStatusRequiresRunDir(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), []string{"status"}, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d", code, ExitUsage)
	}
}

func TestSelects(t *testing.T) {
	options := RunOptions{From: "01c-fetch-program-pool", To: "03b-construct-task-definitions"}
	cases := map[string]bool{
		"01a-read-cadevolve-metadata":    false,
		"01c-fetch-program-pool":         true,
		"02b-execute-cadquery":           true,
		"03b-construct-task-definitions": true,
		"04-render-prompt-and-choices":   false,
		"03c-resolve-deficits":           false,
	}
	for pipelineStage, want := range cases {
		if got := options.Selects(pipelineStage); got != want {
			t.Errorf("Selects(%q) = %v, want %v", pipelineStage, got, want)
		}
	}
}

func TestValidateRunDir(t *testing.T) {
	root := t.TempDir()
	valid := filepath.Join(root, "run0001")
	if err := os.Mkdir(valid, 0o755); err != nil {
		t.Fatalf("create valid run directory: %v", err)
	}
	short := filepath.Join(root, "run25")
	if err := os.Mkdir(short, 0o755); err != nil {
		t.Fatalf("create short run directory: %v", err)
	}

	if err := validateRunDir(valid); err != nil {
		t.Fatalf("valid run directory rejected: %v", err)
	}
	if err := validateRunDir(short); err == nil {
		t.Fatal("two-digit run directory was accepted")
	}
	if err := validateRunDir(filepath.Join(root, "run0002")); err == nil {
		t.Fatal("missing run directory was accepted")
	}
}

func TestRunDirMustExist(t *testing.T) {
	runDir := filepath.Join(t.TempDir(), "run0001")
	args := append(baseRunArgs(), "--run-dir", runDir, "--to", "04-render-prompt-and-choices")
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitUsage, stderr.String())
	}
	if !strings.Contains(stderr.String(), "does not exist") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestSplitForce(t *testing.T) {
	if got := splitForce(""); got != nil {
		t.Fatalf("splitForce(\"\") = %v, want nil", got)
	}
	got := splitForce("01a-read-cadevolve-metadata, 02b-execute-cadquery")
	if len(got) != 2 || got[0] != "01a-read-cadevolve-metadata" || got[1] != "02b-execute-cadquery" {
		t.Fatalf("splitForce = %v", got)
	}
}

func TestPipelineStageConcurrencyCapsShardedStages(t *testing.T) {
	options := RunOptions{Jobs: 8, ShardCount: 3}
	if got := options.PipelineStageConcurrency("01d-normalize-programs"); got != 3 {
		t.Fatalf("01d concurrency = %d, want 3", got)
	}
	if got := options.PipelineStageConcurrency("01c-fetch-program-pool"); got != 8 {
		t.Fatalf("01c concurrency = %d, want 8", got)
	}
}

func TestPipelineStageConcurrencyUsesCPUWhenJobsIsZero(t *testing.T) {
	options := RunOptions{ShardCount: 16}
	if got := options.PipelineStageConcurrency("01c-fetch-program-pool"); got != runtime.NumCPU() {
		t.Fatalf("01c concurrency = %d, want %d", got, runtime.NumCPU())
	}
}

func TestMemoryBoundJobs(t *testing.T) {
	const (
		gib = int64(1 << 30)
		mib = int64(1 << 20)
	)
	if got := MemoryBoundJobs(16*gib, 2*gib, 451*mib); got != 6 {
		t.Fatalf("memory-bound jobs = %d, want 6", got)
	}
	if got := MemoryBoundJobs(1*gib, 2*gib, 451*mib); got != 0 {
		t.Fatalf("memory-bound jobs = %d, want 0", got)
	}
}

func TestRunRejectsInvalidShardCount(t *testing.T) {
	args := append(baseRunArgs(), "--shard-count", "0")
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d", code, ExitUsage)
	}
	if !strings.Contains(stderr.String(), "--shard-count") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunRejectsNegativeJobs(t *testing.T) {
	args := append(baseRunArgs(), "--jobs", "-1")
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitUsage {
		t.Fatalf("exit code = %d, want %d", code, ExitUsage)
	}
	if !strings.Contains(stderr.String(), "--jobs") {
		t.Fatalf("stderr = %q", stderr.String())
	}
}

func TestRunAcceptsJobsAndShardCount(t *testing.T) {
	args := append(fullRunArgs(), "--jobs", "2", "--shard-count", "4")
	var stdout, stderr bytes.Buffer
	code := Main(context.Background(), args, &stdout, &stderr)
	if code != ExitBlocked {
		t.Fatalf("exit code = %d, want %d (stderr: %s)", code, ExitBlocked, stderr.String())
	}
}
