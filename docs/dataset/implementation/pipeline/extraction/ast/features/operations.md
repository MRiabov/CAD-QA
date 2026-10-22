# AST operations

**Parent:** [`../algorithm/pipeline.md`](../algorithm/pipeline.md).

These fields describe one top-level call assignment. A `StaticOperation` is a
statement about the program, not a measured shape. The deterministic passes are
in [`pipeline.md`](../algorithm/pipeline.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `operation_id` | string | AST | yes | `op:<order:06d>`. | 02b, 02c |
| `order` | integer | AST | yes | Zero-based top-level assignment index. | 02c |
| `source_line` | integer | AST | yes | One-based start line of the call. | failures, review |
| `source_span` | SourceSpan | AST | yes | Call span; end exclusive. | failures, review |
| `result_var` | string | AST | yes | Assigned variable. | 02b, 02c |
| `method` | string | AST | yes | Allowlisted CadQuery method or qualified constructor name. | 02c |
| `operation_kind` | OperationKind | AST | yes | CadQuery workplane, sketch, path, solid, CadQuery selector, boolean, assembly, modifier, transform, or accessor. | 02c |
| `receiver` | StaticExpression or null | AST | no | Receiver expression; null for a plain-name call. | review |
| `receiver_var` | string or null | AST | no | Receiver name when the receiver is a `Name`. | 02b |
| `args` | list of StaticExpression | AST | yes | Positional arguments, unevaluated. | 02b, 02c |
| `kwargs` | map of string to StaticExpression | AST | yes | Keyword arguments, unevaluated. | 02b, 02c |
| `input_vars` | list of string | AST | yes | Variables read by the call, in first-use order. | 02b |
| `is_state_producing` | boolean | AST | yes | True only for the methods marked solid state producing in the algorithm. | 02b |
| `feature_kind` | FeatureKind or null | AST | no | Required when `is_state_producing` is true. | 02c |
| `solid_kind` | SolidKind or null | AST | no | Required when `is_state_producing` is true. | 02c |

`operation_id` is derived only from `order`; it does not encode method or result.
`cadevolve_program_family_id` and `split` are not AST operation fields; they
belong to the program record.

## Aliases

A top-level assignment without a CadQuery call records a `StaticAlias`:

| Field | Field type | Origin | Required | Meaning |
|---|---|---|---|---|
| `alias_id` | string | AST | yes | `alias:<order:06d>`. |
| `alias_kind` | `name` or `subscript` | AST | yes | Alias form. |
| `order` | integer | AST | yes | Zero-based assignment index. |
| `source_line` | integer | AST | yes | One-based start line. |
| `result_var` | string | AST | yes | New variable. |
| `target_var` | string or null | AST | no | Root target name for either alias form, when the target starts from a binding. |
| `target_expression` | StaticExpression or null | AST | no | Target expression for `alias_kind = subscript`. |
| `source_span` | SourceSpan | AST | yes | Assignment span; end exclusive. |

An alias copies the target binding's kind, CadQuery workplane ID, selected category, and
frame status. It creates no state, CadQuery selector result, effect, or graph operation.
The last assignment must be `result`; it may be a call or an alias.

## Rules

- Operations and aliases are recorded in assignment order.
- An alias consumes an assignment index but no operation ID.
- Nested `cq.Plane`, `cq.Vector`, and allowed constructor calls are expressions,
  not operations.
- Unknown methods, chained calls, and unsupported nested calls reject the whole
  program.
- A `StaticOperation` row exists only for a call assignment.
