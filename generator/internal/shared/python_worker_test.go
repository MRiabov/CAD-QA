package shared

import (
	"context"
	"errors"
	"os/exec"
	"path/filepath"
	"testing"
)

func pythonWorkerForPipelineStage(t *testing.T, pipelineStage string) *PythonWorker {
	t.Helper()

	root := repositoryRoot(t)
	python := pythonExecutable(t, root)
	if _, err := exec.LookPath(python); err != nil {
		t.Skipf("python interpreter %q is not available: %v", python, err)
	}
	worker := NewPythonWorker(pipelineStage)
	worker.Python = python
	worker.Dir = root
	worker.Env = []string{"PYTHONPATH=" + filepath.Join(root, "generator", "python")}
	return worker
}

func pythonWorkerForTest(t *testing.T) *PythonWorker {
	t.Helper()
	return pythonWorkerForPipelineStage(t, "01d_normalize_programs")
}

func startWorker(t *testing.T, worker *PythonWorker) {
	t.Helper()
	if err := worker.Start(context.Background()); err != nil {
		t.Fatalf("start worker: %v", err)
	}
	t.Cleanup(func() { _ = worker.Close() })
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
	for _, pipelineStage := range stages {
		if _, ok := want[pipelineStage]; ok {
			want[pipelineStage] = true
		}
	}
	for pipelineStage, found := range want {
		if !found {
			t.Fatalf("stage %q is missing from %v", pipelineStage, stages)
		}
	}
}

func TestPythonWorkerReturnsPipelineStageNotImplemented(t *testing.T) {
	// 02a has no typed contract yet, so it exercises the free-form path.
	worker := pythonWorkerForPipelineStage(t, "02a_extract_cadquery_ast")
	startWorker(t, worker)

	var response map[string]any
	err := worker.Run(context.Background(), map[string]any{}, &response)
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
	worker.PipelineStage = "99-not-a-stage"

	err := worker.Start(context.Background())
	var workerError *WorkerError
	if !errors.As(err, &workerError) {
		t.Fatalf("error = %v, want *WorkerError", err)
	}
	if workerError.Code != "unknown_stage" {
		t.Fatalf("error code = %q, want unknown_stage", workerError.Code)
	}
}

func TestPythonWorkerReusesOneProcess(t *testing.T) {
	worker := pythonWorkerForTest(t)
	startWorker(t, worker)
	firstPID := worker.cmd.Process.Pid

	for range 2 {
		var response map[string]any
		_ = worker.Run(context.Background(), map[string]any{}, &response)
	}

	if worker.cmd == nil || worker.cmd.Process == nil {
		t.Fatal("worker stopped before the request limit")
	}
	if worker.cmd.Process.Pid != firstPID {
		t.Fatalf("worker PID = %d, want %d", worker.cmd.Process.Pid, firstPID)
	}
	if worker.requests != 2 {
		t.Fatalf("worker requests = %d, want 2", worker.requests)
	}
}

func TestPythonWorkerRestartsAtRequestLimit(t *testing.T) {
	worker := pythonWorkerForTest(t)
	worker.RequestLimit = 2
	startWorker(t, worker)
	firstPID := worker.cmd.Process.Pid

	var response map[string]any
	_ = worker.Run(context.Background(), map[string]any{}, &response)
	if !worker.started {
		t.Fatal("worker stopped before the request limit")
	}

	_ = worker.Run(context.Background(), map[string]any{}, &response)
	if worker.started {
		t.Fatal("worker did not stop at the request limit")
	}

	_ = worker.Run(context.Background(), map[string]any{}, &response)
	if !worker.started {
		t.Fatal("worker did not restart after the request limit")
	}
	if worker.cmd.Process.Pid == firstPID {
		t.Fatal("worker reused the process after the request limit")
	}
}

func TestPythonWorkerCloseRestarts(t *testing.T) {
	worker := pythonWorkerForTest(t)
	startWorker(t, worker)
	firstPID := worker.cmd.Process.Pid

	if err := worker.Close(); err != nil {
		t.Fatalf("close worker: %v", err)
	}

	var response map[string]any
	_ = worker.Run(context.Background(), map[string]any{}, &response)
	if !worker.started {
		t.Fatal("worker did not restart after close")
	}
	if worker.cmd.Process.Pid == firstPID {
		t.Fatal("worker reused the process after close")
	}
}
