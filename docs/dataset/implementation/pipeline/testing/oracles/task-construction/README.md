# Task-construction oracles

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-22; rebuilt 2026-11-25 and 2026-11-27. Defines the
hand-authored gold task format, the first thirteen records, and the coverage
gaps. The gold queries pass. Every record was rebuilt against the 2026-11-24
requirement revisions — categorical features and the measured direction,
one-condition references, the clue reduction form rename, the provenance workplane
removal, and the pair-angle relation — and validates against
`schema_version` 3. The owner reviewed and accepted the set on 2026-11-25 and
accepted the three re-verified records on 2026-11-27. The later center-naming and
distance-copy change altered two questions, and the 2026-11-27 pair-answer
rebuild moved `box-top-bottom-distance` and `box-top-front-angle` onto a
clue-bound reference (the angle record now runs on the box-with-hole program so
both of its clues are necessary). All thirteen records are `verified`; a record
added later starts as `proposed`.

## 1. What a task-construction oracle is

A task-construction oracle is a checked-in, hand-authored **gold task**: one
program, one task description, one answer, and one **gold query** that
reproduces the answer with plain CadQuery. It is the independent expectation for
`03b` construct task definitions.

It is not a pipeline artifact. The generator never reads it, and the release
never contains it. It is test data with a reviewed diff.

It is not a golden record. A [golden record](../../golden/README.md) pins what the
constructor *did* produce, so a change is visible. An oracle pins what the
constructor *should* produce, written from the program and the task contract,
with a second code path that proves the answer. A golden record catches
regression; an oracle catches a shared mistake between the graph and the
constructor.

## 2. What the set is for

The set answers two questions:

1. **What cases do we intend to support?** The coverage table in section 9 is
   the executable form of the P0 vocabulary. A cell with no record is a work
   item, not a silent absence.
2. **Are those cases supported independently?** When `03b` lands, it constructs
   each oracle's task from the program and the task description. The answer, the
   clue chain, and the evidence must match. A mismatch is a defect in the graph,
   the constructor, or the contract. It is never a reason to edit the oracle to
   match the constructor.

The gold query is the independent half. It executes the program with plain
CadQuery and OCP, using no CAD graph and no constructor code. If the constructor
and the query disagree, one of them is wrong, and the disagreement is the
signal.

## 3. File shape

One file per gold task:

```text
pipeline/testing/oracles/task-construction/<slug>.json
```

`<slug>` is a lower-case slug and matches the file stem. The file is UTF-8 JSON
with a trailing newline. The executable form of this section is
`tools/manual-verification/task_oracle_schema.py`; the test parses every record
with it, so a field this document omits or renames fails the test.

The top-level mapping has twelve keys:

| Key | Meaning |
|---|---|
| `schema_version` | Record format version. |
| `oracle_kind` | `task-construction`. |
| `slug` | Stable slug; matches the file stem. |
| `verification` | Who approved it, why, and the gold-query check. |
| `environment` | The versions that produced the record. |
| `program` | The normalized program and its identity. |
| `task` | The task description given to the constructor. |
| `clues` | The expected canonical clue chain, with narrowing counts. |
| `answer` | The expected answer, parameter, evidence, and equivalent set. |
| `gold_query` | The independent query that reproduces the answer. |
| `covers` | The vocabulary cell this record pins. |
| `excluded` | Expected absences, each with a reason. |

`notes` is optional and carries free-text rationale. It is not identity-bearing.

### 3.1 `verification`

| Key | Meaning |
|---|---|
| `status` | `proposed`, `verified`, or `stale`. |
| `verified_by`, `verified_at` | The human who approved a `verified` record, and when. |
| `rationale` | Why the record is trustworthy, or what is still unchecked. |
| `gold_query` | `status` (`passed`, `failed`, `not_run`), the observed `stdout`, and `checked_at`. |

`proposed` means the record is machine-checked but a human has not read it. A
`proposed` oracle cannot gate a release. `verified` requires a named human.
`stale` means the environment or the contract moved; the record is re-derived
and re-verified, not reused.

The `gold_query` block is the machine check. The test re-runs the query and
compares its output with `expected_stdout`; a passing block with a different
recorded stdout is a defect.

### 3.2 `environment`

| Key | Meaning |
|---|---|
| `cadquery_version`, `ocp_version`, `python_version` | The versions that produced the record. |
| `oracle_tool_version` | The prelude and gold-query check version. Bumped when the prelude, or the rule that turns a run into a recorded result, changes. |

