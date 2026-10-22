# Extraction contract

**Status:** complete for P0/P1, 2026-10-22.

This document is the entry point for the `02` extraction module. It defines the
input, the deterministic process, the outputs, the versions, and the failure
boundary. Field definitions live in the linked documents; the algorithms that
populate them live in `ast/algorithm.md` and `cadquery/runtime.md`.

Extraction is a module inside pipeline stage `02`, not a standalone service. It
has no network API, no service database, and no independent trigger. Its outputs
are artifacts consumed by `02c` and `03`.

## Input

Extraction consumes one `NormalizedProgram` from `01d`:

- `program_id`, `program_sha256`, `normalization_version`;
- canonical program text;
- `cadevolve_program_family_id` and split metadata when present.

The program text is trusted build input. Extraction still uses a child process
for crash isolation and resource limits, but it is not a security sandbox.

## Output

Extraction produces two logical results:

- `StaticCadQueryModel`, written by `02a` without running CadQuery;
- `ExecutionResult`, written by `02b`, either successful runtime captures or a
  failure tombstone.

`02c` joins them on `program_id` and `operation_id`. Artifact tables and hashes
are defined in [`artifacts.md`](artifacts.md).

## Process

```text
NormalizedProgram
  → 02a parse, validate, classify, assign static IDs
      → StaticCadQueryModel
      → instrumented program
  → 02b execute instrumented program in a child process
      → ExecutionResult
  → 02c graph assembly
```

The process is fail-fast per program and deterministic:

1. Parse and validate the module.
2. Process top-level assignments in program order.
3. Build typed static records and expression trees.
4. Validate the static model.
5. Rewrite the program for runtime recording.
6. Execute once in a child process.
7. Classify and capture runtime values.
8. Validate the execution result against the static model.
9. Emit a complete static model or one failure record.

No pipeline stage produces a partial static model, partial graph, or partial release row.

## Two extraction paths, no guessing

- **AST extraction** records what the program says. It never evaluates CadQuery
  and never invents geometry.
- **CadQuery extraction** records what the executed shape is. It never infers
  intent from method names when runtime evidence is required.

A static field and a runtime field with similar names are different facts. The
static model may say `extrude`; only execution says whether the result was a
valid solid. Neither side fills the other's missing fields.

## Identity

Extraction IDs are program-scoped strings, not global IDs:

- `operation_id = op:<order:06d>`;
- `state_id = state:<operation_id>`;
- `selector_id = sel:<operation_id>:<ordinal>`;
- `selector_result_id = sres:<operation_id>:<ordinal>`;
- `workplane_id = <operation_id>:<ordinal>`;
- `profile_id = <operation_id>:<ordinal>`;
- `path_id = <operation_id>:<ordinal>`;
- `entity_id = ent:<sha256>`;
- `alias_id = alias:<order:06d>`.

`order` is the zero-based index of a top-level assignment. Call assignments get
an operation ID; name and subscript assignments get an alias ID. Operation IDs
are therefore stable but not necessarily contiguous.

Every persisted reference carries `program_id`. Extraction IDs are never global
join keys. `02c` derives deterministic UUIDv5 graph IDs from them and stores the
program-scoped strings as scope columns.

Do not use random UUIDv4 in extraction. Do not add a UUID layer to static or
runtime records unless a value leaves program scope.

## Versions

Every artifact carries:

- `extractor_version`: the implementation version;
- `static_schema_version`, `runtime_schema_version`;
- `canonicalization_version`;
- pinned Python, CadQuery, OCP, and Ruff versions where relevant;
- `program_sha256` and `normalization_version` from `01d`.

The cache key includes the program hash, extractor and canonicalization
versions, CadQuery/OCP versions, execution limits, and the static model hash. A
change to the parser, allowlist, classification, instrumentation, capture,
rounding, ordering, or hash input is a new `extractor_version` and a cache miss.

## Determinism

- Same program, versions, environment, and limits produce byte-identical
  extraction artifacts.
- All lists have a canonical order defined in
  [`canonicalization.md`](canonicalization.md).
- No wall-clock values, random IDs, unordered sets, or kernel handles are
  persisted.
