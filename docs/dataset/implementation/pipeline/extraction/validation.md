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

An AST rejection is a [`failure record`](../../failure-record.md) with the
subject program, `pipeline_stage` `02a_extract_cadquery_ast`, and a
`reason_code` from this closed set. The row carries the reason's disposition. It
sets `program_line` and `program_span` when known.

| Reason | Disposition | Meaning |
|---|---|---|
| `syntax` | `corpus_defect` | The text does not parse as Python. |
| `import` | `by_design` | The program does not carry exactly one `import cadquery as cq`. |
| `module_shape` | `by_design` | A statement other than a top-level assignment appears. |
| `assignment_shape` | `by_design` | A target, starred argument, or call form the contract rejects. |
| `unsupported_expression` | `by_design` | A valid expression form outside the accepted subset. |
| `unsupported_call` | `by_design` | A valid call outside the accepted subset. |
| `chained_call` | `by_design` | More than one CadQuery call in one assignment. |
| `unknown_method` | `corpus_defect` | A method not in the CadQuery vocabulary. |
| `unresolved_name` | `corpus_defect` | A receiver or input variable is not defined earlier. |
| `duplicate_target` | `by_design` | A target is rebound. |
| `missing_result` | `by_design` | The final assignment is not `result`. |
| `invalid_id` | `extractor_gap` | An ID the extractor assigns is duplicated or malformed. |
| `invalid_reference` | `extractor_gap` | An extractor record references a record the extractor did not emit. |
| `internal` | `extractor_gap` | The extractor raised or failed unexpectedly. |

`syntax`, `unresolved_name`, and `unknown_method` reject a program that is not
valid Python or not valid CadQuery. `unsupported_expression`, `unsupported_call`,
and `chained_call` are the declared-scope exclusions: the input is valid at a
wider scope and the contract intends the rejection. The remaining program-shape
reasons reject a valid Python program that does not follow the contract's module
or assignment shape, which the contract also intends at the declared scope. The
last three reject the extractor's own output or behavior. A known CadQuery method
excluded by scope is `unsupported_call`, not `unknown_method`.

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

Every cross-check reason is `extractor_gap`: both inputs already passed their
own validation, so a failed cross-check or graph assembly invariant is a
generator defect, not a property of the corpus.

This is a rejection, not a partial graph. `02c` does not repair, interpolate, or
drop a subset of the records.

## Runtime error kinds

A runtime rejection is a [`failure record`](../../failure-record.md) with the
subject program, `pipeline_stage` `02b_execute_cadquery`, and an `error_kind`
from this closed set. The row carries the error kind's disposition.

| Error kind | Disposition | Cause |
|---|---|---|
| `timeout` | `corpus_defect` | Child exceeded the wall-clock limit. |
| `memory` | `corpus_defect` | Child hit the address-space limit. |
| `cadquery_exception` | `corpus_defect` | CadQuery/OCP raised during execution. |
| `recorder` | `extractor_gap` | The recorder itself failed or returned an invalid value. |
| `result_kind` | `corpus_defect` | A runtime value did not classify into an allowed kind. |
| `non_solid_result` | `corpus_defect` | A solid state producing operation returned no solid. |
| `missing_state` | `extractor_gap` | A CadQuery selector or effect needs a receiver state that does not exist. |
| `missing_shape` | `corpus_defect` | A later operation uses a null shape binding. |
| `unmapped_entity` | `extractor_gap` | A selected value has no entity row in the current state. |
| `fingerprint_collision` | `extractor_gap` | Two entities in one state and category have the same fingerprint. |
| `no_state` | `corpus_defect` | A successful program produced no solid state. |
| `geometry_capture` | `corpus_defect` | A required kernel classification or measurement call failed. |
| `internal` | `extractor_gap` | An extractor bug or unexpected process failure. |

A kernel failure is a property of the program's geometry, so `cadquery_exception`
and `geometry_capture` are `corpus_defect`. A capture, bookkeeping, or identity
failure is `extractor_gap`.

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

The disposition of a rejection caused by one of these exclusions follows the
reason table: a valid construct excluded by scope is `by_design`, while
`combineSolids` is `corpus_defect` because it is not a CadQuery 2.7 method
(`EX-5`), and a graph ID or UUIDv4 in an extraction record is `extractor_gap`
because the record must not carry one.

## The must-extract capability set

