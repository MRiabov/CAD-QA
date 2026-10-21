# Pipeline stage 02 — Execute CadQuery and build graph

**Purpose:** turn a normalized CadQuery program into the CAD graph that task
clues and answers can be checked against.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Sub-steps

| Step | Responsibility | Doc |
|---|---|---|
| `02a` | Extract static CadQuery structure without execution. | [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) |
| `02b` | Execute CadQuery and capture snapshots or a failure tombstone. | [`02b-execute-cadquery.md`](02b-execute-cadquery.md) |
| `02c` | Build graph entities, relations, measurements, and evidence. | [`02c-build-cad-graph.md`](02c-build-cad-graph.md) |

## Language and parallelism

- **Python:** `02a` static extraction and `02b` CadQuery execution.
- **Go:** `02c` graph construction.
- `02a`, `02b`, and `02c` are parallel per program; each program has independent
  input and output.
- `02b` uses a bounded process pool because CadQuery/OCP execution is memory
  heavy. Do not oversubscribe it.
- Parallel graph outputs are merged by `program_id`; graph construction does not
  mutate shared state.

## Why three steps

Static extraction is cheap and can succeed when execution fails. Execution is
expensive and cacheable. Graph assembly needs both. Evidence is part of graph
assembly, not a separate pipeline stage: a measurement without evidence is not a graph
measurement.

Failures are execution results, not a pipeline stage. The execution boundary returns
either snapshots or a failure tombstone.
