# CadQuery operation effects

**Parent:** [`extraction/README.md`](../README.md).

Effects describe what a state-producing operation changed.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `effect_id` | string | CadQuery | yes | `effect:<operation_id>`. | 02c |
| `operation_id` | string | AST | yes | Producing operation. | 02c |
| `before_state_id` | string or null | CadQuery | no | State before the operation; null for the first state. | 02c |
| `after_state_id` | string | CadQuery | yes | State after the operation. | 02c |
| `volume_change` | double or null | CadQuery | no | Signed volume change. | 02c |
| `bbox_change` | BoundingBoxChange or null | CadQuery | no | Bounding-box change. | 02c |
| `topology_change` | TopologyDelta or null | CadQuery | no | Face, edge, and vertex count changes. | 02c |
| `evidence` | EffectEvidence | CadQuery | yes | Before/after state IDs and measurement rule. | 02c |

## Rules

- Effects are measured from recorded states, not inferred from method names.
- A missing before state means the operation created the first state; the change
  fields are null.
- A failed operation produces no effect.
- Topology counts may be equal while individual entities changed; the count delta
  is not a persistence claim.
