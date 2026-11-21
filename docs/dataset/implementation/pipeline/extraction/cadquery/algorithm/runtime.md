# CadQuery runtime extraction

**Parent:** [`extraction/README.md`](../../README.md).

This document defines how `02b` turns an accepted `CadQueryAstExtractionResult` into a
`CadQueryRuntimeExtractionResult`. It specifies the instrumentation ABI, runtime recorder,
capture rules, and failure boundary.

## Execution boundary

- Run one accepted program in a fresh child process forked from a worker that
  has already imported CadQuery and OCP. The child is a fresh address space; the
  interpreter start and the library import are amortized across programs. Never
  execute two programs in one child.
- The worker preloads CadQuery and OCP once, with `PYTHONHASHSEED=0` set before
  the preload. A forked child inherits the preloaded modules, and a program still
  cannot observe another program's CadQuery or OCP state.
- Apply 30 seconds wall clock and 2 GiB address space to the child by default.
  The wall clock starts when the child signals that the program is about to
  execute, not when the process is created; import time is worker startup, not
  execution time.
- Pin CadQuery, OCP, Python, and the extractor version in the environment record.
- Kill the child on timeout and record `timeout`.
- Record `memory` when the address-space limit is reached.
- Do not persist kernel handles, BRep objects, or raw shape files.

The child returns only the typed runtime records defined here. A crash or
uncaught exception becomes a failure tombstone. A worker that cannot preload its
libraries is a pipeline stage failure, not a per-program rejection.

## Parent/child protocol