A CadQuery, OCP, or tool-version change invalidates the recorded check. Re-run
the gold-query verifier; `--write` stamps the new environment and reopens a
`verified` record as `proposed`, so review the diff and accept it again. A
record whose contract moved, rather than only its environment, is marked
`stale` before re-derivation. How the gold-query verifier schedules records is
not part of this version: it runs the same per-record script, so batching those
scripts into one process does not bump `oracle_tool_version`.

### 3.3 `program`

| Key | Meaning |
|---|---|
| `program_id` | `cadqaprog:<program_sha256>`. |
| `program_sha256` | SHA-256 over the canonical text bytes. |
| `text` | The normalized program, exactly one trailing newline. |

The test recomputes the hash from `text`. The gold query runs after this text in
the same namespace and uses the final solid bound to `result`.

### 3.4 `task`

| Key | Meaning |
|---|---|
| `target_category` | The task target category. |
| `question` | The hand-authored question the reviewer answers. Not the rendered prompt; `04` owns the prompt wording. |
| `state_scope` | `final` in P0. |
| `possible_answer_count` | The size of the initial possible-answer set. |
| `task_reasoning_step_count` | Clue steps plus the answer step, if any. |
| `answer_meaning` | What the answer is about. |
| `native_answer_format` | The meaning's native format. |
| `answer_format` | The format the prompt requests. |
| `geometry_required` | Whether at least one task reasoning step (a clue step or the answer step) depends on the built shape. |
| `uniqueness` | The rule that makes the target and the answer unique. |

`possible_answer_count` is the full target-category set in the state scope when
a clue narrows the target. A task whose question identifies the target directly
has no clue, and its `possible_answer_count` is 1: the question already names
the one candidate. This is the rule the rebuilt records use. `03b` must adopt
the same rule, or the two disagree about the first clue's `before` count.

### 3.5 `clues`

One entry per clue, in canonical order. The record does not carry a separate
clue reduction form profile field: the ordered form values define it.

| Key | Meaning |
|---|---|
| `order` | 1-based canonical position. |
| `clue_type` | `property`, `relation`, `comparison`, `aggregation`, or `provenance`. |
| `clue_reduction_form` | The reference's reduction form: `filtered`, `selected_in_earlier_clue`, `aggregated`, or `cross_state`; null for a property clue. |
| `statement` | The clue in words, for review. Not compared. |
| `check` | The typed check. Its `predicate_kind` equals `clue_type`. |
| `narrows` | `before` and `after` possible-answer counts. |

A property check is one of two shapes, discriminated by `property_shape`:

| `property_shape` | Keys | Meaning |
|---|---|---|
| `measurement` | `measurement`, `comparator`, and `threshold` or `range_min`/`range_max`; `axis` when the measurement is `angle` | A measured value. The comparator is a `label.comparator` key (`eq`, `gt`, `ge`, `lt`, `le`); `between` marks a range. A direction is the `angle` measurement against the named program axis. |
| `categorical_feature` | `feature`, `value` | Equality on a face's categorical feature: `face_surface_kind` or `position`. |

A relation check is one of two shapes, discriminated by `relation_shape`:

| `relation_shape` | Keys | Meaning |
|---|---|---|
| `named` | `relation_type`, `direction`, `object` | A named relation from `graph-content.md` §3. |
| `angle` | `measurement` (`angle`), `comparator`, `threshold`, `object` | The `Angle` measurement between the target and the reference. |

A comparison check carries `measurement`, `comparator`, and `reference`; a
provenance check carries exactly one of `operation` or `cadquery_profile`.

The first clue starts at `possible_answer_count`; each clue ends where the next
one starts; every clue strictly narrows and is necessary, so dropping it from the
chain leaves at least two distinct answers or changes the answer (`DS-REQ-34`);
the last `after` count equals the size of the answer-equivalent set.

### 3.6 `answer`

| Key | Meaning |
|---|---|
| `value_kind` | `number`, `integer`, `boolean`, `point`, `bounding_box`, `label`, or `structured`. |
| `value` | The answer value, in the shape its value kind declares. |
| `unit` | The graph measurement unit of the expected answer: `millimetre`, `square_millimetre`, `cubic_millimetre`, `degree`, or `unitless`. It is test data used to choose the tolerance; it is not a release column. |
| `tolerance` | `{tolerance_kind, value_text}` for a numeric answer; null for an exact answer. |
| `scoring_rule` | `exact`, `numeric_tolerance`, or `structured_exact`. |
| `parameter` | The meaning's declared parameter, or null. See section 4. |
| `point_probe` | The probe for a membership answer; null otherwise. |
| `evidence_kind` | `measured` or `derived`. |
| `evidence_rule` | The resolver rule that produced the answer. |
| `evidence_refs` | The graph references the rule uses. |
| `answer_equivalent_set` | One entry per remaining candidate, with its subject and value. |

