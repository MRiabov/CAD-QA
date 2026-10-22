# CadQuery CAD feature solid state effect deltas

**Parent:** [`../algorithm/runtime.md`](../algorithm/runtime.md).

Effects describe what a solid state producing operation changed.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `effect_id` | string | CadQuery | yes | `effect:<operation_id>`. | 02c |
| `operation_id` | string | AST | yes | Producing operation. | 02c |
| `before_state_id` | string or null | CadQuery | no | State before the operation; null for the first state. | 02c |
| `after_state_id` | string | CadQuery | yes | State after the operation. | 02c |
| `volume_change` | double or null | CadQuery | no | Signed volume change. | 02c |
| `bbox_change` | BoundingBoxChange or null | CadQuery | no | Bounding-box change. | 02c |
| `topology_change` | TopologyDelta or null | CadQuery | no | Face, edge, and vertex count changes. | 02c |
| `evidence` | EffectEvidence | CadQuery | yes | Before/after state IDs, measurement rule, and evidence refs. | 02c |

`EffectEvidence` is defined in [`evidence.md`](evidence.md).

## Rules

- Effects are measured from recorded states, not inferred from method names.
- `before_state_id` is the receiver binding's state immediately before the
  operation. A missing before state means the operation created the first state;
  the change fields are null.
- `after_state_id` is the state produced by the operation. A solid state producing
  operation with a receiver state but no after state is a failure; the runtime
  never drops the state or emits a partial effect.
- A failed operation produces no effect.
- Topology counts may be equal while individual entities changed; the count delta
  is not a persistence claim.
