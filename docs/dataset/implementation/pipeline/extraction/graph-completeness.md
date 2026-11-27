# CAD graph completeness

**Parent:** [`02c — Build CAD graph`](../02c-build-cad-graph.md).

**Status:** draft, 2026-11-21. This contract closes the gap between "the graph
rejects a dangling endpoint" and "the graph contains every row it must."

## Purpose

Define what a complete CAD graph must contain, where each expectation comes
from, and how a per-program report proves the expected set equals the persisted
set. [`graph-construction.md`](graph-construction.md) says how to build the
graph. [`validation.md`](validation.md) says when to reject it. This document
says what must be present.

## 1. Why this exists

A graph can be accepted today with a required relation absent. The construction
contract forbids a relation with a missing endpoint and forbids guessing a pair,
but it does not require every valid relation to exist. The only completeness
statement is for per-entity measurements: a missing row rejects the graph.
Relations never got the same sentence.

The loss is invisible. The final shape is unchanged, so no render or
program-level check sees it. The capability census then records the resulting
capability as absent, and `03a` treats it as a corpus deficit. The dataset
shrinks silently, one CAD graph entity or relation at a time.

This contract makes the loss a failure:

- **complete** — the expected set equals the persisted set;
- **sound** — every persisted row is supported by its evidence.

## 2. Expectation origins

An expectation comes from one of four origins. The graph artifact is never one
of them. The origins split by when they run:

