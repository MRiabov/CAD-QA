# Extraction decisions

**Parent:** [`README.md`](README.md).

**Status:** accepted for P0/P1, 2026-10-22.

This document records why the extraction contract has its current shape. The
contract remains normative; a decision explains the choice and its consequence.
An accepted decision is not silently rewritten. A change adds a new decision and
marks the old one superseded.

## EX-1 — Extraction is a module, not a standalone service

**Decision:** Extraction is a deterministic module inside pipeline stage `02`.
It has no network API, service database, independent trigger, or deployment unit.

**Why:** The standalone feature-extraction service precedent applied to a
separate product with multiple consumers and its own lifecycle. Here the only
consumer is `02c`, inside the same pipeline stage. A service boundary would add
deployment, API, persistence, retry, and compatibility surfaces without a second
consumer.

**Consequence:** The contract owns input, algorithms, artifacts, versions, and
failures, but not service orchestration. Pipeline stage `02` owns execution and
artifact placement.

## EX-2 — Keep extraction IDs as strings; use UUIDv5 only in graph storage

**Decision:** `operation_id`, `state_id`, `entity_id`, `selector_id`,
`selector_result_id`, `workplane_id`, `profile_id`, `path_id`, and `alias_id`
remain program-scoped strings. `02c` derives graph UUIDs.

**Why:** The strings are readable in failures, review, and evidence, and they
carry enough identity when every row also carries `program_id`. UUIDs at the
extraction layer would add a second hash layer before the graph hash.

**Consequence:** Every persisted extraction reference carries `program_id`.
Extraction IDs are never global join keys. Random UUIDv4 is rejected because it
would break deterministic replay.

## EX-3 — P0/P1 use flat assignments and one CadQuery call per assignment

**Decision:** The accepted CadQuery program has module-level assignments only.
A call assignment has one top-level CadQuery call. Chained CadQuery calls are
rejected.

**Why:** The CADEvolve-C corpus is flat. A single call per assignment gives one
unambiguous `operation_id`, one program span, and one runtime result. Chained
calls would require assigning identity to intermediate receivers that never
appear in the CadQuery program.

**Consequence:** P2 may add chained calls only with a new identity and capture
contract. It must not weaken P0/P1.

## EX-4 — Fail closed

**Decision:** An unsupported module shape, method, expression, nested call, or
validation failure rejects the whole CadQuery program. There is no best-effort
or partial extraction.

**Why:** A partial CadQuery program AST extraction result or partial CadQuery program runtime extraction result is worse than a
failure record because downstream stages cannot tell which fields are missing by
design and which are missing by accident.

**Consequence:** A failure emits no operations, aliases, CadQuery workplanes,
CadQuery profiles, paths, CadQuery selectors, states, or entities that a consumer
could mistake for a CadQuery program AST extraction result.

## EX-5 — Reject `combineSolids`

**Decision:** `combineSolids` is not in the P0/P1 allowlist and is not rewritten
as `combine`.

**Why:** It is observed in CADEvolve-C programs but is not a CadQuery 2.7 method.
Silently rewriting it would change the CadQuery program.

**Consequence:** Programs that call `combineSolids` fail AST extraction. The
local cache contains 701 CADEvolve-C-core, 41 ABC-C, and 3 ShapeNet-C affected
programs.

## EX-6 — Reject wire and solid CadQuery selectors

**Decision:** P0/P1 accept `faces`, `edges`, and `vertices` CadQuery selectors
only. `wires` and `solids` are rejected. `wire`, `Edges`, and `Solids` are
accessor/path forms governed by the method-signature contract, not selectors.

**Why:** `02c` has no wire or solid entity category. Recording a selected count
without stable membership would be a partial CadQuery selector result and would
break the graph invariant that selected membership maps to entity nodes.

**Consequence:** The unique affected set is 1,208 of 60,896 CADEvolve-C-core,
5,248 of 763,062 ABC-C, and 423 of 105,200 ShapeNet-C programs: 6,879 of the
929,158 C programs (0.74%). The P pool is unaffected because P0/P1 uses
CADEvolve-C only. Supporting wire/solid selection later requires new graph entity
categories, fingerprints, topology records, and task bindings.

## EX-7 — AST workplane frames are intent; runtime frames are measurements

**Decision:** AST extraction records a CadQuery workplane frame only when it
can derive it from the CadQuery program. Otherwise `frame_status = unknown`.
`02b` always measures the executed frame.