- Parallel programs never share mutable state. Results merge by `program_id`.

## Failure model

A program either produces a complete static model or one failure record. Failure is
data, not an exception across the dataset pipeline boundary.

Static failures reject before execution: syntax, import, statement shape,
unsupported call, unknown method, chained call, invalid expression, unresolved
name, duplicate target, missing final `result`, or invalid static model.

Runtime failures produce a tombstone: timeout, memory, CadQuery exception,
recorder failure, non-solid result for a state-producing operation, CadQuery selector
failure, unmapped selected entity, missing runtime state, or fingerprint
collision.

A failed program never reaches graph assembly as a measurable state. A failure
record carries `program_id`, pipeline stage, reason, program line and operation ID when
known, environment, and cache key. The taxonomy and validation rules are in
[`validation.md`](validation.md).

## P0/P1 scope

P0/P1 accept only the flat CADEvolve-C subset:

- one `import cadquery as cq`;
- top-level assignments only;
- one CadQuery call per top-level assignment;
- no chained CadQuery calls;
- no control flow, functions, classes, comprehensions, or dynamic evaluation;
- selectors limited to faces, edges, and vertices;
- no wire or solid selectors/accessors until the graph models those entities;
- no `combineSolids`; it is not a CadQuery 2.7 method.

P2 control flow and chained calls are outside this contract. A P2 extension must
define its own static and runtime rules rather than weakening these.

## Design decisions

- **No standalone service.** The extraction service precedent does not apply:
  extraction is a deterministic module in `02`, with no independent API, tables,
  or trigger.
- **Strings inside extraction, UUIDs at graph storage.** This preserves readable
  provenance and avoids double hashing.
- **No kernel handles.** Persist only canonical fingerprints, IDs, and
  measurements.
- **No raw BRep requirement.** State identity is the canonical entity table plus
  shape hash; raw shapes are not a pipeline artifact.
- **Static frames may be incomplete.** Derived CadQuery workplane frames are measured at
  runtime; static extraction records only frames it can derive from the program.
- **No runtime argument capture.** The recorder records the result, receiver
  binding, and static operation identity. Argument values are not needed for
  graph assembly and are not captured.
- **Fail closed.** An unsupported construct rejects the program; there is no
  best-effort extraction.

## Contract index

| Document | Responsibility |
|---|---|
| [`ast/algorithm.md`](ast/algorithm.md) | Deterministic AST passes, assignment rules, binding classification, and method classification. |
| [`ast/operations.md`](ast/operations.md) | Static operation and alias fields. |
| [`ast/expressions.md`](ast/expressions.md) | Typed expression trees and literals. |
| [`ast/workplanes.md`](ast/workplanes.md) | Static CadQuery workplane records and frame derivation. |
| [`ast/profiles-paths.md`](ast/profiles-paths.md) | CadQuery profile and path records. |
| [`ast/selectors.md`](ast/selectors.md) | Static CadQuery selector records and filter predicates. |
| [`ast/solids.md`](ast/solids.md) | Static feature classification. |
| [`ast/instrumentation.md`](ast/instrumentation.md) | Exact AST rewrite and recorder ABI. |
| [`cadquery/runtime.md`](cadquery/runtime.md) | Execution, state, CadQuery selector, entity, topology, effect, and frame capture. |
| [`cadquery/states.md`](cadquery/states.md) | Shape snapshot fields and final-state rule. |
| [`cadquery/solids.md`](cadquery/solids.md) | Entity tables and fingerprints. |
| [`cadquery/topology.md`](cadquery/topology.md) | Incidence and adjacency records. |
| [`cadquery/selectors.md`](cadquery/selectors.md) | Runtime CadQuery selector results. |
| [`cadquery/effects.md`](cadquery/effects.md) | Before/after effects. |
| [`canonicalization.md`](canonicalization.md) | Numbers, JSON, hashes, and ordering. |
| [`validation.md`](validation.md) | Static, runtime, and cross-pipeline stage invariants. |
| [`artifacts.md`](artifacts.md) | Logical tables, keys, and artifact identities. |
