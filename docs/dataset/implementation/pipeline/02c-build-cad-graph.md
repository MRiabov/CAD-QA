# 02c — Build CAD graph

**Parent:** [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).

**Purpose:** combine the CadQuery program AST extraction result and CadQuery
program runtime extraction result into the CAD graph.

This is the `02c` contract. The graph contract has a large fanout, so its
construction algorithm and persistence schema live in the
[`extraction/`](extraction/README.md) supporting docs.

## Input / output

- Input: `CadQueryAstExtractionResult`, `CadQueryRuntimeExtractionResult`, and
  `NormalizedProgram`.
- Output: `CadGraph`.

A failure tombstone from `02b` never enters graph assembly as a measurable state.
The `02c` contract emits one complete graph per program or rejects the pair; it does not
emit a partial graph.

## Supporting contracts

| Document | Responsibility |
|---|---|
| [`extraction/graph-construction.md`](extraction/graph-construction.md) | Deterministic mapping from extraction records to CAD graph entities, relations, and measurements. |
| [`extraction/graph-persistence.md`](extraction/graph-persistence.md) | CAD graph tables, IDs, attributes, enums, tolerances, and evidence payloads. |

Every task target, task clue operand, answer value, and piece of answer evidence
must resolve to a CAD graph element. A missing graph element rejects the task; it
is not guessed or softened.

Point probes are graph entities. They are copied from the runtime result and
attached to their solid state; a probe with no state is a graph defect.

## Language and parallelism

- **Go:** graph assembly and persistence.
- Programs are independent; graph assembly runs in parallel per program.
- Parallel outputs merge by `program_id`.
- Graph assembly does not mutate shared state.

## Failure boundary

The pair is rejected when extraction hashes do not match, a required reference is
missing, a relation or measurement endpoint does not resolve, an extraction
schema version is unknown, or a graph ID is not deterministic from its documented
components.

## Not here

AST extraction and CadQuery execution (`02a`/`02b`), task construction (`03`),
prompt rendering, and release validation.
