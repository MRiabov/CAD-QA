# 02a — Extract CadQuery AST

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** extract the static structure of a CadQuery program without running
it.

## Input / output

- Input: normalized program.
- Output: static CadQuery model.

## Behavior

- Parse assignments and call chains.
- Identify operations and their order.
- Extract CadQuery profiles, CadQuery workplanes, paths, and named arguments.
- Preserve program order and variable names for internal identity.
- Do not execute CadQuery and do not produce geometry measurements.

## Open questions

- Which CadQuery constructs must be supported before graph build can start?
- When should an unsupported construct reject the program rather than emit a
  diagnostic?
