# AST CadQuery selectors

**Parent:** [`extraction/README.md`](../README.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `selector_id` | string | AST | yes | `sel:<operation_id>:<ordinal>`. | 02b, 02c |
| `operation_id` | string | AST | yes | Evaluating operation. | 02b, 02c |
| `selector_kind` | SelectorKind | AST | yes | String, call, or filter. | 02c |
| `selector_expression` | string or null | AST | no | CadQuery selector string, such as `>Z` or `|Y`. | 02b, 02c |
| `receiver_var` | string | AST | yes | Shape or CadQuery workplane variable the CadQuery selector runs on. | 02b |
| `filter_predicate` | FilterPredicate or null | AST | no | Narrow `filter` lambda fields. | 02b |
| `source_span` | SourceSpan | AST | yes | Span of the CadQuery selector call. | review |

## FilterPredicate

| Field | Field type | Origin | Required | Meaning |
|---|---|---|---|---|
| `attribute` | string | AST | yes | Always `Length` in P0/P1. |
| `comparator` | `lt` or `le` | AST | yes | Comparison operator. |
| `threshold` | double | AST | yes | Numeric threshold. |

## Mapping

- Lowercase `faces`, `edges`, `vertices`, `wires`, `solids` → string or implicit
  CadQuery selector.
- `filter` → filter predicate plus the receiver CadQuery selector.
- `cq.NearestToPointSelector([x, y, z])` → call selector.

Static extraction records the expression. `02b` evaluates it at the call point.
Zero matches is a valid result. An exception rejects the program.