A numeric answer is canonical decimal text at 4 significant figures, and its
tolerance is explicit. An integer, boolean, or label answer is exact. The
answer-equivalent set is non-empty, and every entry gives the answer value under
`same_answer`.

### 3.7 `gold_query`

| Key | Meaning |
|---|---|
| `language` | `python`. |
| `code` | The query fragment. |
| `expected_stdout` | The one line the query prints. |
| `sha256` | SHA-256 over the UTF-8 bytes of `code`. |

The gold-query verifier builds one script: the prelude, the program text, then the query
fragment. The prelude imports `json`, `math`, and `cadquery as cq`, and defines:

```python
def canon(value: float) -> str:
    """Canonical decimal text: 4 significant figures, near-zero is 0."""
    if abs(value) < 1e-9:
        return "0"
    return format(value, ".4g")
```

The query prints exactly one non-empty line. A scalar prints its canonical text;
a point prints `{"x": "...", "y": "...", "z": "..."}`; a bounding box prints
`{"min": {...}, "max": {...}}`; both use compact JSON with sorted keys. The
record's `expected_stdout` is derived from `answer.value` and must equal the
query's output.

`canon` uses Python's `.4g` formatting. The constructor must produce the same
canonical text. If the two languages disagree about a rounding tie, that is a
contract defect, not a reason to loosen the oracle.

### 3.8 Entity descriptors

