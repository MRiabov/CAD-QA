// Command generator is the CAD-QA dataset generator.
//
// There is one binary. It owns the run directory, the run lock, pipeline stage
// selection, the shared cache, and the exit codes. Python stage workers are
// child processes; bulk data crosses the boundary as Parquet.
package main

import (
	"context"
	"os"

	"github.com/MRiabov/CAD-QA/generator/internal/run"
)

func main() {
	os.Exit(run.Main(context.Background(), os.Args[1:], os.Stdout, os.Stderr))
}
