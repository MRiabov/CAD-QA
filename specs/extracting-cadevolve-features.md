# Extracting Features From CADEvolve

This document freezes the first implementation policy for extracting CAD-QA
features from CADEvolve CadQuery programs. It turns the favorable CADEvolve
source regularity described in
[`docs/cad_qa_feature_provenance.md`](../docs/cad_qa_feature_provenance.md)
into executable rules for source normalization, operation graphs,
statement-by-statement tracing, provenance approximation, split metadata, and
answer parsing. Later complex task families also require graph-query
resolution, spatial references, region indexes, and validity probes built from
the same trace records.

The intent is not to support arbitrary Python CAD code first. The first release
targets the programmatically normalized CADEvolve shape: mostly assignments of
the form:

```python
wp2 = wp1.function(...)
```

Rare source constructs are represented explicitly and either executed in the
trace worker or filtered from task families that cannot defend their labels.

## 1. Ported IntersectionQA Policies

CAD-QA should port these proven IntersectionQA implementation contracts.

### 1.1 Isolated worker execution

Use the same bounded multiprocessing pattern as IntersectionQA source object
validation:

- create one worker process per source validation or trace job;
- return exactly one structured result through a bounded queue;
- terminate the worker after `timeout_seconds`;
- record timeout, worker crash, queue-empty, source error, and unknown error as
  explicit failure records;
- return results in input order, independent of worker completion order;
- store Python, CadQuery, OCP, OpenCascade, config hash, source hash, and label
  policy in the trace metadata.

IntersectionQA reference:

- `../IntersectionQA/intersectionqa/sources/validation.py`
- `../IntersectionQA/intersectionqa/config.py`

CAD-QA adapts this contract from "execute one object and measure final shape"
to "execute a normalized source statement-by-statement and emit operation
nodes, snapshots, selector tables, point labels, and failure diagnostics."

The first port is process isolation plus timeout/crash accounting. Stronger
filesystem, network, and subprocess restrictions remain desirable, but they
must be implemented without changing the public trace schema.

### 1.2 Group-safe splits

Use the same deterministic grouped split style as IntersectionQA:

- compute a split group before row-level assignment;
- assign all rows in the group to one split;
- use stable SHA-256 buckets of `f"{seed}:{group_id}"`;
- route selected generator/source-family values to generator heldout;
- route selected operation signatures to operation heldout;
- route selected topology signatures to topology heldout;
- route near-boundary point groups to the near-boundary challenge split;
- emit a split manifest and leakage audit.

IntersectionQA reference:

- `../IntersectionQA/intersectionqa/splits/grouped.py`
- `../IntersectionQA/intersectionqa/sources/cadevolve.py`

For CAD-QA, the default split group is:

```text
counterfactual_group_id
or source_id
or normalized_source_code_hash
```

This is stricter than object-pair grouping because one CADEvolve script can
produce many trace-backed QA rows. Rows from the same base source must not
cross protected splits.

## 2. CADEvolve Source Identity

Load only executable source trees by default:

```text
CADEvolve-P/
CADEvolve-C/
```

Treat `CADEvolve-G/` as generator or family metadata unless a later policy
explicitly supports generator execution.

Do not redownload or duplicate CADEvolve by default. Prefer a configured
adjacent/local source tree, including an extracted source cache owned by a
sibling repository. Normalize source-relative paths by removing one leading
`./`. Preserve the original archive member path separately when it exists, but
do not require an archive for ordinary generation.

Derive source metadata as follows:

| Field | Rule |
| --- | --- |
| `source_id` | Deterministic ID from normalized source-relative path plus normalized source hash. |
| `source_subtree` | First path component, for example `CADEvolve-P`. |
| `source_subset` | First two path components when present. |
| `generator_id` | `cadevolve_` plus a sanitized first-two-component path prefix, matching IntersectionQA's conservative fallback. |
| `normalized_source_code_hash` | SHA-256 over canonical normalized source text. |
| `operation_signature_hash` | SHA-256 over the canonical ordered operation names and normalized argument classes. |
| `topology_signature_hash` | SHA-256 over final snapshot topology counts and coarse geometry tags, when final trace succeeds. |

