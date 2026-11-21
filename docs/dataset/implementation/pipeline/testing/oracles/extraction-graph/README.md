# Extraction graph oracle

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-21. Defines the file format for a human-verified
expected extraction graph and the first two records.

## 1. What it pins

An extraction graph oracle pins the CAD graph that `02c` must build for one
program: the entities, the relations, and the measurements, with the upstream
record that establishes each one.

It is the calibration set for the completeness checker in
[`../../../extraction/graph-completeness.md`](../../../extraction/graph-completeness.md).
The production checker compares the graph with the upstream extraction records;
the oracle proves that the rule table that check applies matches a human on the
sampled programs. The kernel oracle is a development-time expectation origin; it
is not a pipeline stage, and it never runs on the production pool.

It is not a coverage fixture. A coverage fixture is a program chosen to exercise
a capability. An oracle is a program whose expected output a human has checked.

## 2. Scope

`schema_version` 1 covers the **final solid state**:

- the program, operation, feature, state, face, edge, vertex, edge-endpoint, and
  region nodes for the final state;
- the provenance, topology, and material-change relations that end at those
  nodes;
- the state, entity, and effect measurements for the final state.

Intermediate states, selectors, profiles, paths, and workplanes are in the
schema but may be absent from a record. An absent group is named in `excluded`
with a reason. It is not a silent gap.

The oracle is environment-pinned. A CadQuery, OCP, extractor, or tolerance
policy change makes the record `stale`.

## 3. File shape

One file per program:

```text
pipeline/testing/oracles/extraction-graph/<slug>.json
```

The top-level mapping has ten required keys, plus an optional `notes` list.
Unknown keys are rejected at every level. The executable form of this section is
the Pydantic schema in `tools/manual-verification/extraction_oracle_schema.py`;
the test parses every record with it, so a field this document omits or renames
fails the test.

| Key | Value shape | Meaning |
|---|---|---|
| `schema_version` | integer | Record format version. |
| `oracle_kind` | string | `extraction-graph`. |
| `slug` | string | Stable slug; matches the file stem. |
| `scope` | string | `final_state` in version 1. |
| `verification` | object | Who approved it and when. |
| `program` | object | The normalized program and its identity. |
| `environment` | object | The versions that produced the record. |
| `expected` | object | Nodes, relations, measurements, and capabilities. |
| `covers` | object | The vocabulary this record pins. |
| `excluded` | list | Expected absences, each with a reason. |

`notes` is optional and carries free-text rationale. It is not identity-bearing.

### 3.1 `verification`

| Key | Value shape | Meaning |
|---|---|---|
| `status` | `proposed`, `verified`, or `stale` | `proposed` is machine-derived and cannot gate a release. |
| `verified_by` | string or null | The human who approved a `verified` record. |
| `verified_at` | date string or null | When. |
| `rationale` | string | Why the record is trustworthy, or what is still unchecked. |

### 3.2 `program`

| Key | Value shape | Meaning |
|---|---|---|
| `program_id` | string | `cadqaprog:<program_sha256>`. |
| `program_sha256` | string | SHA-256 over the canonical text bytes. |
| `text` | string | The normalized program, exactly one trailing newline. |

The test recomputes the hash from `text`. An edited program without a new hash
fails.

### 3.3 `environment`

| Key | Value shape | Meaning |
|---|---|---|
| `cadquery_version` | string | The CadQuery version the record was derived with. |
| `ocp_version` | string | The OCP version. |
| `tolerance_policy_version` | string | The tolerance policy version. |
| `tolerance_policy_sha256` | string or null | The policy hash, when the policy file exists. |

## 4. Expected content

`expected` has four keys: `nodes`, `relations`, `measurements`, `capabilities`.

### 4.1 Nodes

| Key | Value shape | Meaning |
|---|---|---|
| `local_id` | string | A within-file handle. It is not an identity and is never compared across files. |
| `kind` | string | The CAD graph entity kind, for example `operation`, `solid_state`, `face`. |
| `descriptor` | object | The resolution target in the actual graph. |
| `attributes` | object | String-valued facts the CAD graph entity must carry, for example `method` or `is_final`. |

`local_id` is referenced by relations and measurements. It is stable within the
file and meaningless outside it.

### 4.2 Relations

| Key | Value shape | Meaning |
|---|---|---|
| `kind` | string | The relation kind, for example `has_edge`. |
| `from_local_id` | string | The subject node handle. |
| `to_local_id` | string | The CAD graph entity handle of the relation object. |
| `evidence_rule` | string | The rule that establishes the relation. |

The checker compares resolved endpoint pairs as a set. `adjacent_to` is compared
as an unordered pair.

### 4.3 Measurements

| Key | Value shape | Meaning |
|---|---|---|
| `kind` | string | The measurement kind, for example `volume` or `length`. |
| `subject_local_id` | string | The CAD graph entity handle the measurement belongs to. |
| `value` | string | Canonical decimal text, or canonical JSON text for a composite value. |
| `unit` | string or null | `millimetre`, `square_millimetre`, `cubic_millimetre`, or `unitless`. |
| `tolerance` | string or null | An override; null uses the run policy. |

