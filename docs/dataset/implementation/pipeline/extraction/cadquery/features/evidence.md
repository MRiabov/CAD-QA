# Extraction evidence

**Parent:** [`../algorithm/runtime.md`](../algorithm/runtime.md).

Evidence makes a measurement, effect, or topology record reproducible. It is an
extraction-local model; `02c` translates it into CAD graph evidence references.

## EvidenceRef

`EvidenceRef` is a tagged union with exactly one non-null group:

| Group | Fields | Meaning |
|---|---|---|
| `state` | `state_id` | Shape snapshot used by the record. |
| `entity` | `state_id`, `entity_id` | Entity row used by the record. |
| `operation` | `operation_id` | AST operation that produced the record. |
| `span` | `SourceSpan` | CadQuery program span. |
| `kernel_call` | `call` | Exact CadQuery/OCP call string, such as `Face.Edges()` or `Shape.Volume()`. |
| `selector` | `selector_result_id` | CadQuery selector membership used by the record. |
| `runtime_artifact` | `artifact_uri`, `field` | Runtime extraction artifact and field used by the record. |

`call` is the exact API name and argument shape used at capture. It is not a
free-form explanation.

## EffectEvidence

| Field | Field type | Required | Meaning |
|---|---|---|---|
| `before_state_id` | string or null | no | State before the operation. |
| `after_state_id` | string | yes | State after the operation. |
| `rule` | string | yes | Exact measurement rule, such as `after.volume - before.volume`. |
| `refs` | list of EvidenceRef | yes | States, operations, spans, and kernel calls that reproduce the effect. |

Effect evidence is attached at capture time. A missing state or kernel call
rejects the effect.

## TopologyEvidence

| Field | Field type | Required | Meaning |
|---|---|---|---|
| `relation_kind` | TopologyRelationKind | yes | Relation category. |
| `from_entity_id` | string | yes | From entity row. |
| `to_entity_id` | string | yes | Target entity row. |
| `call` | string | yes | Kernel call that produced the relation. |
| `refs` | list of EvidenceRef | yes | State, entities, operation, and span. |

Topology evidence records the traversal that found the relation. It does not
invent an incidence that the kernel did not return.

## CadQuery selector evidence

A `CadQuerySelectorResult` carries its `selector_id`, `selector_result_id`, `state_id`,
and `source_span`. Its membership list is the evidence; a count without
membership is not sufficient for a face, edge, or vertex CadQuery selector.

## Mapping to `02c`

`02c` converts:

- `state` and `entity` references to CAD graph entity IDs;
- `operation` references to operation CAD graph entity IDs;
- `span` references to graph `source_line` evidence;
- `selector` references to CadQuery selector-result CAD graph entity IDs;
- `kernel_call` and `runtime_artifact` references to runtime-artifact evidence.

A reference that does not resolve to a CAD graph entity, measurement, operation, or
artifact rejects the graph. `02c` does not drop an unresolved reference.

## Rules

- A record with required evidence missing is rejected.
- Evidence is captured once, at the same time as the record.
- Do not reconstruct evidence from prompt text, task text, or a later run.
- Do not store a kernel handle as evidence.
- Canonical ordering of `refs` follows [`../canonicalization.md`](../../canonicalization.md).
