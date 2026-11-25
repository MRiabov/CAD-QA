# Answer semantics

**Parent:** [`README.md`](README.md).

## Answer step and answer format

The answer step produces the answer after the target is identified. It is absent
only when the answer is the target identity; otherwise it is one task reasoning
step.

The answer meaning determines the native answer format:

| Answer meaning | Native answer format |
|---|---|
| Identity | Multiple choice. |
| Volume, area, length, distance, angle | Number. |
| Count, rank | Integer. |
| Membership, validity | Yes or no. |
| Position | 3D coordinate. |
| Extent | Bounding box. |
| CadQuery workplane state | Structured object. |
| Material change | Number for a volume effect; integer for a count effect. |
| Topology change | Integer for a count change. |

Multiple choice is a presentation wrapper valid for every answer meaning when
the definition carries enough real choices. The native format is still recorded.
A format that cannot express the meaning is not used; for example, identity is
not returned as a number and position is not returned as a scalar.

The choice pool is a construction output (`TG-8`). Identity answers draw options
from the penultimate answer candidate set; numeric answers draw them from the
distinct answers of that set. Fewer than five real options rejects the task.
`04` renders the pool in the recorded order.

The answer must be produced by CadQuery execution or by an exact derivation from
the program and its geometry, with answer evidence. A guessed or approximate
answer is not valid.

### Multiple-choice choices

A pool entry is typed:

| Field | Meaning |
|---|---|
| `label` | The position label, `A` to `G`. |
| `candidate` | The answer value, as canonical text in the same representation as `gold_answer`. |
| `distinguishing_facts` | The graph facts the choice description is rendered from. |
| `error_mode` | Why a P2 near-miss is wrong. Null in P0 and P1. |

`03b` orders the pool by a stable hash of `(task_id, candidate)` and assigns
labels from the fixed alphabet `A` to `G` in that order. The order and the labels
are therefore construction output: the correct answer is not always in the same
position, no render step chooses a position, and the pool is hashed with its
labels.

For a multiple-choice task, `gold_answer` is the label. A label is a position,
not an answer: the answer value is the `candidate` the label denotes, and
`answer_evidence` records it. `05` validate and export release counts the
candidate, not the label, when it counts distinct answers.

The pool checks run at construction, on the pool:

| Check | Holds when |
|---|---|
| Pool size | At least five entries and at most seven, because the alphabet ends at `G`. Seven is the goal. |
| Correct choice | `gold_answer` is one of the pool labels. |
| Answer space | Every `candidate` is a valid answer under `answer_format`: the same task target category for identity, the same unit and precision for a number, the same frame for a coordinate, and the documented fields for a structured answer. |
| Distinctness | No two entries hold the same answer under `same_answer`. |
| Real candidates | Every entry comes from the penultimate answer candidate set. None is padding. |
| Fact basis | Every entry's `distinguishing_facts` are geometric or construction facts from the graph, not free text. |
| Fact uniqueness | No two entries share the same `distinguishing_facts`. |
| Fact cleanliness | No fact is a variable name or an internal identifier, and no fact states the answer value. |
| Labels | Labels are contiguous from `A`, with no repeat. |
| P2 near-miss | Every near-miss fails at least one task clue or the answer step, and its `error_mode` is recorded. |

The first nine rows are P0. The P2 row is deferred.

`04` renders the descriptions and checks the rendered choice block: one line per
pool entry, in the pool's order, with the pool's labels; the description text
distinct across entries; and no description stating the answer value. A mismatch
is a defect in the template or the renderer, not a reason to reject the task.

`05` rechecks the released pool in the `choices` column: the entry count, the
labels, `same_answer` distinctness, that `gold_answer` is one of the labels, and
that the label's `candidate` is the answer in `answer_evidence`'s
answer-equivalent set. It does not recheck the construction facts, because the
release does not carry the graph.

### Answer resolver

The resolver turns the bound target and the penultimate answer candidate set into
the answer value and its evidence:

```text
resolve_answer(answer_meaning, bound_target, answer_parameter, penultimate_set)
  -> (answer_value, answer_evidence)
```