**Why:** `workplaneFromTagged`, `transformed`, and face-derived workplanes need
runtime state. Guessing their frame in AST extraction would contaminate
intent with an unverified measurement.

**Consequence:** `origin`, `x_direction`, and `normal` are nullable in the AST extraction result
record. `02c` uses the measured workplane frame for graph measurements.

## EX-8 — Capture the result, not the arguments

**Decision:** Instrumentation passes the operation ID, result variable, receiver
variable, CadQuery selector category, capture class, and an `evaluate` callable. It does not
pass evaluated receiver or argument values.

**Why:** The graph needs the produced state, CadQuery selector membership, and before/after
effect. Argument values are not required, and evaluating them separately would
risk double evaluation or require rewriting every argument expression.

**Consequence:** The `evaluate` callable is evaluated exactly once. The recorder uses the AST extraction result's
`receiver_var` to look up the current runtime state. A `RecordedAssignment` has no
`receiver_value` or `argument_values` field.

## EX-9 — Do not persist kernel handles or raw BRep

**Decision:** Persist stable entity IDs, canonical fingerprints, shape hashes,
measurements, and topology. Do not persist OCP/OCCT handles, raw BRep, or raw
shape files.

**Why:** Kernel handles are process-local and unstable. Raw BRep would add a
large mutable payload that the graph does not need. Canonical fingerprints give
deterministic identity and inspection evidence.

**Consequence:** A state is identified by its entity table and `shape_hash`.
Debugging exports are separate, non-pipeline artifacts.

## EX-10 — Aliases copy bindings; rebinding is rejected

**Decision:** `name = other_name` and `name = other_name[expr]` are aliases, not
CadQuery operations. Rebinding any target name is rejected.

**Why:** Aliasing must preserve the runtime state, CadQuery workplane, and
selected category without creating a fake operation. Rebinding makes receiver
history and closure timing ambiguous.

**Consequence:** An alias consumes an assignment index but no operation ID. It
creates no state, CadQuery selector result, effect, or graph operation.

## EX-11 — Only face, edge, and vertex membership is graph-addressable

**Decision:** Runtime selector results map to state entity rows only for faces,
edges, and vertices.

**Why:** Those are the entity categories in the CAD graph. A selected wire or
solid has no CAD graph entity to receive a `selected_by` relation.

**Consequence:** The runtime rejects a CadQuery selector category outside this set during
AST extraction, before execution. A selected value that has no matching
entity row is an `unmapped_entity` failure.

## EX-12 — Canonicalization is explicit and versioned

**Decision:** Floats round to 9 decimal places with round-half-to-even, `-0.0`
normalizes to `0.0`, JSON has sorted keys and no spaces, hashes are SHA-256 with
fixed prefixes, and every list has a documented order.

**Why:** Kernel enumeration order, Python float `repr`, and dictionary order are
not stable enough for byte-identical replay or cache identity.

**Consequence:** A change to precision, rounding, JSON encoding, fingerprint
fields, hash prefixes, or ordering changes `canonicalization_version` and
invalidates extraction caches and graph artifacts.

## EX-13 — Failure is data; no partial artifacts

**Decision:** AST rejection produces an AST rejection record. Runtime failure
produces a failure tombstone. Neither produces a partial CadQuery program AST extraction result, partial
CadQuery program runtime extraction result, or partial graph.

**Why:** Downstream stages must distinguish rejected CadQuery programs from
successful ones without guessing. Failure reuse also needs an explicit cache key.

**Consequence:** `02c` never receives a failed execution as a measurable state.
The release-level failures table copies these records; it does not reconstruct
them.

## EX-14 — Child process is for isolation and limits, not security

**Decision:** `02b` runs one CadQuery program per child process with a timeout and
address-space limit. It is not a security sandbox.

**Why:** CADEvolve programs are trusted build input. The child process protects
the dataset pipeline from crashes, runaway memory, and CadQuery global state; it does not
pretend to contain hostile code.

**Consequence:** No network or filesystem sandbox is part of the extraction
contract. Changing the timeout, memory limit, or environment changes the cache
key.

## EX-15 — P2 is outside this contract

**Decision:** Arbitrary Python control flow, chained CadQuery calls, near-miss
choices, and P-tier expansion are not P0/P1 extraction features.

