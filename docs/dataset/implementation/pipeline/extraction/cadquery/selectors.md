# CadQuery selector results

**Parent:** [`extraction/README.md`](../README.md).

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `selector_result_id` | string | CadQuery | yes | `sres:<operation_id>:<ordinal>`. | 02c |
| `selector_id` | string | AST | yes | Static CadQuery selector record. | 02c |
| `state_id` | string | CadQuery | yes | State the CadQuery selector ran on. | 02c |
| `selected_entity_ids` | list of string | CadQuery | yes | Stable entity IDs, in deterministic order. | 02c |
| `count` | integer | CadQuery | yes | Number of selected entities. | 02c |
| `source_span` | SourceSpan | AST | yes | Evaluating call span. | review |

## Rules

- Evaluate at the call point; do not re-evaluate later.
- Zero matches is a successful result with count 0.
- A CadQuery selector exception rejects the whole program.
- Every selected entity ID must exist in the state entity table.
- `count` must equal the number of selected entity IDs.
