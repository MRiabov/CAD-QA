# Extraction contracts

**Status:** draft, 2026-10-22. These docs define the fields extracted from a
CadQuery program before graph assembly. They do not define the graph tables; see
[`../02c-build-cad-graph.md`](../02c-build-cad-graph.md).

## Two sources

Extraction has two independent sources:

- **AST extraction** reads normalized program text and records what the program
  says.
- **CadQuery extraction** runs the program and records what the shape actually
  is.

Static fields describe intent. Runtime fields describe the produced shape.
Neither extraction path may guess the other's fields.

## Flow

```text
normalized program text
  → AST extraction
      → StaticCadQueryModel
      → instrumented program
  → CadQuery extraction
      → ExecutionResult
  → 02c graph assembly
```

AST extraction assigns `operation_id` values. The instrumented program and the
runtime records join on those IDs. Program-level IDs come from `01d`; graph-level
UUIDs are assigned only in `02c`.

## Field contract format

Each field doc uses:

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|

`Origin` is `AST`, `CadQuery`, or `both`. `Consumer` is another extraction doc or
`02c`.

## Rules

- A missing required field rejects the program; no field is inferred from a
  prompt or an answer.
- AST fields carry a one-based `source_line` and a complete span.
- Runtime fields carry the operation or state identity used by `02c`.
- P0/P1 programs have one CadQuery call per top-level assignment. Chained calls
  are P2.
- Static entity IDs are stable within a program. Runtime entity IDs are stable
  across reruns of the same program and environment.
- Numeric geometry belongs to runtime extraction and graph measurements, not AST
  extraction.

## Index

| Document | Fields |
|---|---|
| [`ast/operations.md`](ast/operations.md) | Static operation records, aliases, and operation IDs. |
| [`ast/expressions.md`](ast/expressions.md) | Expression trees and literal typing. |
| [`ast/workplanes.md`](ast/workplanes.md) | CadQuery workplane records. |
| [`ast/solids.md`](ast/solids.md) | Static solid feature, boolean, modifier, and transform records. |
| [`ast/profiles-paths.md`](ast/profiles-paths.md) | CadQuery profile and path records. |
| [`ast/selectors.md`](ast/selectors.md) | Static CadQuery selector records. |
| [`ast/instrumentation.md`](ast/instrumentation.md) | AST rewrite and runtime recorder contract. |
| [`cadquery/states.md`](cadquery/states.md) | Shape snapshots and state identity. |
| [`cadquery/solids.md`](cadquery/solids.md) | Entity tables and geometric fingerprints. |
| [`cadquery/topology.md`](cadquery/topology.md) | Incidence and adjacency records. |
| [`cadquery/selectors.md`](cadquery/selectors.md) | Evaluated CadQuery selector results. |
| [`cadquery/effects.md`](cadquery/effects.md) | Operation before/after effects. |
