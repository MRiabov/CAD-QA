# CadQuery entities

**Parent:** [`extraction/README.md`](../README.md).

Each state has an entity table with one row per face, edge, and vertex.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `entity_id` | string | CadQuery | yes | Stable geometric entity ID. | 02c |
| `state_id` | string | CadQuery | yes | Containing state. | 02c |
| `entity_category` | EntityCategory | CadQuery | yes | Face, edge, or vertex. | 02c |
| `fingerprint` | EntityFingerprint | CadQuery | yes | Canonical geometry used for the ID. | 02c |
| `fingerprint_sha256` | sha256 | CadQuery | yes | Hash of the canonical fingerprint. | 02c |
| `surface_kind` | SurfaceKind or null | CadQuery | no | Face surface category. | 02c |
| `curve_kind` | CurveKind or null | CadQuery | no | Edge curve category. | 02c |
| `is_closed` | boolean or null | CadQuery | no | Closed edge flag. | 02c |

## EntityFingerprint

| Entity category | Fields |
|---|---|
| Vertex | `point: Point3` |
| Edge | `start: Point3`, `end: Point3`, `length: double` |
| Face | `centroid: Point3`, `area: double`, `normal: Vector3`, `bbox: BoundingBox` |

`entity_id` is a hash of `state_id`, `entity_category`, and the canonical
fingerprint. Rounding and canonical encoding are fixed by the extraction version.
Two entities in one state with the same fingerprint reject the program as
ambiguous topology; do not add an arbitrary ordinal.
