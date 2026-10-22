# CadQuery topology

**Parent:** [`extraction/README.md`](../README.md).

Topology records connect entities inside one state. They are extracted from the
kernel, not inferred from the program text.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `topology_id` | string | CadQuery | yes | Stable record ID. | 02c |
| `state_id` | string | CadQuery | yes | Containing state. | 02c |
| `relation_kind` | TopologyRelationKind | CadQuery | yes | Face-edge, edge-vertex, or face-face adjacency. | 02c |
| `from_entity_id` | string | CadQuery | yes | From entity. | 02c |
| `to_entity_id` | string | CadQuery | yes | Target entity. | 02c |
| `evidence` | TopologyEvidence | CadQuery | yes | Kernel call or traversal that produced the record. | 02c |

## Records

- `face_has_edge`: face to edge.
- `edge_has_vertex`: edge to vertex.
- `face_adjacent_to_face`: shared edge.
- `solid_has_face`: solid state to face.
- `solid_has_edge`: solid state to edge.
- `solid_has_vertex`: solid state to vertex.

Every endpoint must be in the entity table for the same state. A missing endpoint
rejects the state.
