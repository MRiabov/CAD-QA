package shared

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

const (
	// WorkerProtocolVersion is the wire version of the JSON request and response
	// documents. It must match WORKER_PROTOCOL_VERSION in
	// generator/python/cadqa_dataset_generator/contracts.py; the contract test checks both sides.
	WorkerProtocolVersion = 1
	// DefaultWorkerRequestLimit bounds how many requests one worker serves
	// before it is replaced. A pipeline stage can override it from its
	// execution environment.
	DefaultWorkerRequestLimit = 1000
	workerStopTimeout         = 5 * time.Second
	workerLogLines            = 20
)

// PythonWorker is one long-lived Python pipeline stage worker. It starts once,
// serves
// newline-delimited JSON requests, and is replaced after a crash, a request
// timeout, or RequestLimit requests. Bulk data crosses the boundary as Parquet
// paths; only the small control request and response cross standard input and
// standard output as JSON.
type PythonWorker struct {
	// Python is the interpreter executable. It defaults to CADQA_PYTHON or
	// python3.
	Python string
	// Module is the worker module. It defaults to cadqa_dataset_generator.worker.
	Module string
	// PipelineStage names which pipeline stage this worker serves. It is fixed
	// for the worker's lifetime.
	PipelineStage string
	// Dir is the child working directory. Empty means the current directory.
	Dir string
	// Env is appended to the parent environment.
	Env []string
	// RequestLimit is the number of requests after which the worker is
	// replaced. Zero selects DefaultWorkerRequestLimit.
	RequestLimit int

	mu       sync.Mutex
	lifetime context.Context
	cmd      *exec.Cmd
	stdin    io.WriteCloser
	encoder  *json.Encoder
	stdout   *json.Decoder
	done     chan error
	log      *workerLog
	requests int
	started  bool
}

// NewPythonWorker returns a worker for one pipeline stage, configured from the
// environment.
func NewPythonWorker(pipelineStage string) *PythonWorker {
	python := os.Getenv("CADQA_PYTHON")
	if python == "" {
		python = "python3"
	}
	return &PythonWorker{
		Python:        python,
		Module:        "cadqa_dataset_generator.worker",
		PipelineStage: pipelineStage,
		RequestLimit:  DefaultWorkerRequestLimit,
	}
}

// WorkerError is the structured error a Python worker returns when it handled
// the request but a pipeline stage failed.
type WorkerError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

// Error implements error.
func (e *WorkerError) Error() string {
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

type workerEnvelope struct {
	OK              bool            `json:"ok"`
	ProtocolVersion int             `json:"protocol_version"`
	Result          json.RawMessage `json:"result"`
	Error           *WorkerError    `json:"error"`
}

// Start launches the worker and waits for its ready document. The context
// bounds the worker's lifetime: canceling it kills the process.
func (w *PythonWorker) Start(ctx context.Context) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.lifetime = ctx
	return w.startLocked()
}

func (w *PythonWorker) startLocked() error {
	if w.started {
		return nil
	}
	if w.PipelineStage == "" {
		return fmt.Errorf("python worker: stage is required")
	}

	lifetime := w.lifetime
	if lifetime == nil {
		lifetime = context.Background()
	}
	command := exec.CommandContext(lifetime, w.python(), "-m", w.module(), w.PipelineStage)
	command.Dir = w.Dir
	command.Env = append(os.Environ(), w.Env...)

	stdin, err := command.StdinPipe()
	if err != nil {
		return fmt.Errorf("python worker %s: stdin: %w", w.PipelineStage, err)
	}
	stdout, err := command.StdoutPipe()
	if err != nil {
		_ = stdin.Close()
		return fmt.Errorf("python worker %s: stdout: %w", w.PipelineStage, err)
	}
	stderr, err := command.StderrPipe()
	if err != nil {
		_ = stdin.Close()
		return fmt.Errorf("python worker %s: stderr: %w", w.PipelineStage, err)
	}
	if err := command.Start(); err != nil {
		_ = stdin.Close()
		return fmt.Errorf("python worker %s: start: %w", w.PipelineStage, err)
	}

	log := &workerLog{}
	w.cmd = command
	w.stdin = stdin
	w.encoder = json.NewEncoder(stdin)
	w.stdout = json.NewDecoder(stdout)
	done := make(chan error, 1)
	w.done = done
	w.log = log
	w.requests = 0
	w.started = true
	go func() { done <- command.Wait() }()
	go captureWorkerLog(log, stderr)

	return w.waitReadyLocked()
}

func (w *PythonWorker) waitReadyLocked() error {
	var envelope workerEnvelope
	if err := w.stdout.Decode(&envelope); err != nil {
		stderr := w.log.String()
		w.stopLocked()
		return fmt.Errorf("python worker %s: ready: %w (stderr: %s)", w.PipelineStage, err, stderr)
	}
	if envelope.ProtocolVersion != WorkerProtocolVersion {
		w.stopLocked()
		return fmt.Errorf(
			"python worker %s: protocol version %d, want %d",
			w.PipelineStage, envelope.ProtocolVersion, WorkerProtocolVersion,
		)
	}
	if !envelope.OK {
		w.stopLocked()
		if envelope.Error != nil {
			return fmt.Errorf("python worker %s: %w", w.PipelineStage, envelope.Error)
		}
		return fmt.Errorf("python worker %s: not ready", w.PipelineStage)
	}
	var ready struct {
		Ready bool `json:"ready"`
	}
	if len(envelope.Result) == 0 || json.Unmarshal(envelope.Result, &ready) != nil || !ready.Ready {
		w.stopLocked()
		return fmt.Errorf("python worker %s: did not signal ready", w.PipelineStage)
	}
	return nil
}

