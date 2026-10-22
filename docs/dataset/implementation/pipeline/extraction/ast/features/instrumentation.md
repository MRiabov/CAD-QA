# AST instrumentation

**Parent:** [`../algorithm/pipeline.md`](../algorithm/pipeline.md).

Instrumentation turns the normalized program into an equivalent program that
records runtime values by `operation_id`. It does not change CadQuery semantics.
The runtime side of this ABI is [`../../cadquery/algorithm/runtime.md`](../../cadquery/algorithm/runtime.md).

## Rewrite

For each call assignment in order:

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

For a name alias:

```text
result = wpN
```

becomes:

```text
result = __cadqa_alias(
    alias_id="alias:<order:06d>",
    result_var="result",
    target_var="wpN",
    evaluate=lambda: wpN,
)
```

For a subscript alias:

```text
result = wpN[0]
```

becomes:

```text
result = __cadqa_alias(
    alias_id="alias:<order:06d>",
    result_var="result",
    target_var="wpN",
    evaluate=lambda: wpN[0],
)
```

## Recorder ABI

`__cadqa_record` takes the operation ID, result variable, receiver variable,
CadQuery selector category, capture class, and a zero-argument `evaluate` callable. It calls the `evaluate` callable
exactly once, classifies the result, and returns the result unchanged.

`__cadqa_alias` takes the alias ID, result variable, optional target variable,
and an `evaluate` callable. It calls the `evaluate` callable exactly once, copies the target binding's runtime
state, CadQuery workplane, and selected category, and returns the result unchanged.

The rewrite does not pass receiver values or argument values to the recorder.
The runtime uses `receiver_var` to look up the current binding and does not
evaluate the receiver or arguments a second time.

## RecordedAssignment

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `operation_id` | string | AST | yes | Operation being recorded. | states, effects |
| `result_var` | string | AST | yes | Assigned variable. | validation |
| `result_kind` | ResultKind | CadQuery | yes | CadQuery workplane, shape, shape list, list, scalar, plane, vector, edge, wire, or none. | validation |
| `state_id` | string or null | CadQuery | no | State produced by this operation, when any. | states, effects |
| `selector_result_id` | string or null | CadQuery | no | CadQuery selector result produced by this operation, when any. | selectors |
| `source_span` | SourceSpan | AST | yes | Assignment span. | failures |

## ResultKind

`workplane`, `workplane_list`, `shape`, `shape_list`, `list`, `scalar`, `plane`,
`vector`, `edge`, `wire`, `none`.

## Rules

- The `evaluate` callable is called once. The original expression is not evaluated twice.
- Nested constructor, filter, and `list` expressions stay inside the `evaluate` callable.
- The recorder must preserve object identity and shape-list order.
- A recorder failure rejects the program with the operation ID and assignment
  span.
- P0/P1 has one top-level CadQuery operation per call assignment and no chained
  calls.
- Aliases create no operation, state, CadQuery selector result, or effect.