Local absolute source roots are private run-manifest data. They must not appear
in public rows.

When exact upstream generator IDs are later recoverable from `CADEvolve-G`, they
may be stored as `generator_ids`; the path-derived `generator_id` remains the
fallback leakage key.

## 3. Source Normalization

Normalization must be deterministic and AST-backed.

### 3.1 Text normalization

Apply these rules before hashing:

- decode as UTF-8 with replacement only at source loading boundaries;
- normalize line endings to `\n`;
- strip trailing whitespace;
- ensure exactly one final newline;
- preserve statement order and source line numbers;
- do not rewrite numeric literals except through Python AST round-tripping if a
  later formatter is adopted for every source.

### 3.2 Imports and globals

Allow CadQuery imports and harmless Python assignments needed by CADEvolve
programs. The normalized prompt may standardize import aliases, but the trace
worker must preserve semantics.

The first implementation should accept:

```python
import cadquery as cq
import cadquery
from cadquery import Workplane
```

Other imports are marked `unsupported_import` unless they are explicitly
allowlisted by config. Unsupported imports do not silently disappear.

### 3.3 Final result detection

Use this priority:

1. `result`
2. `shape`
3. `solid`
4. `part`
5. the target of the last supported CadQuery-producing assignment

If the detected final object is missing, not a CadQuery object, empty,
non-finite, or not a valid solid/compound under the configured policy, trace
execution returns an invalid record with a machine-readable failure reason.

### 3.4 Supported operation statements

The primary supported operation node is:

```python
target = base.method(...)
```

where `target` and `base` are names and `method` is a CadQuery operation or
selector-producing method.

The extractor should also support:

- initial constructor calls such as `wp1 = cq.Workplane("XY")`;
- single assignment to a fluent chain by decomposing the chain into canonical
  ordered operations when source locations are available;
- calls on prior variables, such as `wp5 = wp2.cut(wp4)`;
- final aliases, such as `result = wp42`;
- direct CadQuery constructors and simple constants used as arguments.

Rare constructs are represented explicitly:

| Construct | Policy |
| --- | --- |
| Attribute bases such as `foo.bar.method(...)` | Create an operation node with `status: "partial"` and execute in trace worker if safe. |
| Subscript bases such as `wp7.vals()[18]` | Create `status: "partial"` node; exclude from static operation-count rows unless trace expansion proves the operation count. |
| Direct context mutation such as `wp41.ctx.pendingWires = [...]` | Create a side-effect node; exclude from provenance rows unless the trace proves a stable effect. |
| Dynamic imports, `exec`, `eval`, filesystem, network, subprocess | Reject or quarantine before execution. |
| Unbounded loops or data-dependent loops | Reject from source-normalized MVP rows. |
| Static bounded loops | Execute in trace worker; static operation-count rows may use trace-expanded counts only when expansion is recorded. |

## 4. Operation Graph

Each accepted operation node must include:

```json
{
  "feature_id": "wp13",
  "step_index": 13,
  "source_line": 42,
  "target": "wp13",
  "base": "wp7",
  "operation": "cut",
  "args_repr": ["wp12"],
  "input_features": ["wp7", "wp12"],
  "status": "ok"
}
```

`feature_id` is the normalized output variable when the variable is unique and
stable. Otherwise use `opNNNN` from canonical operation order. `step_index` is
zero-based in the normalized operation graph.

`operation_signature_hash` is computed from canonical operation records, not
from prompt text. At minimum it includes operation name, argument kind summary,
selector strings when present, and dependency feature IDs.

## 5. Statement-By-Statement Trace

CAD-QA traces should execute normalized source statement-by-statement inside
the isolated worker.

For each supported statement:

1. execute the statement in the worker namespace;
2. identify the produced or mutated CadQuery object;
3. record pre/post object references while the worker is alive;
4. compute cheap scalar snapshot labels immediately;
5. defer expensive matching or boolean work behind task-specific gates;
6. emit a structured snapshot or failure record.

Snapshot scalar labels include:

- object status;
- volume;
- world-coordinate bounding box;
- topology counts;
- coarse geometry type counts;
- selector result tables when the statement includes a selector;
- diagnostics and kernel status.

Task materialization must consume stored trace metadata only. It must not load
CadQuery or rerun source code while formatting prompts.

Optional later-stage trace metadata includes:

- typed graph nodes and edges over features, parameters, workplanes, topology
  entities, material regions, and measured attributes;
- stable point, centroid, axis, and centerline references;
- entity and material-region bounding boxes for spatial-window queries;
- validity probe results for bounded operation or candidate-edit checks.

## 6. Diff And Provenance Policy

The default diff unit is adjacent snapshots: compare state before and after one
operation.

Do not compute full boolean diffs for every adjacent pair. Boolean operations
are expensive and should be gated.

### 6.1 Cheap first-pass diff

Always compute:

- volume delta;
- bounding-box delta;
- topology count delta;
- entity geometry signatures where entity traversal is available;
- point membership before/after for sampled points;
- selector count before/after for selector tasks.

Use these cheap signals to decide whether a row is eligible for task
materialization or needs expensive confirmation.

### 6.2 Entity matching

Stable entity IDs are per snapshot. Cross-snapshot matching is best-effort and
must store method and confidence.

Preferred matching signals:

- OpenCascade builder history when captured;
- entity type;
- geometry type;
- centroid or representative point;
- area or length;
- bounding box;
- normal or tangent direction;
- adjacency signatures;
- tolerance-versioned hash of the above.

Low-confidence many-to-many matches are not forced into single-feature labels.
They are stored as `ambiguous_or_merged` or filtered from single-choice tasks.

### 6.3 Point provenance

For a point-grounded provenance row, run the point classifier at each relevant
snapshot. A feature is a candidate:

- `created_by` when the point changes from outside or ambiguous to inside;
- `deleted_by` when it changes from inside to outside or ambiguous;
- `modified_by` when it remains inside but the nearest containing/bounding
  entity changes with adequate confidence;
- `inherited_from` when it remains inside and nearest-entity matching is stable;
- `bounded_by` when the point lies on a boundary induced by multiple features;
- `ambiguous_or_merged` when the above cannot be defended.

This avoids full shape boolean diffs for most point questions.

### 6.4 Boolean-gated confirmation

Use OpenCascade Boolean differences only when all of these are true:

- the candidate task needs material-region evidence that cheap signals cannot
  provide;
- pre/post bounding boxes overlap or a volume delta indicates possible material
  change;
- the operation type is high-value for provenance, such as cut, fuse, intersect,
  hole, shell, fillet, chamfer, loft, sweep, or revolve;
- the source already passed scalar snapshot validation;
- the worker has budget left under the configured timeout.

Boolean diff failures must not invalidate the whole trace when scalar labels
are otherwise valid. They invalidate only provenance rows that require the
failed evidence.

## 7. Graph, Spatial, And Validity Extensions

These extensions are not required for the MVP rows, but their extraction policy
must remain compatible with the same source records and trace snapshots.

### 7.1 Graph query inputs

Build a typed graph from existing trace records:

- feature nodes from operation graph nodes;
- parameter nodes from normalized arguments when they can be resolved without
  executing arbitrary Python outside the trace worker;
- workplane, solid, face, edge, vertex, and material-region nodes from
  snapshots and topology maps;
- edges such as `before`, `after`, `input_to`, `selected_by`, `created_by`,
  `modified_by`, `deleted_by`, `adjacent_to`, `parallel_to`, `coaxial_with`,
  and `contained_in`.

Store graph-query IR separately from natural-language prompts. Query resolution
must produce resolved feature/entity IDs, measured values, tie-break evidence,
and a resolution status. Rows with ambiguous ordinal references such as "the
second box" are invalid unless the exact operation node resolves uniquely.

### 7.2 Spatial references

Derive stable references only when the geometry supports them:

- points from explicit coordinates, centroids, or sampled point queries;
- axes from cylindrical/conical entities or operation parameters with a stable
  workplane frame;
- centerlines from holes, cylinders, or circular edge sets with a documented fit
  method;