// Run sends one request and decodes one response. The context bounds the
// request; canceling it kills the worker, which the caller replaces.
func (w *PythonWorker) Run(ctx context.Context, request any, response any) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if !w.started {
		if err := w.startLocked(); err != nil {
			return err
		}
	}
	if err := w.encoder.Encode(request); err != nil {
		stderr := w.log.String()
		w.stopLocked()
		return fmt.Errorf("python worker %s: encode request: %w (stderr: %s)", w.PipelineStage, err, stderr)
	}

	type decoded struct {
		envelope workerEnvelope
		err      error
	}
	decoder := w.stdout
	received := make(chan decoded, 1)
	go func() {
		var envelope workerEnvelope
		err := decoder.Decode(&envelope)
		received <- decoded{envelope: envelope, err: err}
	}()

	select {
	case <-ctx.Done():
		stderr := w.log.String()
		w.stopLocked()
		return fmt.Errorf("python worker %s: %w (stderr: %s)", w.PipelineStage, ctx.Err(), stderr)
	case result := <-received:
		w.requests++
		if w.RequestLimit > 0 && w.requests >= w.RequestLimit {
			defer w.stopLocked()
		}
		if result.err != nil {
			stderr := w.log.String()
			w.stopLocked()
			return fmt.Errorf("python worker %s: response: %w (stderr: %s)", w.PipelineStage, result.err, stderr)
		}
		if result.envelope.ProtocolVersion != WorkerProtocolVersion {
			w.stopLocked()
			return fmt.Errorf(
				"python worker %s: protocol version %d, want %d",
				w.PipelineStage, result.envelope.ProtocolVersion, WorkerProtocolVersion,
			)
		}
		if !result.envelope.OK {
			if result.envelope.Error != nil {
				return fmt.Errorf("python worker %s: %w", w.PipelineStage, result.envelope.Error)
			}
			return fmt.Errorf("python worker %s: failed without an error document", w.PipelineStage)
		}
		if response == nil {
			return nil
		}
		if len(result.envelope.Result) == 0 || string(result.envelope.Result) == "null" {
			return fmt.Errorf("python worker %s: returned no result", w.PipelineStage)
		}
		if err := json.Unmarshal(result.envelope.Result, response); err != nil {
			return fmt.Errorf("python worker %s: decode result: %w", w.PipelineStage, err)
		}
		return nil
	}
}

// Close stops the worker. A later Run starts a new process.
func (w *PythonWorker) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.stopLocked()
	return nil
}

func (w *PythonWorker) stopLocked() {
	if !w.started {
		return
	}
	w.started = false
	if w.stdin != nil {
		_ = w.stdin.Close()
	}
	if w.cmd != nil && w.cmd.Process != nil && w.done != nil {
		select {
		case <-w.done:
		case <-time.After(workerStopTimeout):
			_ = w.cmd.Process.Kill()
			<-w.done
		}
	}
	w.cmd = nil
	w.stdin = nil
	w.encoder = nil
	w.stdout = nil
	w.done = nil
}

// ListStages asks a one-shot worker which stage modules it can dispatch.
func (w *PythonWorker) ListStages(ctx context.Context) ([]string, error) {
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
		ProtocolVersion int      `json:"protocol_version"`
		Stages          []string `json:"stages"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &document); err != nil {
		return nil, fmt.Errorf("decode python worker stage list: %w", err)
	}
	if document.ProtocolVersion != WorkerProtocolVersion {
		return nil, fmt.Errorf(
			"python worker protocol version %d, want %d",
			document.ProtocolVersion, WorkerProtocolVersion,
		)
	}
	return document.Stages, nil
}

func (w *PythonWorker) command(ctx context.Context, args ...string) *exec.Cmd {
	commandArgs := append([]string{"-m", w.module()}, args...)
	command := exec.CommandContext(ctx, w.python(), commandArgs...)
	command.Dir = w.Dir
	command.Env = append(os.Environ(), w.Env...)
	return command
}

func (w *PythonWorker) python() string {
	if w.Python == "" {
		return "python3"
	}
	return w.Python
}

func (w *PythonWorker) module() string {
	if w.Module == "" {
		return "cadqa_dataset_generator.worker"
	}
	return w.Module
}

type workerLog struct {
	mu    sync.Mutex
	lines []string
}

func (l *workerLog) append(line string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if len(l.lines) == workerLogLines {
		copy(l.lines, l.lines[1:])
		l.lines[len(l.lines)-1] = line
		return
	}
	l.lines = append(l.lines, line)
}

func (l *workerLog) String() string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return strings.Join(l.lines, "\n")
}

func captureWorkerLog(log *workerLog, reader io.Reader) {
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		log.append(scanner.Text())
	}
}
