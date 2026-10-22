# Extraction validation

**Parent:** [`extraction/README.md`](README.md).

This document defines the accept/reject boundary for AST extraction, runtime
extraction, and their cross-check. A validation failure is terminal for the
program.

## AST validation

`02a` emits a `CadQueryAstExtractionResult` only when all checks pass:

| Area | Invariant |
|---|---|
| Module | Exactly one `import cadquery as cq`; no other statements except top-level assignments. |
| Assignments | One `Name` target per assignment; no rebinding; final target is `result`. |
| Calls | One top-level call per call assignment; no chained call; no starred arguments. |
| Names | Every receiver and input variable is defined earlier. |
| Methods | Every method is in the closed allowlist and has one classification. |
| Expressions | Every expression node is in the accepted subset. |
| IDs | All IDs are unique and match their documented format. |
| Order | `order` equals the zero-based assignment index. |
| References | Profiles, paths, selectors, and workplanes reference existing operations and records. |
| Classification | Every solid state producing method has `feature_kind` and `solid_kind`. |
| Selectors | Every CadQuery selector has a face, edge, or vertex category. |
| Workplanes | Every CadQuery workplane reference resolves; frame status is explicit, derived, or unknown. |
| Final state | The last assignment is `result`; it is a call or alias that can produce or copy a value. |

An AST rejection record carries:

- `program_id`, `program_sha256`, `extractor_version`;
- `stage = 02a`;
- `error_kind`: `syntax`, `import`, `module_shape`, `assignment_shape`,
  `unsupported_expression`, `unsupported_call`, `chained_call`, `unknown_method`,
  `unresolved_name`, `duplicate_target`, `missing_result`, `invalid_id`,
  `invalid_reference`, or `internal`;
- `message`, `source_line`, and `source_span` when known;
- `cache_key`.

An AST rejection emits no operations, aliases, workplanes, profiles, paths,
selectors, or diagnostics that consumers could mistake for a CadQuery program AST extraction result.

## Runtime validation

`02b` emits a `CadQueryRuntimeExtractionResult` only when all checks pass:

| Area | Invariant |
|---|---|
| AST extraction result | The CadQuery program AST extraction result is valid and its hash matches the instrumented program. |
| Recordings | Every AST operation has exactly one recording; no extra recordings exist. |
| Operation identity | Recorded operation ID, result variable, and method match the AST operation. |
| Result kind | Every runtime value classifies into the allowed `ResultKind`. |
| State capture | Every solid state producing operation yields one solid state. |
| Final state | A successful execution has exactly one final state: the last Shape snapshot in operation order. |
| Entity tables | Every state has one entity table; every entity ID is unique within its state. |
| Fingerprints | No two entities in one state and category share a fingerprint. |
| Selectors | Every CadQuery selector result references a CadQuery selector in the AST extraction result and an existing state. |
| CadQuery selector membership | Every selected entity ID exists in the referenced state's entity table; `count` equals the number of IDs. |
| Effects | Every effect references existing before/after states; null before is allowed only for the first state. |
| Workplanes | Every captured CadQuery workplane frame references an existing CadQuery workplane in the AST extraction result. |
| Ordering | All lists use the canonical order in [`canonicalization.md`](canonicalization.md). |

## Cross-pipeline stage validation

`02c` rejects the pair when:

- an AST operation has no recording;
- a recording has no AST operation;
- a state ID does not match its producing operation ID;
- a CadQuery selector result's `selector_id` does not match a CadQuery selector in the AST extraction result;
- a selected entity ID does not exist in the state entity table;
- a solid state producing operation's effect is missing;
- the final state differs from the last state in operation order;
- the CadQuery program AST extraction result hash or CadQuery program runtime extraction result hash does not match the artifact;
- a CAD topology entity ID hash does not match its fingerprint fields.

This is a rejection, not a partial graph. `02c` does not repair, interpolate, or
drop a subset of the records.

## Runtime error kinds

| Error kind | Cause |
|---|---|
| `timeout` | Child exceeded the wall-clock limit. |
| `memory` | Child hit the address-space limit. |
| `cadquery_exception` | CadQuery/OCP raised during execution. |
| `recorder` | The recorder itself failed or returned an invalid value. |
| `result_kind` | A runtime value did not classify into an allowed kind. |
| `non_solid_result` | A solid state producing operation returned no solid. |
| `missing_state` | A CadQuery selector or effect needs a receiver state that does not exist. |
| `missing_shape` | A later operation uses a null shape binding. |
| `unmapped_entity` | A selected value has no entity row in the current state. |
| `fingerprint_collision` | Two entities in one state and category have the same fingerprint. |
| `no_state` | A successful program produced no solid state. |
| `geometry_capture` | A required kernel classification or measurement call failed. |
| `internal` | An extractor bug or unexpected process failure. |

## Failure precedence

When several problems exist, report the earliest in this order:

1. syntax and module shape;
2. import;
3. assignment shape and chained calls;
4. unknown method and unsupported expression;
5. unresolved name and duplicate target;
6. missing final `result`;
7. AST reference and ID validation;
8. execution timeout or memory;
9. CadQuery exception;
10. recorder and capture failures;
11. runtime cross-check failures.

The reported program line and operation ID are the earliest known location for
the chosen failure.

## No partial outputs

- A failed `02a` writes a failure record, not a partial CadQuery program AST extraction result.
- A failed `02b` writes a failure tombstone, not partial states.
- A failed `02c` writes a failure record, not a partial graph.
- A failure is reusable as a cache result for the same key.

## P0/P1 exclusions

These are validation failures, not deferred features:

- `wires` and `solids` CadQuery selectors;
- `combineSolids`;
- chained CadQuery calls;
- arbitrary control flow;
- runtime argument capture;
- graph IDs or UUIDv4 in extraction records.