| Answer meaning | Answer value | Evidence |
|---|---|---|
| Identity | The entity the whole answer-equivalent set shares. | The set and the binding. |
| Volume | The volume of the bound solid state. | Kernel volume. |
| Area | The area of the bound face or profile. | Kernel area. |
| Length | The length of the bound edge or path segment. | Kernel length. |
| Distance | The shortest distance between the bound pair, or between the point and the entity. | Kernel distance. |
| Angle | The graph angle for the pair, with the convention in `graph-content.md`. | Graph measurement. |
| Count | The number of entities in the bound set. | Set size. |
| Membership | Inside or outside, from the point probe. | Probe classification. |
| Position | The declared point: face area centroid, edge midpoint, vertex point, region center of mass, or solid state center of mass. | Kernel point or graph centroid. |
| Extent | The minimum and maximum corner of the bounding box in the program frame. | Graph bounding box. |
| Material change | The signed volume or count the bound operation adds or removes. | Signed volume change or feature count. |
| Topology change | The signed change in the declared category. | Topology change. |

When the task is multiple choice, `gold_answer` is the pool label whose
`candidate` equals this answer value, not the answer value itself. The answer
value stays in `answer_evidence` and in `choice_pool`.

`answer_parameter` is null for every meaning that declares nothing. It carries
the point for a position or a membership and the category for a topology change.
A material change declares no parameter: its sign carries the direction, so a cut
answers a negative number.

The membership point is both the question parameter and the point the probe
classifies, bound once. `04` renders the question from `answer_parameter`, so it
does not parse the evidence to find the point.

P1 and P2 meanings get a row when their implementation scope is built. The
resolver never guesses: a missing target or a missing graph measurement rejects
the task rather than producing an approximate answer.

### Membership answers

A membership answer is computed by `is_inside(solid_state, point)`. The point comes
from a point probe in the graph (`graph-content.md` section 2.2); the task
definition copies its coordinates and its classification, so `03b` never needs a
kernel. The answer is inside or outside. A point within the geometric
clear-case margin of the face surface is not used, because "on the boundary" is a third case
that the binary answer cannot express. The classification is measured evidence
and records the point, the solid state hash, and the classifier.

### Answer evidence

`answer_evidence` is one typed record:

| Field | Meaning |
|---|---|
| `evidence_kind` | `measured` or `derived`, from `graph-content.md` section 4.3. |
| `evidence_rule` | The rule that produced the answer. |
| `evidence_refs` | The graph entity, relation, and measurement references the rule used. |
| `answer_equivalent_set` | The final possible-answer set: one entry per remaining candidate, with its subject and its answer. |
| `point_probe` | The point, its classification, the solid state reference, the distance to the nearest face, the classifier, and the margin it was tested against. Null unless the answer is membership. |

`answer_equivalent_set` is stored so answer uniqueness can be rechecked from the
definition alone, without the graph. The release does not carry the full set; it
carries `answer_equivalent_count` and `answer_equivalent_answer`. Every entry's answer must equal the answer
value under `same_answer`; an identity answer requires exactly one entry. An
entry's subject is a `node_id` for an entity target and the measurement name for
a scalar target.

### Answer equality

`same_answer(left_answer, right_answer)` is the comparison used for answer
uniqueness and for scoring
(`DS-REQ-15`). It is not a margin; it is canonical equality at the answer's stated
precision.

| Answer meaning | `same_answer(left_answer, right_answer)` |
|---|---|
| identity | the two answers are the same entity |
| volume, area, length, distance, angle | same canonical string at the stated precision |
| count, rank | same integer |
| membership | same label: inside or outside |
| validity | same boolean |
| position | same point at the stated precision, component by component |
| extent | same minimum and maximum corner at the stated precision |
| CadQuery workplane state | same origin and frame at the stated precision |
| material change | same added and removed volume at the stated precision |
| topology change | same face, edge, and vertex counts, and the same changed set |

The precision comes from the answer format and the release scoring rule:

| Answer format | Precision |
|---|---|
| integer, count, rank | exact integer equality |
| number, coordinate, bounding box | canonical rounding, 4 significant figures by default |
| yes or no, membership, validity | label equality |
| structured object | componentwise under the same rules |
