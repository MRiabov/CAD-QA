# Extraction canonicalization

**Parent:** [`extraction/README.md`](README.md).

Extraction artifacts must be byte-identical on replay. This document fixes the
numeric, JSON, hash, span, and ordering rules used by `02a` and `02b`.

## Versions

`canonicalization_version = "cadqa-extract-canonicalization-v1"`.

The version changes when any rule here changes: decimal precision, rounding
mode, JSON encoding, hash prefix, fingerprint fields, entity ID inputs, shape
hash inputs, or sort order. A change invalidates extraction caches and graph
artifacts built from them.

## Numeric values

- Reject `NaN`, positive infinity, and negative infinity.
- Round every double to 9 decimal places using round-half-to-even.
- Normalize `-0.0` to `0.0`.
- Hash and canonical-JSON floats use a decimal string, never Python `repr`.
  The string has no exponent, no trailing zeros, and no trailing decimal point:
  `12`, `0.5`, `-3.125`.
- Parquet columns remain `DOUBLE`. The decimal string is the hash input only.
- Integer fields are signed 64-bit unless a field says otherwise.
- Counts and ordinals are non-negative.

The canonical decimal string is produced from the rounded value with:

```text
format = sign, integer digits, optional "." and fractional digits
fraction = fractional digits with trailing zeros removed
zero = "0"
```

## Program spans

`SourceSpan` has one-based `start_line`, `start_column`, `end_line`, and
`end_column`. Columns count UTF-8 code points, not bytes. The end position is
exclusive. `source_line` is `start_line`.

## Canonical JSON

`canonical_json(value)` is:

- UTF-8 JSON with sorted object keys;
- separators `,` and `:` with no spaces;
- `ensure_ascii=True`;
- no trailing newline;
- floats encoded as canonical decimal strings;
- null as `null`, booleans as `true`/`false`, strings as JSON strings;
- no `NaN` or infinity.

All hashes are SHA-256 lowercase hexadecimal over UTF-8 bytes.

## Fingerprints

The fingerprint fields are defined in [`cadquery/features/entities.md`](cadquery/features/entities.md).
The canonical fingerprint object is:

```json
{"category":"face","fields":{...}}
```

where `fields` contains only the fields for that category:

- vertex: `point`;
- edge: `start`, `end`, `length`;
- face: `centroid`, `area`, `normal`, `bbox`.

`fingerprint_json = canonical_json({"category": category, "fields": fields})`.

`fingerprint_sha256 = sha256("cadqa.fingerprint.v1\0" + fingerprint_json)`.

`entity_id = "ent:" + sha256("cadqa.entity.v1\0" + state_id + "\0" +
category + "\0" + fingerprint_sha256)`.

The state ID is part of entity identity. The same geometry in two states has two
entity IDs. The fingerprint hash is an audit value and must be reproducible from
the fingerprint fields.

## Shape hash

`shape_hash` is independent of the operation and state IDs:

```text
shape_material = canonical_json({
  "schema": "cadqa.shape.v1",
  "volume": volume,
  "bbox_min": bbox_min,
  "bbox_max": bbox_max,
  "face_count": face_count,
  "edge_count": edge_count,
  "vertex_count": vertex_count,
  "entities": [
    {"category": category, "fingerprint_sha256": fingerprint_sha256}
    ...
  ]
})
shape_hash = sha256("cadqa.shape.v1\0" + shape_material)
```

`entities` is sorted by the entity order below. Two geometrically identical
states have the same shape hash even when produced by different operations.

## Entity order

Entity rows are sorted by:

1. category rank: `vertex` = 0, `edge` = 1, `face` = 2;
2. `fingerprint_json` ascending;
3. `entity_id` ascending.

`ShapeSnapshot.face_count`, `edge_count`, and `vertex_count` count the rows in the
entity table. CadQuery selector `selected_entity_ids` are sorted by:

1. category rank;
2. `entity_id`.

This makes CadQuery selector membership order independent of kernel enumeration order.

## Record order

- Shape snapshots: operation order.
- CadQuery workplane frames: operation order.
- CadQuery selector results: operation order, then `ordinal`.
- CAD feature solid state effect deltas: operation order.
- Topology records: relation kind, then `from_entity_id`, then `to_entity_id`.
- Failure records: one per program; the AST or runtime failure is terminal.

## Topology identity

`topology_id = "topo:" + sha256("cadqa.topology.v1\0" + state_id + "\0" +
relation_kind + "\0" + from_entity_id + "\0" + to_entity_id)`.

Topology endpoints are extraction entity IDs. A topology record whose endpoint
is absent from the state entity table rejects the state.

## Artifact hashes

- `static_model_sha256` is the canonical hash of the complete
  `StaticCadQueryModel` after AST ordering.
- `execution_result_sha256` is the canonical hash of the complete successful
  `ExecutionResult` or failure tombstone.
- `entity_table_ref = "entity:<state_id>"` is a logical reference; the physical
  artifact path is defined in [`artifacts.md`](artifacts.md).

Hashes never include timestamps, hostnames, process IDs, absolute paths, or
kernel handles.

## What is not canonical

The following are never used as inputs to any extraction hash:

- original cache text or comments;
- variable names in P1 duplicate normalization;
- kernel enumeration order;
- floating-point `repr`;
- dictionaries or sets without explicit ordering;
- graph UUIDs, which belong to `02c`.
