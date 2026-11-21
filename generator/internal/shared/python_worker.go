package shared

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

// PythonWorker starts one Python stage worker as a child process. Bulk data
// crosses the boundary as Parquet paths; only the small control request and
// response cross standard input and standard output as JSON.
type PythonWorker struct {
	// Python is the interpreter executable. It defaults to CADQA_PYTHON or
	// python3.
	Python string
	// Module is the worker module. It defaults to cadqa_dataset_generator.cli.
	Module string
	// Dir is the child working directory. Empty means the current directory.
	Dir string
	// Env is appended to the parent environment.
	Env []string
}

// NewPythonWorker returns a worker configured from the environment.
func NewPythonWorker() PythonWorker {
	python := os.Getenv("CADQA_PYTHON")
	if python == "" {
		python = "python3"
	}
	return PythonWorker{
		Python: python,
		Module: "cadqa_dataset_generator.cli",
	}
}

// WorkerError is the structured error a Python worker returns when it handled
// the request but the stage failed.
type WorkerError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

// Error implements error.
func (e *WorkerError) Error() string {
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

type workerEnvelope struct {
	OK     bool            `json:"ok"`
	Result json.RawMessage `json:"result"`
	Error  *WorkerError    `json:"error"`
}

// Run invokes one Python stage. The request is JSON-encoded to standard input;
// a successful result is JSON-decoded into response. A handled stage failure is
// returned as *WorkerError, so the caller can tell a rejection from a crash.
func (w PythonWorker) Run(
	ctx context.Context,
	stage string,
	request any,
	response any,
) error {
	payload, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("encode python worker request for %s: %w", stage, err)
	}

	command := w.command(ctx, stage)
	command.Stdin = bytes.NewReader(payload)

	var stdout, stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr

	runErr := command.Run()
	trimmed := bytes.TrimSpace(stdout.Bytes())
	if len(trimmed) == 0 {
		if runErr != nil {
			return fmt.Errorf(
				"python worker %s failed: %w (stderr: %s)",
				stage, runErr, strings.TrimSpace(stderr.String()),
			)
		}
		return fmt.Errorf(
			"python worker %s returned no response (stderr: %s)",
			stage, strings.TrimSpace(stderr.String()),
		)
	}

	var envelope workerEnvelope
	if err := json.Unmarshal(trimmed, &envelope); err != nil {
		return fmt.Errorf(
			"decode python worker response for %s: %w (stdout: %s, stderr: %s)",
			stage, err, trimmed, strings.TrimSpace(stderr.String()),
		)
	}
	if !envelope.OK {
		if envelope.Error != nil {
			return fmt.Errorf("python worker %s: %w", stage, envelope.Error)
		}
		return fmt.Errorf("python worker %s failed without an error document", stage)
	}
	if runErr != nil {
		return fmt.Errorf("python worker %s exited with %w after reporting success", stage, runErr)
	}
	if response == nil {
		return nil
	}
	if len(envelope.Result) == 0 || string(envelope.Result) == "null" {
		return fmt.Errorf("python worker %s returned no result", stage)
	}
	if err := json.Unmarshal(envelope.Result, response); err != nil {
		return fmt.Errorf("decode python worker result for %s: %w", stage, err)
	}
	return nil
}

// ListStages asks the worker which stage modules it can dispatch.
func (w PythonWorker) ListStages(ctx context.Context) ([]string, error) {
	command := w.command(ctx, "--list-stages")

	var stdout, stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	if err := command.Run(); err != nil {
		return nil, fmt.Errorf(
			"list python worker stages: %w (stderr: %s)",
			err, strings.TrimSpace(stderr.String()),
		)
	}

	var document struct {
		Stages []string `json:"stages"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &document); err != nil {
		return nil, fmt.Errorf("decode python worker stage list: %w", err)
	}
	return document.Stages, nil
}

func (w PythonWorker) command(ctx context.Context, args ...string) *exec.Cmd {
	commandArgs := append([]string{"-m", w.module()}, args...)
	command := exec.CommandContext(ctx, w.python(), commandArgs...)
	command.Dir = w.Dir
	command.Env = append(os.Environ(), w.Env...)
	return command
}

func (w PythonWorker) python() string {
	if w.Python == "" {
		return "python3"
	}
	return w.Python
}

func (w PythonWorker) module() string {
	if w.Module == "" {
		return "cadqa_dataset_generator.cli"
	}
	return w.Module
}
