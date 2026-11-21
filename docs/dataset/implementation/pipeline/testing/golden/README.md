# Golden records

**Parent:** [`README.md`](README.md).

**Status:** draft, 2026-11-20. Defines the fixed golden-record file format for
task construction and the first record. It closes `MC-42`.

## 1. What a golden record is

A golden record is a checked-in, versioned JSON file that pins the expected
output of `03b` construct task definitions for one program and one task
description. It is the fixed comparison target for the construction end-to-end
test. It is not a pipeline artifact and not a plan document: the constructor
never reads it, and the release never contains it.

The record holds:

- the normalized program text and its identity;
- the construction input that makes the output deterministic;
- the task description the constructor was given;
- the expected canonical clue sequence, with its narrowing counts;
- the expected answer and its evidence.

A plan narrative is not a golden record. A plan can describe a chain that the
graph does not support; a golden record is data, and the test fails when the
constructor disagrees with it.

## 2. Location and naming

One file per golden task:

```text
pipeline/testing/golden/<golden_id>.json
```

`<golden_id>` is a lower-case slug (`box-with-hole`). It is stable and matches
the file stem. The file is UTF-8 JSON with a trailing newline. Indentation is
not identity-bearing: the test parses the file. The program text inside the
record is the canonical bytes; the record file itself is not hashed.

The first record is [`golden/box-with-hole.json`](box-with-hole.json).

## 3. File shape

The top-level mapping has exactly seven keys:

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | integer | Record format version. Bumped when the record shape changes. |
| `golden_id` | string | Stable slug; matches the file stem. |
| `construction` | object | The constructor input that makes the expected output deterministic. |
| `program` | object | The normalized program and its identity. |
| `task` | object | The task description given to the constructor. |
| `clues` | list | The expected canonical clue sequence. |
| `answer` | object | The expected answer and evidence. |

Unknown keys are rejected at every level. A misspelled key is a validation
error, not a silently ignored field.

### 3.1 `construction`

| Key | Type | Meaning |
|---|---|---|
| `constructor_version` | string | The typed constructor set that produced the definition. |
| `construction_seed` | integer | The seed the constructor sampled with. |
| `definition_schema_version` | string | The definition schema the expected fields use. |
| `graph_schema_version` | string | The graph schema the record was written against. |

The record does not carry `runtime_extraction_sha256`; it depends on the
CadQuery environment and is not portable. The end-to-end test compares
construction content, not the runtime hash.

### 3.2 `program`

| Key | Type | Meaning |
|---|---|---|
| `program_id` | string | `cadqaprog:<program_sha256>`. |
| `program_sha256` | string | SHA-256 over the canonical text bytes. |
| `text` | string | The normalized program text from `01d`, with exactly one trailing newline. |

`program_sha256` is computed over the UTF-8 bytes of `text`, not over the JSON
serialization. The test recomputes it, so an edited program without a new hash
fails.

### 3.3 `task`

| Key | Type | Meaning |
|---|---|---|
| `target_category` | string | The task target category. Values are the snake-case code identifiers for the approved terms in [`../../../../requirements/task-structure.md`](../../../../requirements/task-structure.md). |
| `state_scope` | string | `final` in P0 (`DS-REQ-08`). |
| `possible_answer_count` | integer | Size of the initial possible-answer set for the target category in the state scope. |
| `task_reasoning_step_count` | integer | Clue steps plus the answer step, if any. |
| `answer_meaning` | string | What the answer is about, from `03b`. |
| `native_answer_format` | string | The answer meaning's native format. |
| `answer_format` | string | The format the prompt requests. |
| `geometry_required` | boolean | Whether at least one clue depends on the built shape. |

`answer_format` equals `native_answer_format` unless the task uses multiple
choice, which is a presentation wrapper valid for every answer meaning.

### 3.4 `clues`

One entry per clue, in canonical order. The record does not carry a separate
`clue_operand_form_profile`: the ordered `clue_operand_form` values are the
profile, so the two cannot disagree.

