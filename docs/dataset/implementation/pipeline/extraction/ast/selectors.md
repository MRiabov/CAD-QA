# AST CadQuery selectors

**Parent:** [`extraction/README.md`](../README.md).

P0/P1 selectors are limited to faces, edges, and vertices. Wire and solid
selectors have no graph entity category and reject the program.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `selector_id` | string | AST | yes | `sel:<operation_id>:<ordinal>`. | 02b, 02c |
| `operation_id` | string | AST | yes | Evaluating operation. | 02b, 02c |
| `selector_kind` | SelectorKind | AST | yes | `string`, `call`, `filter`, or `implicit`. | 02c |
| `selected_entity_category` | `face`, `edge`, or `vertex` | AST | yes | Category the CadQuery selector produces. | 02b, 02c |
| `selector_expression` | string or null | AST | no | CadQuery selector string such as `>Z` or `|Y`. | 02b, 02c |
| `receiver_var` | string | AST | yes | CadQuery workplane or shape binding the CadQuery selector runs on. | 02b |
| `filter_predicate` | FilterPredicate or null | AST | no | Narrow `filter` lambda fields. | 02b |
| `source_span` | SourceSpan | AST | yes | CadQuery selector call span. | review |

## FilterPredicate

| Field | Field type | Origin | Required | Meaning |
|---|---|---|---|---|
| `attribute` | string | AST | yes | Always `Length` in P0/P1. |
| `comparator` | `lt` or `le` | AST | yes | Comparison operator. |
| `threshold` | double | AST | yes | Numeric threshold. |

## Mapping

- `faces`, `edges`, `vertices`:
  - no arguments → `selector_kind = implicit`;
  - string argument → `selector_kind = string`;
  - `cq.NearestToPointSelector(...)` argument → `selector_kind = call`.
- `filter` → `selector_kind = filter`. The receiver binding must already carry
  a face, edge, or vertex category; the result inherits it.
- `wires`, `solids`, and their accessors are rejected in P0/P1.

The CadQuery selector ID ordinal is zero for every P0/P1 operation. A later operation
with more than one CadQuery selector numbers them in program order.

Static extraction records the expression and category. `02b` evaluates at the
call point. Zero matches is a valid result. An exception rejects the program.
