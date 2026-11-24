// Package run owns the generator command line, run directory selection, and
// exit codes. It is the only orchestrator; pipeline stage packages never import
// it.
package run

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"path/filepath"
	"regexp"
	"runtime"
	"slices"
	"strings"
	"time"
)

// Version is the declared generator version. A release records it; it is not
// derived from git.
var Version = "dev"

// Exit codes from the run contract.
const (
	ExitOK          = 0
	ExitBlocked     = 1
	ExitUsage       = 2
	ExitInterrupted = 130
)

// DefaultShardCount is the journal shard count used when --shard-count is not
// set. A sharded pipeline stage runs at most one pass per shard.
const DefaultShardCount = 16

// SelectablePipelineStages is the linear pass. 03c resolve deficits is a
// controller inside 03 and is not selected by --from or --to.
var SelectablePipelineStages = []string{
	"01a-read-cadevolve-metadata",
	"01b-select-program-pool",
	"01c-fetch-program-pool",
	"01d-normalize-programs",
	"01e-write-external-dataset-manifest",
	"02a-extract-cadquery-ast",
	"02b-execute-cadquery",
	"02c-build-cad-graph",
	"03a-allocate-task-quotas",
	"03b-construct-task-definitions",
	"04-render-prompt-and-choices",
	"05-validate-and-export-release",
}

// AllPipelineStages adds the 03c controller, which --force may name.
var AllPipelineStages = []string{
	"01a-read-cadevolve-metadata",
	"01b-select-program-pool",
	"01c-fetch-program-pool",
	"01d-normalize-programs",
	"01e-write-external-dataset-manifest",
	"02a-extract-cadquery-ast",
	"02b-execute-cadquery",
	"02c-build-cad-graph",
	"03a-allocate-task-quotas",
	"03b-construct-task-definitions",
	"03c-resolve-deficits",
	"04-render-prompt-and-choices",
	"05-validate-and-export-release",
}

// ShardedPipelineStages are pipeline stages whose pass is one journal
// shard. A sharded pipeline stage runs at most one pass per shard, so the
// journal shard count is also its concurrency ceiling.
var ShardedPipelineStages = map[string]bool{
	"01d-normalize-programs":         true,
	"02a-extract-cadquery-ast":       true,
	"02b-execute-cadquery":           true,
	"02c-build-cad-graph":            true,
	"03b-construct-task-definitions": true,
	"04-render-prompt-and-choices":   true,
}

// Scope is the declared implementation scope.
type Scope string

const (
	ScopeP0 Scope = "p0"
	ScopeP1 Scope = "p1"
	ScopeP2 Scope = "p2"
)

// LogLevel is the slog threshold.
type LogLevel string

const (
	LogLevelDebug LogLevel = "debug"
	LogLevelInfo  LogLevel = "info"
	LogLevelWarn  LogLevel = "warn"
	LogLevelError LogLevel = "error"
)

// RunOptions is the typed form of `generator run` flags.
type RunOptions struct {
	RunsRoot                  string
	RunDir                    string
	NewRun                    bool
	ExternalDataset           string
	ExternalDatasetRevision   string
	SelectionPolicy           string
	PlanSeed                  *int64
	ReleaseSeed               *int64
	Scope                     Scope
	Balance                   string
	Checks                    string
	Prompts                   string
	TolerancePolicy           string
	ExternalBenchmark         string
	ExternalBenchmarkID       string
	ExternalBenchmarkRevision string
	From                      string
	To                        string
	Force                     []string
	Jobs                      int
	ShardCount                int
	FlushInterval             time.Duration
	FlushRows                 int64
	CacheDir                  string
	NoCache                   bool
	LogLevel                  LogLevel
}

// UsageError is a command-line or input-contract error. It exits 2.
type UsageError struct {
	Message string
}

// Error implements error.
func (e *UsageError) Error() string {
	return e.Message
}

// BlockedError is a run that cannot proceed. It exits 1.
type BlockedError struct {
	Message string
}

// Error implements error.
func (e *BlockedError) Error() string {
	return e.Message
}