A `subject`, `object`, `reference`, or `parameter.subject` is an entity
descriptor with the shape and resolution rule in
[`golden/README.md` §4](../../golden/README.md#4-entity-descriptors). The oracle
records use these filters:

| Filter | Graph field |
|---|---|
| `surface_kind` | `face_surface_kind` |
| `position` | The face's `position` set contains the named extreme. |
| `curve_kind` | `edge_curve_kind` |
| `centroid_x`, `centroid_y`, `centroid_z` | Components of the `centroid` measurement. |
| `length`, `area` | The `length` and `area` measurements. |
| `method` | The operation's method. |
| `is_final` | Whether the solid state is the final state. |

A descriptor resolves to exactly one entity in the state scope. A clue
reference states one condition (`prompt-content.md` §4.2), so a clue's
descriptor uses one filter; an evidence descriptor may need more than one to
name the answer entity.

## 4. Answer parameters

The oracle schema's `answer_parameter` has three variants. They are the record's
answer to a gap in [`03b/b-answer-semantics.md`](../../../03-task-generation/03b-construct-task-definitions/b-answer-semantics.md#answer-resolver):
`answer_parameter` carries "the point for a position or a membership, and the
category for a topology change", and is null otherwise.

| Parameter kind | Carries | Why |
|---|---|---|
| `membership_point` | The point the probe classifies. | The point is the question parameter and the probe input, bound once. |
| `position_point` | The point kind (`face_centroid`, `edge_midpoint`, `vertex_point`, `region_centroid`, `solid_state_centroid`). | The coordinates are the answer. Storing them in the parameter would render the answer into the prompt. |
| `topology_category` | `face`, `edge`, or `vertex`. | The question declares which count changes. |

The membership and topology-category rows are already in `03b`. The position
row sharpens an ambiguity: "the point for a position" reads as coordinates,
which are the answer.

A `Distance` or `Angle` answer has no parameter and no row in the table. A pair
answer reads the reference set bound by a task clue
([`task-structure.md` §2.2](../../../../../requirements/task-structure.md#22-task-clue),
[`b-answer-semantics.md`](../../../03-task-generation/03b-construct-task-definitions/b-answer-semantics.md#answer-resolver)),
and the question names that reference
([`prompt-content.md` §3](../../../../../requirements/prompt-content.md#3-question)):
it cites the clue by category only when the clue names one set of that category,
and otherwise names the reference phrase. The answer takes the nearest member,
so a multi-member set still yields one value. The earlier
`distance_reference` and `angle_reference` variants were removed on 2026-11-27 when
`MC-67` resolved the pair endpoint this way. A record that stores the second
entity in `answer_parameter` is now invalid.

## 5. Units and canonical text

A record's `answer.unit` is the graph measurement unit of the expected answer:
`millimetre`, `square_millimetre`, `cubic_millimetre`, `degree`, or `unitless`.
It is test data used to choose the answer's tolerance. It is not a release
column.

CadQuery is unitless, so the release has no per-row answer unit and no prompt
renders one. The dataset card states the one convention a consumer needs: 1 CAD
unit = 1 mm, areas mm², volumes mm³, angles degrees. Display spellings such as
`mm`, `mm^2`, `mm^3`, and `deg` are not record keys.

## 6. How to add a record

1. Choose a program and a task description that fills a coverage cell.
2. Write the answer and the clue chain by hand, from the program and the graph
   contract. Do not derive them from the constructor.
3. Write the gold query. It must use plain CadQuery and OCP, not the graph and
   not constructor code.
4. Check the gold query:

   ```bash
   uv run python tools/manual-verification/verify_task_oracles.py --record <slug>
   ```

   The check runs every selected record in one Python process, so CadQuery is
   imported once for the batch instead of once per record
   ([devtools conventions](../../../../devtools/README.md#conventions)). A query
   that exits non-zero, prints more or fewer than one non-empty line, or prints
   anything other than `expected_stdout` fails, and a failing check writes
   nothing.
5. Record the check:

   ```bash
   uv run python tools/manual-verification/verify_task_oracles.py --record <slug> --write
   ```

   `--write` records the environment, the observed stdout, and the date on the
   records that pass, and rewrites only the files whose bytes change. It never
   changes the answer; a query that prints something else is a failure.
6. Read the record as a reviewer: is the task unambiguous, is the clue chain
   true, is the answer the one a careful human would give? The
   [dataset browser](../../../../devtools/dataset-browser.md#gold-oracles) opens every
   record with its program render, answer, clue chain, gold query, coverage, and
   exclusions. Accept the record when the answer is yes:

   ```bash
   uv run python tools/manual-verification/verify_task_oracles.py --record <slug> \
     --accept --by <your name>
   ```

   `--accept` writes `verified`, `verified_by`, and `verified_at` and runs no
   gold query, so acceptance costs one kernel import for the version stamp
   rather than one per record. It refuses a record whose
   gold-query check is not `passed`, whose recorded stdout differs from
   `expected_stdout`, or whose recorded environment differs from the current one;
   those need a `--write` first. It does not rewrite `rationale`: that sentence
   is the reviewer's argument for the record, not a restatement of the audit
   fields. Edit it in the same commit when it still says the review is pending.

## 7. What the test proves

**Status:** `missing`. The `03b` Go test (`generator/internal/stages/03-task-generation/03b-construct-task-definitions/03b_construct_task_definitions_test.go`)
lands with the constructor and proves:

- every record is discoverable and its slug matches the file stem;
- the record has exactly the documented shape; a misspelled or extra field
  fails;
- `program_sha256` and `program_id` match the program text;
- the gold-query hash matches the code, `expected_stdout` matches the answer
  value, and the recorded check passed;
- the clue orders, narrowing counts, step count, and coverage cell are
  internally consistent;
- the answer value, tolerance, scoring rule, parameter, and equivalent set are
  consistent with the answer meaning and format;
- when CadQuery is installed, every gold query prints its `expected_stdout`.

The last check needs CadQuery and OCP; it is skipped when the Python
interpreter or CadQuery is absent. Run `verify_task_oracles.py` by hand before a
release.

It does not prove that `03b` reproduces the record. That test is a TDD pin in
[`03b-construct-task-definitions`](../../03-task-generation/03b-construct-task-definitions/README.md)
and lands with the constructor. It also does not prove that the record is the
only valid reading of the task; that is the owner review.

## 8. Records

| Slug | Task | Answer |
|---|---|---|
| [`box-volume`](box-volume.json) | What is the volume of the target solid state? | `1000` |
| [`box-face-count`](box-face-count.json) | How many faces does the target solid state have? | `6` |
| [`box-membership-inside`](box-membership-inside.json) | Is the point `(0, 0, 0)` inside the target solid state? | `true` |
| [`box-membership-outside`](box-membership-outside.json) | Is the point `(1, 1, 3)` inside the target solid state? | `false` |
| [`box-extent`](box-extent.json) | What is the bounding box of the target solid state? | `(-5, -10, -2.5)`–`(5, 10, 2.5)` |
| [`box-with-hole-top-face-area`](box-with-hole-top-face-area.json) | What is the area of the target face? | `187.4` |
| [`box-with-hole-top-face-centroid`](box-with-hole-top-face-centroid.json) | What is the area centroid of the target face? | `(0, 0, 2.5)` |
| [`box-top-bottom-distance`](box-top-bottom-distance.json) | What is the shortest distance between the target face and the face touching the bottom of the axis-aligned bounding box? | `5` |
| [`box-top-front-angle`](box-top-front-angle.json) | What is the angle between the target face and the face touching the left of the axis-aligned bounding box? | `90` |
| [`box-bottom-face-area-by-angle`](box-bottom-face-area-by-angle.json) | What is the area of the target face? | `200` |
| [`box-with-hole-edge-length`](box-with-hole-edge-length.json) | What is the length of the target edge? | `12.57` |
| [`box-with-hole-material-change`](box-with-hole-material-change.json) | What volume does the `cutBlind` operation remove? | `-25.13` |
| [`box-with-hole-topology-change`](box-with-hole-topology-change.json) | How many faces does the `cutBlind` operation add? | `2` |

## 9. Coverage

The P0 answer meanings and formats. A cell with a record is pinned; a gap is a
work item before the release claims that cell.

| Answer meaning | Native format | Record | Status |
|---|---|---|---|
| Identity | Multiple choice | — | **Gap.** Needs a program whose penultimate candidate set has at least five real candidates. A two-clue identity task on the box leaves fewer than five. |
| Volume | Number | `box-volume` | Covered |
| Area | Number | `box-with-hole-top-face-area` | Covered |
| Length | Number | `box-with-hole-edge-length` | Covered |
| Distance | Number | `box-top-bottom-distance` | Covered |
| Angle | Number | `box-top-front-angle` | Covered |
| Count | Integer | `box-face-count` | Covered |
| Membership | Yes or no | `box-membership-inside`, `box-membership-outside` | Covered, both labels |
| Position | 3D coordinate | `box-with-hole-top-face-centroid` | Covered |
| Extent | Bounding box | `box-extent` | Covered |
| Material change | Number | `box-with-hole-material-change` | Covered |
| Topology change | Integer | `box-with-hole-topology-change` | Covered |
| Rank | Integer | — | P1 |
| CadQuery workplane state | Structured object | — | P1 |
| Validity | Yes or no | — | P2 |

Target categories:

| Category | Records | Status |
|---|---|---|
| Solid state | volume, face count, membership (both labels), extent | Covered |
| Face | area, position, distance, angle | Covered |
| Edge | length | Covered |
| Operation | material change, topology change | Covered |
| Feature, vertex, CadQuery profile, CadQuery workplane, region, scalar value | — | **Gap.** Each needs at least one record before the P0 release claims it. |
| CadQuery program, edge endpoint, path, path point, path segment, CadQuery selector result | — | P1 |

Clue types:

| Clue type | Records | Status |
|---|---|---|
| Property | area (measurement range), position (categorical feature), angle (measured direction) | Covered |
| Relation | edge length (named `has_edge`), bottom-face area (pair angle), top-bottom distance (pair angle) | Covered |
| Comparison | front-face angle (area below the left face) | Covered |
| Provenance | — | **Gap.** |
| Aggregation | — | P1 |

Clue reduction forms:

| Form | Records | Status |
|---|---|---|
| `filtered` | edge length, bottom-face area, top-bottom distance, front-face angle | Covered |
| `selected_in_earlier_clue` | — | **Gap.** |
| `aggregated` | — | P1 |
| `cross_state` | — | P2 |

Answer formats:

| Format | Records | Status |
|---|---|---|
| Number | volume, area, length, distance, angle, material change | Covered |
| Integer | count, topology change | Covered |
| Yes or no | membership (both labels) | Covered |
| 3D coordinate | position | Covered |
| Bounding box | extent | Covered |
| Multiple choice | — | **Gap.** Same program problem as identity. |
| Structured object | — | P1 |

Task reasoning step count:

| Steps | Records | Status |
|---|---|---|
| 1 | volume, count, membership (both labels), extent, material change, topology change | Covered |
| 2 | area (pair angle), position, distance | Covered |
| 3 | edge length, angle | Covered |
| 4–5 | — | **Gap.** |
| 6–10 | — | P1, gated by the dataset PRD section 6.1 |

## 10. What this set does not do

- It does not verify every release row. It pins the supported vocabulary; the
  release still needs the review gate and, if the owner accepts it, a
  release-wide re-derivation.
- It does not prove the prompt renders. That is `04`.
- It does not prove the constructor's clue search is complete. It proves the
  constructor can reproduce the cases a human wrote down.
- It does not replace the extraction-graph oracles. Those calibrate the graph;
  these calibrate the task and the answer.
