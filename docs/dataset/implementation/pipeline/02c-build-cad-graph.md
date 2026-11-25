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
| [`extraction/graph-persistence.md`](extraction/graph-persistence.md) | CAD graph tables, IDs, attributes, enums, tolerances, and evidence fields. |

Every task target, task clue reference, answer value, and piece of answer evidence
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
schema version is unknown, a graph ID is not deterministic from its documented
components, or a solid state exceeds the implementation-scope
`max_state_entities` constant.

A reference class over `max_anchor_class_size` does not reject the program: it
emits no dense pair rows, and a task clue that needs it is rejected at
construction (`DS-REQ-37`).

## Memory

Graph assembly holds one program at a time; the parallel degree is `--jobs`,
capped by `journal_shard_count` (`DS-ADR-12`), so peak memory is the per-program
working set times that degree. The representation is `DS-ADR-14`: columns and
dense handles inside the process, `uuid.UUID` only at the persistence boundary.

Two constants bound the rows a program can produce: `max_state_entities` and
`max_anchor_class_size`. Neither is a byte budget, and neither is a memory bound.
The per-program working set is measured once per implementation scope from the
selected pool, recorded with its distribution, and read by planning the way those
two constants are read. Until that measurement exists, `02c`'s memory requirement
is `[unverified — needs a measured run]`.

## Completeness

Rejection is not completeness. A graph that builds without a dangling endpoint can
still be missing a required node, relation, or measurement. The expected set, its
sources, and the per-program completeness report are defined in
[`extraction/graph-completeness.md`](extraction/graph-completeness.md).

## Not here

AST extraction and CadQuery execution (`02a`/`02b`), task construction (`03`),
prompt rendering, and release validation.

## Open questions

- **Q1.** Is `angle` between two edges or along a path tangent emitted at all?
  `graph-content.md` §4 declares both as P0 angle kinds, but no reference class
  names an edge: the three classes are face surface kind, face position, and face
  provenance. A dense pair kind is emitted only from a reference class, so no
  such row is produced. Either the P0 priority in that row is wrong, or an edge
  reference class is missing and an edge needs a stored direction, since
  `EdgeAttributes` carries only its curve kind and whether it is closed.