- bounding-box regions from explicit world-coordinate min/max values.

Every reference stores source feature/entity IDs, frame, extraction method, and
confidence. Distance rows are valid only when both references resolve with
confidence above the task threshold.

### 7.3 Bounding-box region indexes

Build region indexes from topology entity bounds, centroids, sampled material
points, and conservative pre/post material-change evidence. Region-query rows
must declare whether they use `inside`, `intersects`, `contains_centroid`,
`added_material_in_region`, or `removed_material_in_region`. AABB overlap alone
is a heuristic baseline unless exact or conservative geometry evidence confirms
the answer.

### 7.4 Validity probes

Validity and failure-mode tasks execute bounded probes in isolated workers.
Each probe records target operation or candidate edit, pre/post validity,
kernel status, failure stage, failure type, searched parameter range, and
threshold value when a stable threshold exists. Repeated probes should agree
before a public row is emitted.

## 8. Selector Tables

Selectors are CadQuery semantics, not natural-language geometry descriptions.

For each source selector expression, store:

- expression text;
- target feature/state;
- entity type requested;
- raw selected entity IDs;
- deduplicated entity IDs;
- selected count;
- CadQuery/OCP/OpenCascade versions;
- dedup tolerance and failure status.

Selector tasks use stored selector tables. They do not reevaluate selectors in
prompt generation.

## 9. Split And Leakage Metadata

Every public row must carry:

- `source_id`;
- `generator_id`;
- `source_subtree`;
- `normalized_source_code_hash`;
- `operation_signature_hash`;
- `topology_signature_hash` when available;
- `counterfactual_group_id` when applicable;
- `point_sampling_group_id` when applicable;
- `graph_query_group_id` when applicable;
- `spatial_reference_group_id` when applicable;
- `validity_probe_group_id` when applicable;
- `split_group`.

Protected split assignment priority:

1. all rows in one `split_group` stay together;
2. generator-heldout overrides ordinary random assignment;
3. topology-heldout overrides ordinary random assignment;
4. operation-heldout overrides ordinary random assignment;
5. near-boundary point groups route through the near-boundary bucket policy;
6. remaining groups use deterministic train/validation/test buckets.

Leakage audit must check overlaps across protected splits for:

- `source_id`;
- `generator_id`;
- `source_subtree`;
- `normalized_source_code_hash`;
- `operation_signature_hash`;
- `topology_signature_hash`;
- `counterfactual_group_id`;
- `point_sampling_group_id`;
- `split_group`.

## 10. Numeric Answer Parsing

Numeric answers use a four-significant-figure parse policy unless the row
declares a stricter task-specific tolerance.

Examples of valid four-useful-digit answers:

```text
12.34
123.4
1.234
0.1234
123400
```

For scalar numeric answers:

- parse exactly one finite number from the answer candidate;
- reject prose-only answers and answers with multiple numeric candidates;
- compare the parsed number against the canonical answer with tolerance:

```text
effective_tolerance = max(row.numeric_tolerance or 0,
                          half_unit_of_fourth_significant_digit(answer))
```

For a nonzero canonical value `x`:

```text
half_unit = 0.5 * 10 ** (floor(log10(abs(x))) - 3)
```

For canonical zero, use `row.numeric_tolerance` when present, otherwise the
task's absolute zero tolerance from the label policy.

For bounding boxes and coordinates, apply the same rule independently to each
coordinate, then require every coordinate to pass.

The exported label may keep more precision than four significant figures. The
parse policy defines accepted model output precision, not trace precision.

## 11. Initial Build Order

Implement in this order:

1. source loading and normalized source records;
2. AST operation graph extraction for simple CADEvolve assignments;
3. strict source rejection/quarantine for dangerous dynamic constructs;
4. ported isolated worker execution;
5. statement-by-statement scalar snapshots;
6. `operation_count`, `bbox_after_step`, and `signed_volume_delta` rows;
7. selector tables and `selector_count`;
8. topology counts;
9. point membership;
10. conservative provenance rows.

Provenance and CADEditQA should not block the scalar trace spine.
