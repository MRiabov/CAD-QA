# 02b — Execute CadQuery

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** run the normalized program and capture solid-state snapshots, or a
failure tombstone when execution fails.

## Input / output

- Input: normalized program.
- Output: `ExecutionResult` — execution snapshots or a failure tombstone.

## Behavior

- Execute in an isolated environment with a recorded CadQuery version.
- Capture the solid state before and after each operation.
- Capture operation effects and topology changes.
- On failure, write a failure tombstone with program identity, operation,
  error, environment, and cache key.
- Never pass a failed output to graph assembly as a measurable state.

## Caching

A failure tombstone is reusable for the same program, operation, and
environment. It is not a graph entity and never supports an answer.
