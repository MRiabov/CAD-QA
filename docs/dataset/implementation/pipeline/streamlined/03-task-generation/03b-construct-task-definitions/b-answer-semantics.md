# 03b/b answer semantics — step, format, resolver, choice pool

> Authoritative: `../../../03-task-generation/03b-construct-task-definitions/b-answer-semantics.md`
> Models: `../../models/03-task-generation.md`

## 1 — Answer step and native format

READ:

- the bound target and the penultimate answer candidate set
- `answer_meaning` from the quota target

TRANSFORM:

- choose the answer step and native format from `answer_meaning`; identity → multiple choice; volume, area, length, distance, angle → number; count, rank → integer; membership, validity → yes or no; position → 3D coordinate; extent → bounding box; CadQuery workplane state → structured object; material change → number or integer; topology change → integer
- multiple choice is a presentation wrapper valid for every answer meaning; `native_answer_format` records the meaning's format and `answer_format` records the requested wrapper; the plan's `answer_format` target selects the wrapper, and a format that cannot express the meaning is not used
- the answer step exists unless the answer is the target identity

WRITE:

- (none)

## 2 — Multiple-choice pool

TRANSFORM:

- the pool has 5-7 entries, ordered by a stable hash of `(task_id, candidate)` and labelled `A` to `G` in that order
- each entry is `label, candidate, distinguishing_facts, error_mode`
- every candidate comes from the penultimate answer candidate set and no two are equal under `same_answer`; identity uses entities, a numeric answer uses distinct answers
- `gold_answer` is the label, and the answer value is the entry's `candidate`
- `choice_pool_valid` holds when the pool has 5-7 entries; `gold_answer` is one of the labels; every `candidate` is valid under `answer_format`; no two candidates are equal under `same_answer`; every candidate comes from the penultimate answer candidate set; every `distinguishing_facts` is a geometric or construction fact, unique across entries, and contains no variable name, internal identifier, or answer value; labels are contiguous from `A` with no repeat
- a pool with fewer than five real options rejects the task; do not trim or pad it
- P2 adds `near_miss_valid`: every near-miss fails a clue or the answer step, and its `error_mode` is recorded

WRITE:

- (none)

## 3 — Resolve the answer

TRANSFORM:

- `resolve_answer(answer_meaning, bound_target, answer_parameter, penultimate_set)` → `answer_value, answer_evidence`
- identity → the entity shared by the whole answer-equivalent set; evidence = the set and the binding
- volume → kernel volume of the bound solid state; area → kernel area of the bound face or profile; length → kernel length of the bound edge or path segment; distance → the smallest stored `distance` between the bound target and any member of `reference_set`, taking the single member when the set holds one; evidence = the target, the reference member, and the measurement row
- angle → the graph angle for the pair; evidence = the graph measurement
- count → the size of the bound set
- membership → `is_inside(solid_state, point)` from the point probe; answer is inside or outside; a point within the clear-case margin is not used; evidence = the point, its classification, the solid state, the distance to the nearest face, the classifier, and the margin; `answer_parameter` is that same probe point, bound once, and `04` renders the question from it
- material change → the signed volume or count the bound operation adds or removes; a cut answers a negative number; `answer_parameter` is null
- position → the declared point (face area centroid, edge midpoint, vertex point, region center of mass, or state center of mass)
- extent → minimum and maximum corner of the bounding box in the program frame
- topology change → the signed change in the declared category
- when the task is multiple choice, `gold_answer` is the pool label whose `candidate` equals `answer_value`; the answer value stays in `answer_evidence` and `choice_pool`
- `answer_parameter` is null unless the meaning declares a point (position, membership) or a category (topology change); material change declares no parameter
- evidence is `evidence_kind (measured | derived), evidence_rule, evidence_refs, answer_equivalent_set, point_probe`; `answer_equivalent_set` holds one entry per remaining candidate as `{subject, answer}`, and every entry equals the answer value under `same_answer`
- an entry's `subject` is a graph entity for an entity target and the measurement name for a scalar target; `04` renders the question and `05` the review pack from it
- a missing target or a missing graph measurement rejects the task; never guess or approximate

WRITE:

- (none)

## 4 — Answer equality

TRANSFORM:

- `same_answer`: identity is the same entity; count and rank exact integers; number, coordinate, and bounding box at canonical rounding, 4 significant figures by default; membership and validity label exact; material change the same added and removed volume at the stated precision; topology change the same face, edge, and vertex counts and the same changed set; structured object componentwise
- the precision comes from the answer format and the release scoring rule: integer, count, and rank exact; number, coordinate, and bounding box canonical rounding; yes or no, membership, and validity label equality; structured object componentwise

WRITE:

- (none)
