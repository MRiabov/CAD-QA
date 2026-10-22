# CadQuery selector results

**Parent:** [`../algorithm/runtime.md`](../algorithm/runtime.md).

A CadQuery selector result is the membership produced by one evaluated CadQuery selector in the AST extraction result.
It is not a solid state. The capture algorithm is in [`../algorithm/runtime.md`](../algorithm/runtime.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `selector_result_id` | string | CadQuery | yes | `sres:<operation_id>:<ordinal>`. | 02c |
| `selector_id` | string | AST | yes | CadQuery selector in the AST extraction result record. | 02c |
| `selected_entity_category` | `face`, `edge`, or `vertex` | AST | yes | Category of the selected entities. | 02c |
| `state_id` | string | CadQuery | yes | State the CadQuery selector ran on. | 02c |
| `selected_entity_ids` | list of string | CadQuery | yes | Stable entity IDs in canonical order. | 02c |
| `count` | integer | CadQuery | yes | Number of selected entities. | 02c |
| `source_span` | SourceSpan | AST | yes | Evaluating call span. | review |

## Rules

- Evaluate the CadQuery selector at the call point; do not re-evaluate later.
- Read membership from the returned `Workplane.vals()` exactly once.
- Map every selected value to an entity in the receiver state's entity table.
  An unmapped value rejects the program with `unmapped_entity`.
- Zero matches is a successful result with count 0.
- A CadQuery selector exception rejects the whole program.
- `count` equals `len(selected_entity_ids)`.
- IDs are sorted by category rank and entity ID, as defined in
  [`../../canonicalization.md`](../../canonicalization.md).
- Wire and solid selectors are outside P0/P1; they are rejected before
  execution rather than recorded with incomplete membership.
