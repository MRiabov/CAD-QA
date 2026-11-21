package shared

import (
	"context"
	"errors"
	"os/exec"
	"testing"
)

func pythonWorkerForTest(t *testing.T) PythonWorker {
	t.Helper()

	root := repositoryRoot(t)
	python := pythonExecutable(t, root)
	if _, err := exec.LookPath(python); err != nil {
		t.Skipf("python interpreter %q is not available: %v", python, err)
	}
	return PythonWorker{
		Python: python,
		Dir:    root,
		Env:    []string{"PYTHONPATH=" + root},
	}
}

func TestPythonWorkerListsStages(t *testing.T) {
	worker := pythonWorkerForTest(t)

	stages, err := worker.ListStages(context.Background())
	if err != nil {
		t.Fatalf("list stages: %v", err)
	}

	want := map[string]bool{
		"01d_normalize_programs":   false,
		"02a_extract_cadquery_ast": false,
		"02b_execute_cadquery":     false,
	}
	for _, stage := range stages {
		if _, ok := want[stage]; ok {
			want[stage] = true
		}
	}
	for stage, found := range want {
		if !found {
			t.Fatalf("stage %q is missing from %v", stage, stages)
		}
	}
}

func TestPythonWorkerReturnsStageNotImplemented(t *testing.T) {
	worker := pythonWorkerForTest(t)

	var response map[string]any
	err := worker.Run(context.Background(), "01d_normalize_programs", map[string]any{}, &response)
	if err == nil {
		t.Fatal("unimplemented stage returned no error")
	}

	var workerError *WorkerError
	if !errors.As(err, &workerError) {
		t.Fatalf("error = %v, want *WorkerError", err)
	}
	if workerError.Code != "stage_not_implemented" {
		t.Fatalf("error code = %q, want stage_not_implemented", workerError.Code)
	}
}

func TestPythonWorkerReturnsUnknownStage(t *testing.T) {
	worker := pythonWorkerForTest(t)

	err := worker.Run(context.Background(), "99-not-a-stage", map[string]any{}, nil)
	var workerError *WorkerError
	if !errors.As(err, &workerError) {
		t.Fatalf("error = %v, want *WorkerError", err)
	}
	if workerError.Code != "unknown_stage" {
		t.Fatalf("error code = %q, want unknown_stage", workerError.Code)
	}
}
