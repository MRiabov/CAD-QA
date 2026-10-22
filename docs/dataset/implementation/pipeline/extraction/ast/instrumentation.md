# AST instrumentation

**Parent:** [`extraction/README.md`](../README.md).

Instrumentation turns the normalized program into an equivalent program that
records runtime values by `operation_id`. It does not change CadQuery semantics.

## Rewrite

For each top-level assignment in order:

```text
wpN = <rhs>
```

becomes:

```text
wpN = __cadqa_record(
    operation_id="op:<order:06d>",
    receiver=<receiver expression or None>,
    thunk=lambda: <rhs>,
)
```

An alias assignment:

```text
result = wpN
```

becomes:

```text
result = __cadqa_alias("alias:<order:06d>", lambda: wpN)
```

## RecordedAssignment

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `operation_id` | string | AST | yes | Operation being recorded. | cadquery/states, effects |
| `result_var` | string or null | AST | no | Assigned variable. | 02b |
| `result_kind` | ResultKind | CadQuery | yes | CadQuery workplane, shape, shape list, list, CadQuery selector, or null. | cadquery extraction |
| `receiver_value` | runtime value or null | CadQuery | no | Evaluated receiver. | cadquery/effects |
| `argument_values` | list of runtime values | CadQuery | yes | Evaluated positional and keyword values. | cadquery/effects |
| `result_value` | runtime value or null | CadQuery | yes | Evaluated result. | cadquery extraction |
| `source_span` | SourceSpan | AST | yes | Assignment span. | failures |

## Rules

- The `thunk` is called once. The original expression is not evaluated twice.
- Nested CadQuery constructor expressions are evaluated inside the thunk; only the
  top-level call is an operation.
- The recorder must preserve identity of CadQuery objects and shape lists.
- A recorder failure rejects the program with the `operation_id` and assignment span.
- P0/P1 do not support chained CadQuery calls; one top-level assignment has one
  CadQuery operation.