| Key | Type | Meaning |
|---|---|---|
| `order` | integer | 1-based canonical position. |
| `clue_type` | string | `property`, `relation`, `comparison`, `aggregation`, or `provenance`. |
| `clue_operand_form` | string or null | `named`, `selected`, `aggregated`, or `cross_state`; null when the clue has no reference. |
| `statement` | string | The clue in words, for review. It is not rendered by `04` and not compared. |
| `subject` | object | The binding the clue constrains. The first record uses `{"kind": "target"}`. |
| `check` | object | The typed check from `03b`. |
| `narrows` | object | `before` and `after` possible-answer counts. |

The `check` shape follows the clue type in `03b`. A relation clue carries
`relation_type` and `object`; a property clue carries `measurement`,
`comparator`, and `threshold` or `range`; a comparison clue carries
`measurement`, `comparator`, and `reference`.

A relation clue also carries a `direction` when the graph relation is
directional:

| Value | Meaning |
|---|---|
| `subject_to_object` | The graph relation runs from the clue subject to the check object. |
| `object_to_subject` | The graph relation runs from the check object to the clue subject. |

The first record uses `has_edge`, which runs from a face to an edge, so its
direction is `object_to_subject`.

### 3.5 `answer`

| Key | Type | Meaning |
|---|---|---|
| `gold_answer` | string | Canonical text; the same text `TaskDefinition.gold_answer` holds. |
| `choices` | list of struct `{label, candidate}`, both strings | The multiple-choice pool; empty unless the answer format is multiple choice. |
| `answer_unit` | string or null | `mm` or null. |
| `tolerance` | object or null | Decoded tolerance; null for an exact answer. |
| `scoring_rule` | string | `exact`, `numeric_tolerance`, or `structured_exact`. |
| `answer_schema_version` | string | The answer representation version. |
| `answer_evidence` | object | The typed evidence. |

`tolerance` is decoded for readability. The definition stores it as canonical
JSON text; the end-to-end test canonicalizes the record's object before
comparing.

`answer_evidence` has exactly five keys:

| Key | Type | Meaning |
|---|---|---|
| `evidence_kind` | string | `measured` or `derived`. |
| `evidence_rule` | string | The resolver rule that produced the answer. |
| `evidence_refs` | list | The graph references the rule used. |
| `answer_equivalent_set` | list | One entry per remaining candidate, with its subject and answer. |
| `point_probe` | object or null | The point probe for a membership answer; null otherwise. |

Every `answer_equivalent_set` entry has exactly `subject` and `answer`. The
`subject` is an entity descriptor; the `answer` is canonical text. The set is
non-empty, every entry gives the answer value under `same_answer`, and an
identity answer requires exactly one entry (`DS-REQ-15`).

## 4. Entity descriptors

The record never stores a node ID. A graph entity is written as a descriptor:

```json
{
  "category": "edge",
  "filters": {
    "curve_kind": "circle",
    "centroid_z": "2.5"
  }
}
```

`category` is the entity category. `filters` is an equality filter over graph
fields. Numeric filters are canonical decimal text. The first record uses
`surface_kind`, `curve_kind`, and `centroid_z`; the filter set grows only when a
new record needs it.

| Filter | Graph field |
|---|---|
| `surface_kind` | `face_surface_kind` |
| `curve_kind` | `edge_curve_kind` |
| `centroid_x`, `centroid_y`, `centroid_z` | Components of the `centroid` measurement. |
| `length` | The `length` measurement. |
| `area` | The `area` measurement. |

A descriptor must resolve to exactly one entity in the state scope. Zero
matches or several matches is a record defect, not a reason to pick one. The
end-to-end test resolves the descriptor and compares the resolved entity, so a
change to an entity ID does not change the record.

Descriptors are used because a node ID is an implementation detail. A record
that stored one would fail on a harmless ID change and would not explain which
entity it meant.

## 5. Versioning and change rules

`schema_version` is the record format version. Bump it when a required key, a
field type, or a descriptor rule changes. A schema change is a new record
revision; the old record is not edited in place.

A record's expected values change only with a deliberate construction change:

- a constructor or definition-schema change that changes the expected chain,
  answer, or evidence;
- a graph-schema change that changes the entity set or a measurement;
- a program normalization change that changes `program_sha256`.

The diff is reviewed like code. A failing golden record is a regression until
the review establishes that the construction contract changed. Do not edit the
record to match the constructor without a contract change.

The `construction` block pins the input. A version or seed bump is a new record
revision, not an in-place edit.