// ErrNotImplemented marks scaffolded orchestration that has no pipeline stage
// logic yet.
var ErrNotImplemented = errors.New("run orchestration is not implemented yet")

// Main runs the generator command line and returns the process exit code.
func Main(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	ctx, stop := signal.NotifyContext(ctx, os.Interrupt)
	defer stop()

	if len(args) == 0 {
		printUsage(stderr)
		return ExitUsage
	}

	switch args[0] {
	case "run":
		return runCommand(ctx, args[1:], stderr)
	case "status":
		return statusCommand(ctx, args[1:], stdout, stderr)
	case "list":
		return listCommand(ctx, args[1:], stdout, stderr)
	case "version", "--version", "-version":
		fmt.Fprintf(stdout, "generator %s\n", Version)
		return ExitOK
	case "help", "-h", "--help":
		printUsage(stdout)
		return ExitOK
	default:
		fmt.Fprintf(stderr, "unknown command %q\n", args[0])
		printUsage(stderr)
		return ExitUsage
	}
}

// Run executes one run. It is the orchestrator entry point; pipeline stage
// execution lands one pipeline stage at a time.
//
// TODO(bootstrap): implement run directory allocation, run.json, the run lock,
// pipeline stage selection, and the loop that runs them. This function is the
// only place a pipeline stage package is called from.
func Run(ctx context.Context, options RunOptions) error {
	_ = ctx
	_ = options
	return &BlockedError{Message: ErrNotImplemented.Error()}
}

// Status prints one run's state.
//
// TODO(bootstrap): read run.json, pipeline stage markers, part counts, failure
// counts, and the current release_id.
func Status(ctx context.Context, runDir string, output io.Writer) error {
	_ = ctx
	_ = runDir
	_ = output
	return &BlockedError{Message: ErrNotImplemented.Error()}
}

// List prints the runs under a runs root.
//
// TODO(bootstrap): scan run<NNNN>/run.json, sort by run_number, and print one
// line per run with partial, complete, or invalid status.
func List(ctx context.Context, runsRoot string, output io.Writer) error {
	_ = ctx
	_ = runsRoot
	_ = output
	return &BlockedError{Message: ErrNotImplemented.Error()}
}

// Validate reports whether the run can start.
func (o RunOptions) Validate() error {
	required := []struct {
		name  string
		value string
	}{
		{"--external-dataset", o.ExternalDataset},
		{"--external-dataset-revision", o.ExternalDatasetRevision},
		{"--selection-policy", o.SelectionPolicy},
	}
	for _, field := range required {
		if strings.TrimSpace(field.value) == "" {
			return &UsageError{Message: field.name + " is required"}
		}
	}
	if o.PlanSeed == nil {
		return &UsageError{Message: "--plan-seed is required"}
	}
	if o.ReleaseSeed == nil {
		return &UsageError{Message: "--release-seed is required"}
	}
	switch o.Scope {
	case ScopeP0, ScopeP1, ScopeP2:
	default:
		return &UsageError{Message: fmt.Sprintf("--scope must be p0, p1, or p2, got %q", o.Scope)}
	}
	switch o.LogLevel {
	case LogLevelDebug, LogLevelInfo, LogLevelWarn, LogLevelError:
	default:
		return &UsageError{
			Message: fmt.Sprintf("--log-level must be debug, info, warn, or error, got %q", o.LogLevel),
		}
	}
	if o.NewRun && o.RunDir != "" {
		return &UsageError{Message: "--new-run and --run-dir are incompatible"}
	}
	if o.RunDir != "" {
		if err := validateRunDir(o.RunDir); err != nil {
			return err
		}
	}
	if err := o.validateRange(); err != nil {
		return err
	}
	if err := o.validateForce(); err != nil {
		return err
	}
	if o.Jobs < 0 {
		return &UsageError{Message: fmt.Sprintf("--jobs is %d, minimum is 0", o.Jobs)}
	}
	if o.ShardCount < 1 {
		return &UsageError{Message: fmt.Sprintf("--shard-count is %d, minimum is 1", o.ShardCount)}
	}
	if o.FlushInterval <= 0 {
		return &UsageError{Message: fmt.Sprintf("--flush-interval is %s, must be positive", o.FlushInterval)}
	}
	if o.FlushRows < 1 {
		return &UsageError{Message: fmt.Sprintf("--flush-rows is %d, minimum is 1", o.FlushRows)}
	}
	if o.Selects("05-validate-and-export-release") {
		if o.ExternalBenchmark == "" || o.ExternalBenchmarkID == "" || o.ExternalBenchmarkRevision == "" {
			return &UsageError{
				Message: "--external-benchmark, --external-benchmark-id, and --external-benchmark-revision are required when the range includes 05-validate-and-export-release",
			}
		}
	}
	return nil
}

