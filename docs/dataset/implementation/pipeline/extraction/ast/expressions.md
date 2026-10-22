# AST expressions

**Parent:** [`extraction/README.md`](../README.md).

`StaticExpression` is a typed, unevaluated expression tree.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `expression_kind` | ExpressionKind | AST | yes | Literal, name, attribute, subscript, call, list, tuple, dict, or lambda. | 02b, 02c |
| `source_span` | SourceSpan | AST | yes | Exact span of the expression. | review |
| `literal_value` | typed value or null | AST | no | Integer, double, string, boolean, or null for a literal. | 02b |
| `name` | string or null | AST | no | Identifier for a name expression. | 02b |
| `value_expression` | StaticExpression or null | AST | no | Base of an attribute or subscript. | 02b |
| `attribute` | string or null | AST | no | Attribute name. | 02b |
| `subscript` | StaticExpression or null | AST | no | Subscript expression. | 02b |
| `callee` | StaticExpression or null | AST | no | Call target. | 02b |
| `args` | list of StaticExpression | AST | no | Positional call arguments. | 02b |
| `kwargs` | map of string to StaticExpression | AST | no | Keyword call arguments. | 02b |
| `elements` | list of StaticExpression | AST | no | List or tuple elements. | 02b |
| `entries` | list of DictEntry | AST | no | Dict keys and values. | 02b |
| `lambda_body` | StaticExpression or null | AST | no | Narrow filter predicate body only. | 02b |

## Typing rules

- Integer literals are `int64`; float literals are `double`; strings are UTF-8;
  booleans are `bool`; `None` is null.
- Negative numeric literals are unary operations over a positive literal.
- A call keeps the callee expression; it does not evaluate it.
- `cq.Plane` and `cq.Vector` remain calls inside the tree.
- A lambda is accepted only as the `filter` predicate:
  `lambda e: e.Length() < number` or `<=`.
- No `eval`, `exec`, dynamic import, or function definition is allowed.