| Expectation origin | Declares | Used for | Runs |
|---|---|---|---|
| `contract_rule` | the row the graph must contain for an entity kind | every CAD graph entity, relation, and measurement | every program |
| `upstream_record` | AST and runtime extraction rows | operations, features, states, profiles, paths, workplanes, selectors, effects | every program |
| `emission_rule` | pair rows from the entity tables and the reference classes | pair relations and pair measurements | every program |
| `kernel_oracle` | geometry and incidence measured by plain CadQuery and OCP, without instrumentation | calibration of the rule table, and the dataset release geometry residual-defect sample in the [dataset release geometry residual ledger](../../../requirements/release-dataset-contract.md#dataset-release-geometry-residual-ledger) | development and sampled runs only |

**Production check.** The report compares the persisted graph with the upstream
extraction records and the contract rules. It makes no CadQuery or OCP call,
executes nothing, and writes no new artifact. Its cost is a set comparison over
rows already in memory or already in Parquet.

**Calibration check.** The kernel oracle is used only in development. It
calibrates the rule table through the extraction-graph oracle set, and an
opt-in dev-mode runner flag can build it for a sample. It is not a pipeline stage;
it is off by default, and it never runs on the production pool.

**Anti-circularity invariant.** An expectation never reads the graph artifact.
`expected_source = graph_artifact` is a contract defect. If expected and actual
share a producer, the check is a consistency check, not a completeness check,
and the report must say so.

**Capture gap.** The production check cannot detect extractor capture loss,
because its expected side is the extraction records and its actual side is the
graph built from them. It detects graph-builder loss. Capture loss is covered
only by the verified oracle set and the optional dev-mode kernel oracle. A
release that relies on the production check alone must state that; the report
does not claim capture completeness.

## 3. CAD graph entity completeness

| CAD graph entity kind | Expected from | Rule |
|---|---|---|
| `cadquery_program` | `01d` program row | exactly one |
| `operation` | AST call operation | one per call assignment |
| `feature` | AST solid state producing operation | one per operation with `is_state_producing` |
| `solid_state` | runtime `shape_snapshots` | one per Shape snapshot |
| `point_probe` | runtime point probe | one per row, per state |
| `face`, `edge`, `vertex` | runtime entity table | one per row, per state |
| `edge_endpoint` | runtime edge | one start and one end per edge |
| `cadquery_profile` | AST profile record | one per record |
| `cadquery_path`, `cadquery_path_point`, `cadquery_path_segment` | AST path record | one per record |
| `cadquery_workplane` | AST workplane record | one per record |
| `cadquery_selector_result` | runtime selector result | one per result |
| `region` | feature kind and captured state | `added` for `add_material` or `construction`, `removed` for `remove_material`, none for `modify` |

An alias has no CAD graph entity. It is resolved when the target binding is read.

## 4. Relation completeness

Cardinality is per subject unless stated otherwise. `declared by` names the
contract section that makes the relation mandatory; `instantiated from` names the
data or oracle that supplies the endpoints.

| Relation | Subject | Object | Cardinality | Declared by | Instantiated from |
|---|---|---|---|---|---|
| `before` | operation | operation | one per consecutive operation pair | `graph-construction.md` §Program and provenance | AST operation order |
| `after` | operation | operation | one per consecutive operation pair | `graph-construction.md` §Program and provenance | AST operation order |
| `creates` | operation | feature | one per solid state producing operation | `graph-construction.md` §Program and provenance | AST classification |
| `creates` | operation | solid_state | one per captured state | `graph-construction.md` §Program and provenance | runtime Shape snapshot |
| `uses` | feature | cadquery_profile | one per profile the operation reads | `graph-construction.md` §Program and provenance | AST record |
| `uses` | feature | cadquery_workplane | one per workplane the operation reads | `graph-construction.md` §Program and provenance | AST record |
| `derived_from` | cadquery_profile | cadquery_workplane | one | `graph-construction.md` §Program and provenance | AST record |
| `derived_from` | cadquery_path_point | cadquery_path | one | `graph-construction.md` §Program and provenance | AST record |
| `derived_from` | cadquery_path_segment | cadquery_path | one | `graph-construction.md` §Program and provenance | AST record |
| `derived_from` | cadquery_path | cadquery_workplane | one when the path has a CadQuery workplane | `graph-construction.md` §Program and provenance | AST record |
| `has_face` | solid_state | face | one per entity table row | `graph-construction.md` §Topology | runtime entity table |
| `has_edge` | face | edge | one per `face_has_edge` topology record | `graph-construction.md` §Topology | runtime topology record |
| `has_vertex` | edge | vertex | one per `edge_has_vertex` topology record | `graph-construction.md` §Topology | runtime topology record |
| `adjacent_to` | face | face | one per `face_adjacent_to_face` topology record | `graph-construction.md` §Topology | runtime topology record |
| `has_point_probe` | solid_state | point_probe | one per runtime point probe | `graph-construction.md` §Point probes | runtime point probe |
| `coplanar_with` (P1) | face | face | one per emitted pair | `graph-content.md` §3.3 | derived geometry |
| `coaxial_with` (P1) | edge, cadquery_path_segment | same category | one per emitted pair | `graph-content.md` §3.3 | derived geometry |
| `endpoint_of` | edge_endpoint | edge | one per endpoint | `graph-construction.md` §Topology | runtime edge endpoint |
| `selected_from` | cadquery_selector_result | solid_state | one | `graph-construction.md` §Selection | runtime selector result |
| `selected_by` | face, edge, vertex | cadquery_selector_result | one per selected entity id | `graph-construction.md` §Selection | runtime selector result |
| `adds_material` | feature | region | one when the feature kind is `add_material` or `construction` | `graph-construction.md` §Material change | AST classification |
| `removes_material` | feature | region | one when the feature kind is `remove_material` | `graph-construction.md` §Material change | AST classification |
| `part_of` | region | feature | one per region | `graph-construction.md` §Material change | region derivation |

`adjacent_to` is emitted once per unordered face pair. The persisted direction is
canonical; the checker compares the unordered set. Rows marked (P1) are reported
but not enforced in a P0 release.

Parallelism and perpendicularity are not relation kinds. The graph stores the
`Angle` measurement, and the pair measurement row in section 5 covers it.

## 5. Measurement completeness

| Subject | Measurements | Origin |
|---|---|---|
| `solid_state` | `volume`, `bounding_box`, `centroid`, `face_count`, `edge_count`, `vertex_count`, `validity` | runtime state measurement |
| `face` | `area`, `bounding_box`, `centroid`, `edge_count`, `vertex_count` | runtime entity measurement |
| `edge` | `length`, `bounding_box`, `centroid` | runtime entity measurement |
| `vertex` | `centroid` | runtime entity measurement |
| `cadquery_profile` | `area` | derived from the CadQuery profile's sketch arguments by an exact rule |
| `region` | `volume`, `area`, `bounding_box`, `centroid` | region derivation |
| `point_probe` | `probe_point`, `distance_to_face_surface` | runtime point probe |
| `cadquery_selector_result` | `selected_count` | runtime selector result |
| `cadquery_workplane` | `workplane_frame` | runtime frame capture |
| `operation` | `volume_change`, `bounding_box_change`, `topology_change` | runtime effect delta |
| `pair` | `distance`, `angle` | runtime pair distance for `distance`; derived geometry for `angle` |

The subject for an effect delta is `operation`: the effect belongs to the
operation that produced it, and the measurement type catalog in
[`graph-persistence.md`](graph-persistence.md) names `operation` as the
subject.

The P0 measurement set includes `distance` and `angle`. `workplane_frame` and
`bounding_box_change` are P1, and `validity` is P2; a P0 report lists them but
does not enforce them. A `region` and a `cadquery_profile` are P0 graph entities,
so their measurements are enforced in P0.

A per-entity measurement is total over its scope. A missing row is a defect, not
a data condition. A measurement value is compared with the runtime record; the
record's agreement with the kernel oracle is the calibration check in section 2,
run on a sample. A count is compared exactly.

## 6. Pair rows

The expected pair set is the emission rule applied to the state:

1. take the reference classes and the candidate endpoints of the declared
   CAD graph entity kind in the same state;
2. cross product, for a sparse kind over the true pairs only;
3. drop a pair whose two endpoints are the same entity;
4. reduce to unordered pairs;
5. order the endpoints canonically.

`expected_source = emission_rule`. A pair the rule does not emit is not expected.
A pair the rule emits and the graph lacks is missing. The checker compares sets,
not counts: an extra pair is an orphan. A dense kind is expected only from a
reference class whose member count is within `max_anchor_class_size`; a wider
class contributes nothing to the expected set and is not a missing row.

## 7. Soundness

Every persisted relation and measurement carries `evidence_kind`,
`evidence_rule`, and `evidence_refs`. The checker replays the evidence:

- every referenced upstream row exists;
- the upstream row implies the persisted endpoints;
- the rule named is the rule in the contract table.

An actual row that fails the replay is an **orphan**. An orphan is worse than a
missing row: it makes a task answerable for the wrong reason. The orphan count
must be zero.

## 8. Report

One `GraphCompletenessReport` per program. It is written by `02c` next to the
graph and copied into the run report by `05`.

| Field | Meaning |
|---|---|
| `program_id` | The program. |
| `graph_artifact_sha256` | The graph identity the report covers. |
| `extractor_version`, `canonicalization_version` | The versions that produced the graph. |
| `tolerance_policy_version`, `tolerance_policy_sha256` | The policy used for value comparison. |
| `rows` | One `RelationCompleteness` per relation kind. |
| `node_rows` | One `NodeCompleteness` per node kind. |
| `measurement_rows` | One `MeasurementCompleteness` per subject kind and measurement kind. |
| `disposition` | `complete`, `extractor_gap`, `corpus_defect`, `contract_gap`, or `unclassified`. |

A `RelationCompleteness` row carries `relation_kind`, `subject_kind`,
`object_kind`, `expected_count`, `actual_count`, `missing_count`,
`orphan_count`, `unclassified_count`, `expected_source`, `actual_source`, and
the missing and orphan endpoint pairs with their evidence.

A `NodeCompleteness` row carries `node_kind`, `expected_count`, `actual_count`,
`missing_count`, `orphan_count`, `expected_source`, and `actual_source`. A
`MeasurementCompleteness` row carries `subject_kind`, `measurement_kind`,
`expected_count`, `actual_count`, `missing_count`, `orphan_count`,
`expected_source`, and `actual_source`; `subject_kind` is a graph entity kind or
`pair`.

The row identity is the
[must-extract capability cell](validation.md#the-must-extract-capability-set)
identity: `entity:<node_kind>` for a CAD graph entity row,
`relation:<relation_kind>@<subject_kind>-><object_kind>` for a relation row, and
`measurement:<measurement_kind>@<subject_kind>` for a measurement row. `05`
reads `actual_count` from these rows to prove that at least one accepted graph
realizes each declared capability: a cell with `actual_count > 0` in any one
report is covered.

`actual_source` is always `graph_artifact`. In a production report,
`expected_source` is `contract_rule`, `upstream_record`, or `emission_rule`.
`kernel_oracle` appears only in a calibration report, which the production DAG
does not write.

Disposition rules:

- `complete` — every expected row exists, no orphan, no unclassified row.
- `extractor_gap` — a required row is missing and the upstream record contains
  it. The run fails.
- `corpus_defect` — the program is invalid CadQuery or the runtime extraction
  recorded a kernel failure. The program is rejected with this disposition, not
  a silent deficit.
- `contract_gap` — the expectation cannot be derived because the contract is
  underspecified. The run fails and the contract is fixed.
- `unclassified` — an actual row kind or endpoint pair the table does not cover.
  Any non-zero count fails.

A report with `missing_count > 0`, `orphan_count > 0`, or
`unclassified_count > 0` does not pass.

## 9. Review

The report is the human review artifact for graph-builder loss. It is a table of
counts per relation kind, ranked by missing and orphan count, with one card per
exception: the expected row, the upstream row that implies it, the program lines,
and a render with the endpoints highlighted.

The [dataset release absence ledger](../../../requirements/release-dataset-contract.md#dataset-release-absence-ledger)
covers whole-program drops. This report covers the graph builder. Capture loss — the extraction records themselves missing a row —
is not visible here; the verified oracle set and the optional dev-mode kernel
oracle own it. The two-pane graph viewer locates an exception on the shape; it
does not replace the report.

## 10. What this does not prove

- That the graph supports a task. That is the capability census and `03b`.
- That every declared capability is realized somewhere in the pool. A per-program
  report is complete when the expected rows for that program exist; a capability
  the contract declares and no program builds needs the pool-level
  `extraction_capability_coverage` check
  ([`validation.md`](validation.md#coverage)), which reads this report set.
- That the contract's rule set is complete. That is the extraction-graph oracle
  set in [`../testing/oracles/extraction-graph/`](../testing/oracles/extraction-graph/)
  and the [dataset release geometry residual-defect sample](../../../requirements/release-dataset-contract.md#dataset-release-geometry-residual-ledger).
- That a measurement value is correct. That is the oracle comparison, not the
  completeness count.
- That the upstream extraction is complete. The production report cannot prove
  that; the verified oracle set and the optional dev-mode kernel oracle cover it
  on a sample.