## 6. Comparison

The construction end-to-end test in [`03b-construct-task-definitions.md`](../03-task-generation/03b-construct-task-definitions/README.md)
constructs a definition from the record's program and task description, using the
pinned construction input, and compares it field by field:

- the task description fields in `task`;
- each clue's `order`, `clue_type`, `clue_operand_form`, `subject`, `check`, and
  `narrows`;
- the answer's `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`,
  `answer_schema_version`, and `answer_evidence`.

The test compares a descriptor by resolving it against the graph and comparing
the resolved entity's canonical identity. It does not compare a node ID.

The test ignores fields that are not construction content:

| Field | Why it is ignored |
|---|---|
| `task_id` | It is derived from the canonical identity, which the compared fields already cover. |
| `definition_sha256`, `answer_sha256` | They include versions and the runtime extraction hash, which are not portable across environments. |
| `cadevolve_program_family_id`, `split`, `subset` | `03a` assigns them. |
| `provenance` | It records the input versions; `construction` pins the ones the record controls. |

The test compares numeric answers under `same_answer` at the stated precision;
strings compare exactly. It compares the canonical clue order as written; it
does not reorder clues.

## 7. The first record: box with hole

[`golden/box-with-hole.json`](box-with-hole.json) pins the box-with-hole
program:

```python
import cadquery as cq

wp = cq.Workplane("XY")
box = wp.box(10, 20, 5)
top = box.faces(">Z")
plane = top.workplane()
hole = plane.circle(2)
result = hole.cutBlind(-2)
```

The task is a three-step edge-length task: two relation clues, then the answer
step. The canonical chain is:

| Step | Clue | Set after | Clue type | Operand form |
|---|---|---|---|---|
| 1 | The edge is on the top face of the box. | 5 edges | Relation | `named` |
| 2 | The edge is on the cylindrical face of the hole. | 1 edge | Relation | `named` |
| Answer | Return the length. | `12.57` | — | answer meaning: length |

The final set is the top circular edge of the hole. Its length is
`2π·2 = 12.566...`, rounded to `12.57` at four significant figures. The
`answer_equivalent_set` is a singleton.

The counts are the actual graph counts. The final solid has 15 edges, not 14:
the cylindrical face carries a periodic seam edge in addition to the two
circular edges. Clue 1 selects the five edges of the top face; the seam edge is
not one of them. Clue 2 then selects the one edge shared by the top face and
the cylindrical face.

The plan's worked example counted 14 edges and expected clue 2 to leave two
circular edges. That count is wrong for the BRep. The plan's third clue is also
redundant. After clue 2 only one edge remains, so the comparison cannot narrow.
Even in the plan's idealized two-circle set, both circles have the same length,
so selecting the top one would not change the answer. The valid P0 length task
is three steps, not four. `DS-REQ-15` still holds: the answer-equivalent set is a
singleton here, and the general rule is tested by the construction property
tests.

## 8. What the test proves

`tests/test_golden_records.py` proves:

- every record is discoverable and its `golden_id` matches the file stem;
- the record has exactly the documented keys; a misspelled or extra field
  fails;
- `program_sha256` and `program_id` match the canonical program text;
- the clue orders, narrowing counts, step count, and operand forms are
  internally consistent;
- the answer-equivalent set is non-empty, every entry gives the gold answer,
  and every entry has an evidence reference;
- the tolerance and scoring rule are consistent with the answer.

It does not prove the record matches the constructor. That is the end-to-end
test in [`03b-construct-task-definitions.md`](../03-task-generation/03b-construct-task-definitions/README.md). It does not prove the
counts against the graph. That is the same end-to-end test.

## 9. What is not here

- The construction algorithm:
  [`../03-task-generation/03b-construct-task-definitions/a-construction.md`](../../03-task-generation/03b-construct-task-definitions/a-construction.md).
- The definition schema and validity rules:
  [`../03-task-generation/03b-construct-task-definitions/README.md`](../../03-task-generation/03b-construct-task-definitions/README.md).
- The construction test contract: [`03b-construct-task-definitions.md`](../03-task-generation/03b-construct-task-definitions/README.md).
- Release validation:
  [`../05-validate-and-export-release.md`](../../05-validate-and-export-release.md).