The parent creates the per-program part directory as `<target>.tmp-<uuid>` and
passes its path to the child. The child writes the runtime tables from
[`../../artifacts.md`](../../artifacts.md) there and exits zero only after all
tables are closed. The parent reads nothing until the child exits, then validates
the status, schema, row counts, and hashes, and commits the directory with the
rename and directory fsync in
[`../../../../run-contract.md`](../../../../run-contract.md#41-write-rule). It
does not re-encode the tables. A non-zero exit without a failure table becomes an
`internal` failure; the parent keeps only the last 4 KiB of stderr for diagnosis
and never trusts it as a result.

The child must not write to stdout as a result channel. Diagnostic prints are
not part of the extraction contract and may be discarded.

## Instrumentation ABI

The CadQuery program AST extraction result supplies one rewrite descriptor per assignment. `02a` rewrites
each assignment without changing evaluation order.

A call assignment:

```text
wpN = <rhs>
```

becomes:

```text
wpN = __cadqa_record(
    op_id="op:<order:06d>",
    result_var="wpN",
    receiver_var="wp0" or None,
    selector_category="face" or "edge" or "vertex" or None,
    capture="state" | "workplane" | "selector" | "value" | "none",
    evaluate=lambda: <rhs>,
)
```

An alias assignment:

```text
result = wpN
result = wpN[0]
```

becomes:

```text
result = __cadqa_alias(
    alias_id="alias:<order:06d>",
    result_var="result",
    target_var="wpN" or None,
    evaluate=lambda: <rhs>,
)
```

The rewrite obeys these rules:

- `<rhs>` appears exactly once and is evaluated exactly once.
- The receiver and arguments are not separately evaluated. The recorder uses
  the `receiver_var` from the AST extraction result to look up the current runtime state; it does not
  capture argument values.
- Nested `cq.Plane`, `cq.Vector`, `cq.Edge`, `cq.Wire`, filter, and `list`
  expressions stay inside the `evaluate` callable.
- The instrumented text is generated with the pinned Python AST and is not a
  string substitution.
- A name used by an `evaluate` callable is the runtime value at the call point. The CadQuery program AST extraction result forbids
  rebinding, so closure timing is unambiguous.

`__cadqa_alias` propagates the target binding's state, CadQuery workplane, and selected
category. It creates no operation, state, CadQuery selector result, or effect.

## Capture classes

`capture` comes from the operation classification in the AST extraction result:

| Capture | Methods | Required result | Produces |
|---|---|---|---|
| `state` | solid, boolean, assembly, modifier, transform methods marked solid state producing | `Workplane` with a solid, or a solid `Shape` | Shape snapshot, entity table, topology, effect. |
| `workplane` | `Workplane`, `workplane`, `workplaneFromTagged`, `transformed` | `Workplane` | CadQuery workplane frame; no shape snapshot. |
| `selector` | `faces`, `edges`, `vertices`, `filter` | `Workplane` | CadQuery selector result; no shape snapshot. |
| `value` | `val`, `vals`, `all`, `first`, `findSolid`, `Length`, `list(vals())` | Any allowed value | Recorded result kind; no state. |
| `none` | sketch, path, `tag`, `toPending` | `Workplane` or path constructor | Binding propagation only. |

A solid state producing operation that returns no solid is a `non_solid_result`
failure. A failed kernel classification call is a `geometry_capture` failure. A CadQuery selector operation whose receiver has no current state is a
`missing_state` failure.

## Recorder state

The recorder maintains:

- `bindings`: variable name to `RuntimeBinding`;
- `states`: state ID to `ShapeSnapshot`;
- `entities`: state ID to entity table;
- `selectors`: CadQuery selector result ID to `CadQuerySelectorResult`;
- `frames`: CadQuery workplane ID to `WorkplaneFrameCapture`;
- `effects`: operation ID to `CadFeatureSolidStateEffectDelta`;
- `operations`: operation ID to `RecordedAssignment`.

`RuntimeBinding` carries:

| Field | Meaning |
|---|---|
| `result_kind` | CadQuery workplane, CadQuery workplane list, shape, shape list, list, scalar, plane, vector, edge, wire, or none. |
| `state_id` | Current containing solid state, or null. |
| `workplane_id` | Current CadQuery workplane, or null. |
| `selected_category` | Face, edge, vertex, or null. |

A binding is replaced only by its own assignment. Rebinding is rejected by
`02a`.

## Runtime classification

After `evaluate()` returns, classify the runtime value once:

| Value | `result_kind` |
|---|---|
| `cadquery.Workplane` | `workplane` |
| `cadquery.ShapeList` | `shape_list` |
| Python `list` when the AST operation is `all` | `workplane_list` |
| Python `list` otherwise | `list` |
| `int`, `float`, `bool`, `str` | `scalar` |
| `None` | `none` |
| `cadquery.Plane` | `plane` |
| `cadquery.Vector` | `vector` |
| `cadquery.Edge` | `edge` |
| `cadquery.Wire` | `wire` |
| any other `cadquery.Shape` subclass | `shape` |

An unrecognized value is a `result_kind` failure. The recorder does not guess
from the variable name or method name.

## State capture

For `capture = state`:

1. Obtain the shape:
   - `Workplane`: call `val()` once; null is a `non_solid_result` failure;
   - solid `Shape`: use it directly.
2. Require `len(shape.Solids()) >= 1`; otherwise fail with `non_solid_result`.
3. Compute `state_id = state:<operation_id>`.
4. Compute the entity table and shape hash using
   [`../../canonicalization.md`](../../canonicalization.md) and
   [`geometry-classification.md`](geometry-classification.md).
5. Build topology records for the state.
6. Capture the shape snapshot.

The Shape snapshot carries the fields in
[`../features/states.md`](../features/states.md), including `is_solid = true`, `is_valid`, volume,
bounding box, centroid, counts, and `entity_table_ref`.

The state is recorded after the assignment returns, using the returned value.
The recorder never re-executes the operation.

The final state is the last shape snapshot in operation order. If the program
produces no state, execution fails with `no_state`.

## CadQuery workplane capture

For `capture = workplane`:

- Require a `Workplane` result.
- Read `frame = result.plane`.
- Record `origin = frame.origin`, `x_direction = frame.xDir`,
  `normal = frame.zDir`.
- Record the `workplane_id` from the AST extraction result, operation ID, CadQuery workplane kind, named plane,
  and program span.

This is a measured frame, not a derivation from the CadQuery program. It is the frame used by
`02c` for `workplane_frame` measurements.

## CadQuery selector capture

For `capture = selector`:

1. Require a `Workplane` result.
2. Read `selected_values = result.vals()` once.
3. Require `state_id = bindings[receiver_var].state_id`; null is
   `missing_state`.
4. Require the CadQuery selector in the AST extraction result category to be `face`, `edge`, or `vertex`.
5. For each selected value, compute its canonical fingerprint and look up the
   entity ID in that state's entity table. A value with no matching entity is an
   `unmapped_entity` failure.
6. Record the selected entity IDs in canonical order.
7. Set `count = len(selected_entity_ids)`.

The CadQuery selector result carries `selector_id`, `selector_result_id`, `state_id`,
`selected_entity_ids`, and `source_span`. It is not a new state.

The result binding inherits the receiver's state and CadQuery workplane, and gains the
CadQuery selector category. A later `filter` uses that category.

## Accessor and value capture

`capture = value` records `result_kind` and the runtime value type. It does not
create a state, CadQuery workplane, CadQuery selector result, or graph
measurement. It inherits the receiver binding's state, CadQuery workplane, and
selected category, so an accessor does not lose the state it reads from. A
`list` produced by `list(vals())` is a Python list of shapes; it is not a shape
list.

`val` may return null; that is a successful `none` result. A later solid state producing
operation on that binding fails with `missing_shape`.

## Effects

For every `capture = state` operation:

- `before_state_id` is the receiver binding's state before the operation; null
  when the receiver has no state.
- `after_state_id` is the new state.
- `volume_change = after.volume - before.volume` when both states exist;
  otherwise null.
- `bbox_change` is the before/after bounding boxes when both exist; otherwise
  null.
- `topology_change` is the after minus before counts when both exist; otherwise
  null.
- `effect_id = effect:<operation_id>`.

A failed operation produces no effect. A solid state producing operation with a
receiver state but no after state is a failure; the recorder does not silently
drop the state.

## Entity tables

For each state:

- Enumerate `shape.Faces()`, `shape.Edges()`, and `shape.Vertices()`.
- Compute the canonical fingerprint for every entity.
- Derive `entity_id` and `fingerprint_sha256`.
- Reject the program if two entities in the same state and category have the
  same fingerprint.
- Sort rows in the canonical order from
  [`../../canonicalization.md`](../../canonicalization.md).

Entity fields and fingerprint inputs are defined in
[`../features/entities.md`](../features/entities.md). The entity table is the only basis for CadQuery selector
membership and CAD graph entities.

## Topology

For each state:

- For every face, emit `face_has_edge` for each face edge, and
  `face_has_vertex` is not emitted; edge-vertex is the atomic incidence.
- For every edge, emit `edge_has_vertex` for each endpoint.
- For every edge shared by two faces, emit one `face_adjacent_to_face` pair in
  canonical order.
- Emit `solid_has_face`, `solid_has_edge`, and `solid_has_vertex` from the state
  to every entity.

Every endpoint must exist in the same state's entity table. The record ID is the
canonical hash of `(state_id, relation_kind, from_entity_id, to_entity_id)`.
Rows are sorted by that tuple.

## Failure tombstone

`FailureTombstone` carries:

- `program_id`, `program_sha256`, `extractor_version`;
- `stage = 02b`;
- `operation_id` when the failure occurs after an assignment begins;
- `error_kind`: `timeout`, `memory`, `cadquery_exception`, `recorder`,
  `result_kind`, `non_solid_result`, `missing_state`, `missing_shape`,
  `unmapped_entity`, `fingerprint_collision`, `no_state`, or `internal`;
- `message`, `source_line`, and `source_span` when known;
- environment record and `cache_key`.

A failure contains no partial state list. `02c` never receives a failed
execution as a graph input.

## CadQuery program runtime extraction result identity

`runtime_extraction_result_sha256` is the canonical hash of the complete successful
result or failure tombstone, using
[`../../canonicalization.md`](../../canonicalization.md). The cache key includes:

- `program_sha256`;
- `ast_extraction_result_sha256`;
- extractor, AST extraction, runtime, and canonicalization versions;
- Python, CadQuery, and OCP versions;
- timeout and memory limit;
- execution environment identifier.

A change to any input produces a new cache entry.

## Cross-check with AST extraction

After execution, `02b` validates:

- every AST operation has exactly one recording;
- every recording has the expected operation ID, result variable, and method;
- no extra operation or alias was recorded;
- every solid state producing operation has a state, unless the failure is terminal;
- every CadQuery selector result references a state and an existing CadQuery selector in the AST extraction result;
- every selected entity ID exists in the state entity table;
- every effect references existing before/after states;
- the final state is the last state in operation order.

A mismatch is a validation failure, not a partial success.
