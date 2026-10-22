# AST operations

**Parent:** [`extraction/README.md`](../README.md).

These fields describe one top-level assignment in the normalized program. A
`StaticOperation` is a statement about the program, not a measured shape.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `operation_id` | string | AST | yes | `op:<order:06d>`. Stable within the program. | 02b, 02c |
| `order` | integer | AST | yes | Zero-based top-level assignment index. | 02c |
| `source_line` | integer | AST | yes | One-based line of the call. | failures, review |
| `source_span` | SourceSpan | AST | yes | Start and end line and column. | failures, review |
| `result_var` | string or null | AST | no | Assigned variable, if the assignment binds one. | 02b, 02c |
| `method` | string | AST | yes | Allowlisted CadQuery method or constructor. | 02c |
| `operation_kind` | OperationKind | AST | yes | `workplane`, `sketch`, `path`, `solid`, `cadquery_selector`, `boolean`, `assembly`, `modifier`, `transform`, or `accessor`. | 02c |
| `receiver` | StaticExpression or null | AST | no | Expression the method is called on. | 02b, 02c |
| `receiver_var` | string or null | AST | no | Variable name of the receiver, when it is a name. | 02b |
| `args` | list of StaticExpression | AST | yes | Positional arguments, unevaluated. | 02b, 02c |
| `kwargs` | map of string to StaticExpression | AST | yes | Keyword arguments, unevaluated. | 02b, 02c |
| `input_vars` | list of string | AST | yes | Variables read by the call, in first-use order. | 02b |
| `is_state_producing` | boolean | AST | yes | True for solid, boolean, assembly, modifier, and transform operations that can produce a solid state. | 02b |
| `alias_of` | string or null | AST | no | Result variable copied without a CadQuery call. | 02c |

## OperationKind

`workplane`, `sketch`, `path`, `solid`, `cadquery_selector`, `boolean`,
`assembly`, `modifier`, `transform`, `accessor`.

## Aliases

An assignment such as `result = wp10` has no CadQuery call. Record a
`StaticAlias`:

| Field | Field type | Origin | Required | Meaning |
|---|---|---|---|---|
| `alias_id` | string | AST | yes | `alias:<order:06d>`. |
| `order` | integer | AST | yes | Zero-based assignment index. |
| `source_line` | integer | AST | yes | One-based line. |
| `result_var` | string | AST | yes | New variable. |
| `target_var` | string | AST | yes | Existing variable or expression name. |
| `source_span` | SourceSpan | AST | yes | Span of the assignment. |

## Rules

- Operations are recorded in assignment order.
- `operation_id` is derived only from `order`; it does not encode method or result.
- Nested `cq.Plane` and `cq.Vector` calls are expressions, not operations.
- Unknown methods reject the whole program.
- P0/P1 reject chained CadQuery calls.
