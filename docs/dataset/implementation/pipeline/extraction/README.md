# Extraction contract

**Status:** complete for P0/P1, 2026-10-22.

This document is the entry point for the `02` extraction module. It defines the
input, the deterministic process, the outputs, the versions, and the failure
boundary. The algorithms that populate the fields live in `ast/algorithm/` and
`cadquery/algorithm/`. The per-item feature field contracts live in `ast/features/`
and `cadquery/features/`. Cross-cutting schemas, validation, and decisions stay at the
extraction root.

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

- `CadQueryAstExtractionResult`, written by `02a` without running CadQuery;
- `CadQueryRuntimeExtractionResult`, written by `02b`, either successful runtime
  captures or a failure tombstone.

`02c` joins them on `program_id` and `operation_id`. Artifact tables and hashes
are defined in [`artifacts.md`](artifacts.md).

## Process

```text
NormalizedProgram
  → 02a parse, validate, classify, assign AST IDs
      → CadQueryAstExtractionResult
      → instrumented program
  → 02b execute instrumented program in a child process
      → CadQueryRuntimeExtractionResult
  → 02c graph assembly
```

The process is fail-fast per program and deterministic:

1. Parse and validate the module.
2. Process top-level assignments in program order.
3. Build typed AST records and expression trees.
4. Validate the CadQuery program AST extraction result.
5. Rewrite the program for runtime recording.
6. Execute once in a child process.
7. Classify and capture runtime values.
8. Validate the CadQuery program runtime extraction result against the CadQuery program AST extraction result.
9. Emit a complete CadQuery program AST extraction result or one failure record.

No pipeline stage produces a partial CadQuery program AST extraction result, partial graph, or partial release row.

## Two extraction paths, no guessing

- **AST extraction** records what the program says. It never evaluates CadQuery
  and never invents geometry.
- **CadQuery extraction** records what the executed shape is. It never infers
  intent from method names when runtime evidence is required.

An AST field and a runtime field with similar names are different facts. The
CadQuery program AST extraction result may say `extrude`; only execution says whether the result was a
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

Do not use random UUIDv4 in extraction. Do not add a UUID layer to AST or
runtime records unless a value leaves program scope.

## Code names

Class and table names mirror the extraction terms:

- `CadQueryAstExtractionResult`, `AstOperation`, `AstWorkplane`, `AstProfile`,
  `AstPath`, `AstSelector`, `AstAlias`, `AstExpression`;
- `CadQueryRuntimeExtractionResult`, `CadQueryRuntimeExtractionSuccess`,
  `FailureTombstone`, `CadFeatureSolidStateEffectDelta`,
  `CadQuerySelectorResult`;
- `ast_*` and `runtime_*` artifact tables;
- `ast_extraction_result_sha256` and `runtime_extraction_result_sha256`.

`Static*`, `static_*`, and `Execution*` are not extraction code names.

## Versions

Every artifact carries:

- `extractor_version`: the implementation version;
- `ast_schema_version`, `runtime_schema_version`;
- `canonicalization_version`;
- pinned Python, CadQuery, OCP, and Ruff versions where relevant;
- `program_sha256` and `normalization_version` from `01d`.

The cache key includes the program hash, extractor and canonicalization
versions, CadQuery/OCP versions, execution limits, and the CadQuery program AST extraction result hash. A
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

A program either produces a complete CadQuery program AST extraction result or one failure record. Failure is
data, not an exception across the dataset pipeline boundary.

AST rejection happens before execution: syntax, import, statement shape,
unsupported call, unknown method, chained call, invalid expression, unresolved
name, duplicate target, missing final `result`, or invalid CadQuery program AST extraction result.

Runtime failures produce a tombstone: timeout, memory, CadQuery exception,
recorder failure, non-solid result for a solid state producing operation, CadQuery selector
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
- no wire or solid CadQuery selectors; shape accessors are limited to the method-signature contract;
- no `combineSolids`; it is not a CadQuery 2.7 method.

P2 control flow and chained calls are outside this contract. A P2 extension must
define its own AST and runtime rules rather than weakening these.

## Decisions

Accepted extraction decisions, rationale, and consequences are in
[`decisions.md`](decisions.md). The contract rules above remain normative; a
decision explains why the contract has that shape.

## Contract index

| Document | Responsibility |
|---|---|
| [`ast/algorithm/pipeline.md`](ast/algorithm/pipeline.md) | Deterministic AST passes, assignment rules, binding classification, and method classification. |
| [`ast/algorithm/allowlist.md`](ast/algorithm/allowlist.md) | Closed CadQuery method and constructor allowlist. |
| [`ast/algorithm/method-signatures.md`](ast/algorithm/method-signatures.md) | Closed receiver, argument, result, and state contract for every allowlisted call. |
| [`ast/features/operations.md`](ast/features/operations.md) | AST operation and alias fields. |
| [`ast/features/expressions.md`](ast/features/expressions.md) | Typed expression trees and literals. |
| [`ast/features/workplanes.md`](ast/features/workplanes.md) | CadQuery workplane records in the AST extraction result and frame derivation. |
| [`ast/features/profiles-paths.md`](ast/features/profiles-paths.md) | CadQuery profile and path records. |
| [`ast/algorithm/shape-derivation.md`](ast/algorithm/shape-derivation.md) | Point, segment, CadQuery shape, and path derivation rules. |
| [`ast/features/selectors.md`](ast/features/selectors.md) | CadQuery selector records in the AST extraction result and filter predicates. |
| [`ast/features/solids.md`](ast/features/solids.md) | AST feature classification. |
| [`ast/features/instrumentation.md`](ast/features/instrumentation.md) | Exact AST rewrite and recorder ABI. |
| [`cadquery/algorithm/runtime.md`](cadquery/algorithm/runtime.md) | Execution, state, CadQuery selector, entity, topology, effect, and frame capture. |
| [`cadquery/algorithm/geometry-classification.md`](cadquery/algorithm/geometry-classification.md) | Kernel API calls and surface, curve, centroid, and shape classification. |
| [`cadquery/features/states.md`](cadquery/features/states.md) | Shape snapshot fields and final-state rule. |
| [`cadquery/features/entities.md`](cadquery/features/entities.md) | Entity tables and fingerprints. |
| [`cadquery/features/topology.md`](cadquery/features/topology.md) | Incidence and adjacency records. |
| [`cadquery/features/selectors.md`](cadquery/features/selectors.md) | Runtime CadQuery selector results. |
| [`cadquery/features/effects.md`](cadquery/features/effects.md) | Before/after effects. |
| [`cadquery/features/evidence.md`](cadquery/features/evidence.md) | Extraction evidence references for effects, topology, and selectors. |
| [`canonicalization.md`](canonicalization.md) | Numbers, JSON, hashes, and ordering. |
| [`validation.md`](validation.md) | AST, runtime, and cross-pipeline stage invariants. |
| [`artifacts.md`](artifacts.md) | Logical tables, keys, and artifact identities. |
| [`ast-schema.md`](ast-schema.md) | AST extraction artifact columns, nested models, and CadQuery program AST extraction result hash. |
| [`runtime-schema.md`](runtime-schema.md) | Runtime artifact columns, nested models, and runtime model hash. |
| [`decisions.md`](decisions.md) | Accepted extraction decisions, rationale, and consequences. |