The P0 exclusions above say what a program may not contain. This section says
what the accepted set must carry: a capability the contract declares and no
accepted graph realizes is a loss, not a scope decision.

A **must-extract capability cell** is one graph row identity the extraction
contract declares at P0. It is written in the same shape the
[completeness report](graph-completeness.md#8-report) proves it with, so the
declaration and the observation are one identity:

| Cell kind | Cell identity | Example |
|---|---|---|
| Entity | `entity:<node_type>` | `entity:point_probe` |
| Relation | `relation:<relation_type>@<from_node_type>-><to_node_type>` | `relation:has_point_probe@solid_state->point_probe` |
| Measurement | `measurement:<measurement_type>@<subject_node_type>` | `measurement:probe_point@point_probe` |

`MustExtractCapability` is this closed set. It is the P0 subset of the entity,
relation, and measurement vocabularies in
[`graph-completeness.md` §3](graph-completeness.md#3-cad-graph-entity-completeness),
[§4](graph-completeness.md#4-relation-completeness), and
[§5](graph-completeness.md#5-measurement-completeness), with the scope from
[`graph-content.md`](../../../requirements/graph-content.md). A relation cell
names its two endpoint kinds because `creates` and `uses` each have several; a
measurement cell names its subject, and `pair` is the subject of a pair
measurement.

Entity cells:

- `entity:cadquery_program`, `entity:operation`, `entity:feature`,
  `entity:solid_state`, `entity:face`, `entity:edge`, `entity:vertex`,
  `entity:cadquery_profile`, `entity:cadquery_workplane`, `entity:region`,
  `entity:point_probe`.

Relation cells:

- `relation:before@operation->operation`,
  `relation:after@operation->operation`,
  `relation:creates@operation->feature`,
  `relation:creates@operation->solid_state`,
  `relation:uses@feature->cadquery_profile`,
  `relation:uses@feature->cadquery_workplane`,
  `relation:derived_from@cadquery_profile->cadquery_workplane`,
  `relation:has_face@solid_state->face`,
  `relation:has_edge@face->edge`,
  `relation:has_vertex@edge->vertex`,
  `relation:adjacent_to@face->face`,
  `relation:has_point_probe@solid_state->point_probe`,
  `relation:adds_material@feature->region`,
  `relation:removes_material@feature->region`,
  `relation:part_of@region->feature`.

Measurement cells:

- `measurement:volume@solid_state`, `measurement:volume@region`,
  `measurement:area@face`, `measurement:area@cadquery_profile`,
  `measurement:area@region`, `measurement:bounding_box@solid_state`,
  `measurement:bounding_box@face`, `measurement:bounding_box@edge`,
  `measurement:bounding_box@region`,
  `measurement:centroid@solid_state`, `measurement:centroid@face`,
  `measurement:centroid@edge`, `measurement:centroid@vertex`,
  `measurement:centroid@region`, `measurement:length@edge`,
  `measurement:face_count@solid_state`, `measurement:edge_count@solid_state`,
  `measurement:vertex_count@solid_state`, `measurement:edge_count@face`,
  `measurement:vertex_count@face`, `measurement:probe_point@point_probe`,
  `measurement:distance_to_face_surface@point_probe`,
  `measurement:volume_change@operation`,
  `measurement:topology_change@operation`, `measurement:distance@pair`,
  `measurement:angle@pair`.

A P1 or P2 vocabulary row is not a cell. A release may still realize one, and a
realized P1 cell is not an error: coverage compares the declared set with the
declared cells that were realized, so a row outside the set cannot appear as an
unexpected value.

### Coverage

A declared cell is **covered** when at least one accepted program's
`GraphCompletenessReport` carries that cell with `actual_count > 0`. A declared
cell with no coverage over the accepted set is a miss of the
`extraction_capability_coverage` release check
([`release-checks.md`](../05-validate-and-export-release/release-checks.md#extraction-capability-coverage)),
which blocks the export until the gap is fixed or the owner accepts the miss.

Coverage is a release gate, not a rejection rule. It rejects no program and
writes no failure row. It also does not read the capability census: the census is
a function of the graphs a run accepted, so a capability missing from every graph
is missing from the census too, and a quota plan or support table built on it
reads the capability as absent rather than as a miss. The contract list is the
independent side.

The set is written above and implemented as data, not parsed from these tables at
run time. A change to a P0 row of the completeness tables changes this list in
the same change; an unlisted P0 capability is a contract gap, not a silent
absence.
