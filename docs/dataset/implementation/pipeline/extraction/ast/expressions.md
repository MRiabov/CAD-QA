# AST expressions

**Parent:** [`extraction/README.md`](../README.md).

`StaticExpression` is a typed, unevaluated expression tree. Its accepted forms
and nesting rules are defined in [`algorithm.md`](algorithm.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `expression_kind` | ExpressionKind | AST | yes | Literal, name, attribute, subscript, call, list, tuple, dict, unary, or lambda. | 02b, 02c |
| `source_span` | SourceSpan | AST | yes | Exact span; end exclusive. | review, failures |
| `literal_value` | typed value or null | AST | no | Integer, double, string, boolean, or null. | 02b |
| `name` | string or null | AST | no | Identifier for a name. | 02b |
| `value_expression` | StaticExpression or null | AST | no | Base of an attribute or subscript. | 02b |
| `attribute` | string or null | AST | no | Attribute name. | 02b |
| `subscript` | StaticExpression or null | AST | no | Subscript expression. | 02b |
| `callee` | StaticExpression or null | AST | no | Call target. | 02b |
| `args` | list of StaticExpression | AST | yes | Positional call arguments; empty for non-calls. | 02b |
| `kwargs` | map of string to StaticExpression | AST | yes | Keyword call arguments; empty for non-calls. | 02b |
| `elements` | list of StaticExpression | AST | yes | List or tuple elements; empty otherwise. | 02b |
| `entries` | list of DictEntry | AST | yes | Dict keys and values; empty otherwise. | 02b |
| `operator` | `neg` or `pos` or null | AST | no | Unary operator. | 02b |
| `operand` | StaticExpression or null | AST | no | Unary operand. | 02b |
| `lambda_parameter` | string or null | AST | no | Filter predicate parameter; always `e`. | 02b |
| `lambda_body` | StaticExpression or null | AST | no | Filter predicate body. | 02b |

`DictEntry` has `key` and `value` `StaticExpression` fields.

## ExpressionKind

`literal`, `name`, `attribute`, `subscript`, `call`, `list`, `tuple`, `dict`,
`unary`, `lambda`.

## Typing rules

- Integer literals are `int64`; float literals are `double`; strings are UTF-8;
  booleans are `bool`; `None` is null.
- Negative and positive numeric literals are `unary` nodes over a numeric
  literal or expression. `-0.0` normalizes to `0.0` in canonical output.
- A call keeps the callee expression; it does not evaluate it.
- `cq.Plane` and `cq.Vector` remain calls inside the tree.
- A lambda is accepted only as the narrow `filter` predicate:
  `lambda e: e.Length() < number` or `<=`.
- `list(vals())` is special-cased by the operation classification; it is not a
  general call form.
- No `eval`, `exec`, dynamic import, function definition, comprehension, set,
  starred argument, or `**kwargs` is allowed.