A count is compared exactly. A geometric value is compared under the tolerance
policy.

### 4.4 Capabilities

A capability entry names a task shape the final graph can support:

| Key | Value shape | Meaning |
|---|---|---|
| `target_category` | string | The task target category. |
| `clue_type` | string | The clue type. |
| `clue_operand_form` | string or null | The operand form, null when the clue carries no reference. |
| `answer_meaning` | string | The answer meaning. |

The list is a lower bound: it records capabilities a human confirmed, not the
complete census. An empty list is valid and means the record does not pin
capabilities yet.

### 4.5 Covers

`covers` names the vocabulary the record pins, so a checker knows the record is
partial:

| Key | Meaning |
|---|---|
| `node_kinds` | CAD graph entity kinds the record pins. |
| `relation_kinds` | Relation kinds the record pins. |
| `measurement_kinds` | Measurement kinds the record pins. |

An entity kind outside the list is outside the record's scope. It is not an
orphan. The record must name the missing capability in `excluded`, so the scope
cannot shrink silently.

## 5. Descriptors

The record never stores a CAD graph entity ID. An entity is written as a
descriptor:

```json
{
  "category": "face",
  "filters": {
    "surface_kind": "cylinder",
    "area": "50.265482",
    "centroid_z": "0.5"
  }
}
```

`category` is the graph entity category. `filters` is an equality filter over
graph fields. Numeric filters are canonical decimal text.

| Category | Usable filters |
|---|---|
| `operation` | `order`, `method` |
| `feature` | `operation_order`, `feature_kind` |
| `solid_state` | `operation_order`, `is_final` |
| `face` | `surface_kind`, `area`, `centroid_x`, `centroid_y`, `centroid_z` |
| `edge` | `curve_kind`, `length`, `centroid_x`, `centroid_y`, `centroid_z` |
| `vertex` | `centroid_x`, `centroid_y`, `centroid_z` |
| `edge_endpoint` | `edge_local_id`, `end` |
| `region` | `feature_operation_order`, `region_sign` |

A descriptor must resolve to exactly one entity in the state scope. Zero matches
or several matches is a record defect, not a reason to pick one. A descriptor
that resolves to several entities means the filters are too weak, and the record
is fixed, not the graph.

## 6. Exclusions

An exclusion records a group the human decided is not expected, with the reason:

```json
{
  "kind": "relation",
  "local_id": null,
  "reason": "selector relations need 02b selector results; added when the stage lands"
}
```

Exclusions are checked in both directions:

- an excluded row that appears in the actual graph makes the record `stale`;
- a row that is neither expected nor excluded is an orphan.

The second direction is what stops an oracle from under-specifying and passing
vacuously.

## 7. Comparison

The checker:

1. resolves every entity descriptor against the actual graph in the scope;
2. compares the resolved node set with the oracle node set;
3. resolves every relation endpoint and compares the relation set;
4. compares measurements under the tolerance policy, and counts exactly;
5. checks every exclusion in both directions;
6. reports missing, orphan, and unclassified counts with the expectation origin
   of each.

A descriptor that does not resolve, a missing relation, an orphan relation, or a
value outside tolerance is a pipeline stage defect. The report carries the
disposition from [`graph-completeness.md`](../../../extraction/graph-completeness.md).

## 8. How to build a record

The generator is a devtool, not pipeline code:

```bash
uv run python tools/manual-verification/build_extraction_oracle.py \
  --program path/to/program.py \
  --slug rotated-box \
  --out docs/dataset/implementation/pipeline/testing/oracles/extraction-graph/rotated-box.json
```

The tool executes the program with plain CadQuery, derives the final-state nodes,
incidence relations, and measurements, and writes a `proposed` record. A human
reviews it against the program text and a render, then sets `verified` and names
the reviewer.

The tool is a different code path from the Go graph builder on purpose. A shared
helper would inherit the builder's blind spots.

## 9. Records

| Slug | Program | Status |
|---|---|---|
| [`box-with-hole`](box-with-hole.json) | A box with a blind hole. | `proposed` |
| [`rotated-box`](rotated-box.json) | The same box, rotated 0.1°, with a blind hole. | `proposed` |

## 10. Calibration coverage

Schema version 1 pins final-state topology and per-entity measurements. It does
not pin the rest of the P0 vocabulary:

| Capability | Pinned by schema v1 | Needs |
|---|---|---|
| final-state topology and incidence | yes | — |
| per-entity measurements | yes | — |
| provenance (`uses`, `derived_from`) | no | 02a CadQuery profile and CadQuery workplane records |
| pair relations and measurements | no | pair emission from the state |
| effects | no | 02b effect capture |
| selectors | no | 02b selector results |
| membership (point probes) | no | builder support for runtime point probes |

Each record's `covers` list is the machine-readable form of this table. A record
that adds a capability adds the entity kinds to `covers` and removes the matching
`excluded` entry.

## 11. What this proves

- That the expected-set derivation matches a human on the sampled programs.
- That the descriptor vocabulary can express the entities and relations a real
  program produces.
- That the known-hard geometry — a 0.1° rotation — is expressible and checkable.

It does not prove the full pool is correct. That is the checker running on the
pool, the coverage census, and the residual random sample.
