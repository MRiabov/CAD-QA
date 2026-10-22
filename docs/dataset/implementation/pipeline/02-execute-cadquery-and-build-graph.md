# Pipeline stage 02 — Execute CadQuery and build graph

**Purpose:** turn a normalized CadQuery program into the CAD graph that task
clues and answers can be checked against.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

**Extraction field contracts:** [`extraction/README.md`](extraction/README.md).

## Sub-steps

| Step | Responsibility | Doc |
|---|---|---|
| `02a` | Extract CadQuery AST structure without execution. | [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) |
| `02b` | Execute CadQuery and capture snapshots or a failure tombstone. | [`02b-execute-cadquery.md`](02b-execute-cadquery.md) |
| `02c` | Build graph entities, relations, measurements, and CAD graph evidence. | [`02c-build-cad-graph.md`](02c-build-cad-graph.md) |

## Language and parallelism

- **Python:** `02a` AST extraction and `02b` CadQuery execution.
- **Go:** `02c` graph construction.
- Each program runs `02a → 02b → 02c` in order; different programs run in
  parallel. The three sub-steps are not independent parallel steps.
- `02b` uses a bounded process pool because CadQuery/OCP execution is memory
  heavy. Do not oversubscribe it.
- Parallel graph outputs are merged by `program_id`; graph construction does not
  mutate shared state.

## Why three steps

AST extraction is cheap and can succeed when execution fails. Execution is
expensive and cacheable. Graph assembly needs both. CAD graph evidence is part of
graph assembly, not a separate pipeline stage: a measurement without CAD graph
evidence is not a graph measurement.

Failures are CadQuery program runtime extraction results, not a pipeline stage. The execution boundary returns
either snapshots or a failure tombstone.