**Why:** Each changes AST identity, runtime capture, or task construction in a
way that would weaken the P0/P1 invariants if added implicitly.

**Consequence:** P2 must add its own decisions and algorithms. The P0/P1 contract
does not reserve partial P2 fields or accept P2 programs as best effort.

## EX-16 — Method names are not enough

**Decision:** Every allowlisted call has a receiver, argument, result, and state
contract in [`ast/algorithm/method-signatures.md`](ast/algorithm/method-signatures.md). `fuse` is a
qualified shape method, `Edges` and `Solids` are shape accessors, `wire` returns
a CadQuery workplane, and `newObject`/`add` are not solid state producing.

**Why:** CadQuery exposes the same method name on different receivers, and the
CADEvolve-C programs use shape-level accessors after `val()`. Method-name-only
classification would accept calls that cannot exist or would assign the wrong
result binding.

**Consequence:** Receiver mismatch, unknown keyword arguments, and wrong arity
reject the program before execution. `newObject` and `add` do not create a solid
state; `combine` does.

## EX-17 — Kernel classification is explicit

**Decision:** Face surface and edge curve categories, centroids, bounding boxes,
counts, validity, and solid detection use the exact calls and closed mappings in
[`cadquery/algorithm/geometry-classification.md`](cadquery/algorithm/geometry-classification.md).

**Why:** CadQuery and OCP expose several plausible calls. A guessed mapping would
make extraction artifacts depend on an implementation choice rather than a
contract.

**Consequence:** A failed required kernel call is a `geometry_capture` failure.
Do not substitute zero, null, or a guessed category.

## EX-18 — Evidence is captured, not reconstructed

**Decision:** Effects, topology, and CadQuery selector results carry typed
evidence references at capture time, defined in
[`cadquery/features/evidence.md`](cadquery/features/evidence.md).

**Why:** A measurement without a reproducible state, entity, operation, span,
kernel call, or selector reference is not sufficient for answer evidence.

**Consequence:** An unresolved evidence reference rejects `02c`; it is not
dropped or repaired.

## EX-19 — Extraction-to-graph mapping is a separate algorithm

**Decision:** `02c` uses the CAD graph entity, relation, and measurement mapping in
[`../02c-extraction-to-graph.md`](../02c-extraction-to-graph.md).

**Why:** The extraction contract owns extraction IDs and records. The graph
contract owns UUIDs, CAD graph entity types, relation categories, and measurements.
Keeping the mapping separate prevents either contract from silently redefining
the other.

**Consequence:** Every extraction record has a defined graph destination, and a
missing endpoint or measurement rejects the graph.

## EX-20 — AST extraction artifacts are typed

**Decision:** The CadQuery program AST extraction result uses the table columns and nested models in
[`ast-schema.md`](ast-schema.md), not JSON strings on the bulk data path.

**Why:** Go and Python exchange Parquet tables. A typed schema makes joins,
validation, and hash inputs unambiguous.

**Consequence:** Expression trees are nested structs, and a schema change bumps
`ast_schema_version`.

## EX-21 — Runtime artifacts are typed

**Decision:** The runtime model uses the table columns and nested models in
[`runtime-schema.md`](runtime-schema.md).

**Why:** `02c` consumes runtime tables across the Python/Go boundary. A typed
schema makes state, entity, evidence, and hash inputs unambiguous.

**Consequence:** Runtime rows are Parquet tables, not JSON payloads. A schema
change bumps `runtime_schema_version`.

## EX-22 — Code names mirror extraction terms

**Decision:** Class names, table prefixes, and hash fields use the approved
extraction terms: `CadQueryAstExtractionResult`, the `Ast*` record types,
`CadQueryRuntimeExtractionResult`, `CadQueryRuntimeExtractionSuccess`,
`FailureTombstone`, `CadFeatureSolidStateEffectDelta`,
`CadQuerySelectorResult`, `ast_*` and `runtime_*` tables,
`ast_extraction_result_sha256`, and `runtime_extraction_result_sha256`.

**Why:** A greenfield contract should not teach an implementation a synonym for a
term the glossary defines. The old `Static*` and `Execution*` names described the
implementation technique, not the extraction result.

**Consequence:** `Static*`, `static_*`, and `Execution*` are not code names in the
extraction contract. A later code-name change is a schema or implementation
change, not a terminology rewrite.

## Superseded decisions

None.