// PipelineStageConcurrency returns the number of concurrent passes for one
// pipeline stage. A non-positive Jobs selects the host's logical CPU count. A
// sharded pipeline stage is capped by the journal shard count. The 02b caller
// applies MemoryBoundJobs as an additional cap.
func (o RunOptions) PipelineStageConcurrency(pipelineStage string) int {
	jobs := o.Jobs
	if jobs <= 0 {
		jobs = runtime.NumCPU()
	}
	shardCount := o.ShardCount
	if shardCount <= 0 {
		shardCount = DefaultShardCount
	}
	if ShardedPipelineStages[pipelineStage] && shardCount < jobs {
		jobs = shardCount
	}
	return jobs
}

// MemoryBoundJobs returns how many 02b children fit in available memory:
// floor(available / (memory_limit + worker_resident)). A zero result means no
// child fits; the caller blocks instead of starting a pipeline stage.
func MemoryBoundJobs(availableMemory, memoryLimit, workerResident int64) int {
	if availableMemory <= 0 {
		return 0
	}
	perChild := memoryLimit + workerResident
	if perChild <= 0 {
		return 0
	}
	return int(availableMemory / perChild)
}

// Selects reports whether the run range includes one selectable pipeline stage.
func (o RunOptions) Selects(pipelineStage string) bool {
	from := o.From
	if from == "" {
		from = SelectablePipelineStages[0]
	}
	to := o.To
	if to == "" {
		to = SelectablePipelineStages[len(SelectablePipelineStages)-1]
	}

	fromIndex, fromOK := selectableIndex(from)
	toIndex, toOK := selectableIndex(to)
	pipelineStageIndex, pipelineStageOK := selectableIndex(pipelineStage)
	if !fromOK || !toOK || !pipelineStageOK {
		return false
	}
	return pipelineStageIndex >= fromIndex && pipelineStageIndex <= toIndex
}

func (o RunOptions) validateRange() error {
	fromIndex := 0
	toIndex := len(SelectablePipelineStages) - 1

	if o.From != "" {
		index, ok := selectableIndex(o.From)
		if !ok {
			return &UsageError{Message: fmt.Sprintf("--from %q is not a selectable pipeline stage", o.From)}
		}
		fromIndex = index
	}
	if o.To != "" {
		index, ok := selectableIndex(o.To)
		if !ok {
			return &UsageError{Message: fmt.Sprintf("--to %q is not a selectable pipeline stage", o.To)}
		}
		toIndex = index
	}
	if fromIndex > toIndex {
		return &UsageError{Message: fmt.Sprintf("--from %q is after --to %q", o.From, o.To)}
	}
	return nil
}

func (o RunOptions) validateForce() error {
	if len(o.Force) == 0 {
		return nil
	}
	if len(o.Force) > 1 {
		if slices.Contains(o.Force, "all") {
			return &UsageError{Message: "--force all cannot be combined with other stages"}
		}
	}
	for _, pipelineStage := range o.Force {
		if pipelineStage == "all" {
			continue
		}
		if _, ok := allIndex(pipelineStage); !ok {
			return &UsageError{Message: fmt.Sprintf("--force names unknown pipeline stage %q", pipelineStage)}
		}
	}
	return nil
}

func runCommand(ctx context.Context, args []string, stderr io.Writer) int {
	flags := newFlagSet("run", stderr)
	options := RunOptions{
		RunsRoot:        "runs",
		Scope:           ScopeP0,
		Balance:         "generator/config/balance.yaml",
		Checks:          "generator/config/checks.yaml",
		Prompts:         "generator/config/prompts.yaml",
		TolerancePolicy: "generator/config/tolerance.yaml",
		Jobs:            runtime.NumCPU(),
		ShardCount:      DefaultShardCount,
		FlushInterval:   30 * time.Second,
		FlushRows:       10000,
		LogLevel:        LogLevelInfo,
	}

	var planSeed, releaseSeed int64
	var force string
	flags.StringVar(&options.RunsRoot, "runs-root", options.RunsRoot, "root for new runs and for list")
	flags.StringVar(&options.RunDir, "run-dir", "", "resume an existing run directory")
	flags.BoolVar(&options.NewRun, "new-run", false, "allocate a new run directory even on a run_id match")
	flags.StringVar(&options.ExternalDataset, "external-dataset", "", "CADEvolve Parquet cache path or URI")
	flags.StringVar(&options.ExternalDatasetRevision, "external-dataset-revision", "", "expected upstream revision")
	flags.StringVar(&options.SelectionPolicy, "selection-policy", "", "selection policy file, including the seed")
	flags.Int64Var(&planSeed, "plan-seed", 0, "deterministic task quota plan seed")
	flags.Int64Var(&releaseSeed, "release-seed", 0, "RenderConfig.release_seed")
	flags.StringVar((*string)(&options.Scope), "scope", string(options.Scope), "p0, p1, or p2")
	flags.StringVar(&options.Balance, "balance", options.Balance, "balance policy file")
	flags.StringVar(&options.Checks, "checks", options.Checks, "check policy file")
	flags.StringVar(&options.Prompts, "prompts", options.Prompts, "prompt template file")
	flags.StringVar(&options.TolerancePolicy, "tolerance-policy", options.TolerancePolicy, "tolerance policy file")
	flags.StringVar(&options.ExternalBenchmark, "external-benchmark", "", "pinned external benchmark program set")
	flags.StringVar(&options.ExternalBenchmarkID, "external-benchmark-id", "", "benchmark name")
	flags.StringVar(&options.ExternalBenchmarkRevision, "external-benchmark-revision", "", "benchmark revision")
	flags.StringVar(&options.From, "from", "", "first pipeline stage doc stem")
	flags.StringVar(&options.To, "to", "", "last pipeline stage doc stem")
	flags.StringVar(&force, "force", "", "comma-separated pipeline stage stems or all")
	flags.IntVar(&options.Jobs, "jobs", options.Jobs, "maximum concurrent passes")
	flags.IntVar(&options.ShardCount, "shard-count", options.ShardCount, "journal shards; a sharded pipeline stage runs at most one pass per shard")
	flags.DurationVar(&options.FlushInterval, "flush-interval", options.FlushInterval, "maximum interval between Parquet commits")
	flags.Int64Var(&options.FlushRows, "flush-rows", options.FlushRows, "maximum rows between Parquet commits")
	flags.StringVar(&options.CacheDir, "cache-dir", "", "shared cache directory")
	flags.BoolVar(&options.NoCache, "no-cache", false, "disable the shared cache")
	flags.StringVar((*string)(&options.LogLevel), "log-level", string(options.LogLevel), "debug, info, warn, or error")

	if code := parseFlags(flags, args); code != ExitOK {
		return code
	}
	if flags.NArg() > 0 {
		fmt.Fprintf(stderr, "unexpected arguments: %v\n", flags.Args())
		return ExitUsage
	}

	visited := make(map[string]bool)
	flags.Visit(func(visitedFlag *flag.Flag) {
		visited[visitedFlag.Name] = true
	})
	if visited["plan-seed"] {
		options.PlanSeed = &planSeed
	}
	if visited["release-seed"] {
		options.ReleaseSeed = &releaseSeed
	}
	options.Force = splitForce(force)

	if err := options.Validate(); err != nil {
		return reportError(err, stderr)
	}
	if err := Run(ctx, options); err != nil {
		return reportError(err, stderr)
	}
	return ExitOK
}

func statusCommand(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	flags := newFlagSet("status", stderr)
	var runDir string
	flags.StringVar(&runDir, "run-dir", "", "existing run directory")
	if code := parseFlags(flags, args); code != ExitOK {
		return code
	}
	if flags.NArg() > 0 {
		fmt.Fprintf(stderr, "unexpected arguments: %v\n", flags.Args())
		return ExitUsage
	}
	if runDir == "" {
		fmt.Fprintln(stderr, "status: --run-dir is required")
		return ExitUsage
	}
	if err := Status(ctx, runDir, stdout); err != nil {
		return reportError(err, stderr)
	}
	return ExitOK
}

func listCommand(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	flags := newFlagSet("list", stderr)
	runsRoot := "runs"
	flags.StringVar(&runsRoot, "runs-root", runsRoot, "root for run directories")
	if code := parseFlags(flags, args); code != ExitOK {
		return code
	}
	if flags.NArg() > 0 {
		fmt.Fprintf(stderr, "unexpected arguments: %v\n", flags.Args())
		return ExitUsage
	}
	if err := List(ctx, runsRoot, stdout); err != nil {
		return reportError(err, stderr)
	}
	return ExitOK
}

func newFlagSet(name string, stderr io.Writer) *flag.FlagSet {
	flags := flag.NewFlagSet(name, flag.ContinueOnError)
	flags.SetOutput(stderr)
	flags.Usage = func() {
		fmt.Fprintf(stderr, "usage: generator %s [flags]\n", name)
		flags.PrintDefaults()
	}
	return flags
}

func parseFlags(flags *flag.FlagSet, args []string) int {
	if err := flags.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return ExitOK
		}
		return ExitUsage
	}
	return ExitOK
}

func reportError(err error, stderr io.Writer) int {
	if usage, ok := errors.AsType[*UsageError](err); ok {
		fmt.Fprintln(stderr, usage)
		return ExitUsage
	}
	if blocked, ok := errors.AsType[*BlockedError](err); ok {
		fmt.Fprintln(stderr, blocked)
		return ExitBlocked
	}
	if errors.Is(err, context.Canceled) {
		fmt.Fprintln(stderr, "interrupted")
		return ExitInterrupted
	}
	fmt.Fprintln(stderr, err)
	return ExitBlocked
}

func splitForce(value string) []string {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	parts := strings.Split(value, ",")
	pipelineStages := make([]string, 0, len(parts))
	for _, part := range parts {
		pipelineStage := strings.TrimSpace(part)
		if pipelineStage != "" {
			pipelineStages = append(pipelineStages, pipelineStage)
		}
	}
	return pipelineStages
}

func selectableIndex(pipelineStage string) (int, bool) {
	for index, candidate := range SelectablePipelineStages {
		if candidate == pipelineStage {
			return index, true
		}
	}
	return 0, false
}

func allIndex(pipelineStage string) (int, bool) {
	for index, candidate := range AllPipelineStages {
		if candidate == pipelineStage {
			return index, true
		}
	}
	return 0, false
}

var runDirectoryPattern = regexp.MustCompile(`^run[0-9]{4}$`)

func validateRunDir(runDir string) error {
	base := filepath.Base(runDir)
	if !runDirectoryPattern.MatchString(base) {
		return &UsageError{Message: fmt.Sprintf("--run-dir basename %q does not match run<NNNN>", base)}
	}
	info, err := os.Stat(runDir)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return &UsageError{Message: fmt.Sprintf("--run-dir %q does not exist", runDir)}
		}
		return &UsageError{Message: fmt.Sprintf("--run-dir %q: %v", runDir, err)}
	}
	if !info.IsDir() {
		return &UsageError{Message: fmt.Sprintf("--run-dir %q is not a directory", runDir)}
	}
	return nil
}

func printUsage(output io.Writer) {
	fmt.Fprintln(output, `usage:
  generator run [flags]
  generator status --run-dir <runs_root>/run<NNNN>
  generator list [--runs-root <path>]
  generator version`)
}
