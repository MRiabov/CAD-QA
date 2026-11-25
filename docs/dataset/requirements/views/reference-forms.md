# Reference forms

**Status:** derived view, 2026-11-25. Every thing a prompt can mention, and the
phrases that name it. The rules are [`prompt-content.md`](../prompt-content.md)
sections 3 and 4 and [`task-structure.md`](../task-structure.md) sections 2.1 and
2.2; the copy is `generator/config/prompts.yaml`. This document owns no rule.

Every placeholder that names a thing — `<target>`, `<category>`, `<operation>`,
`<CadQuery profile>`, `<reference>` — is filled from these tables.

A CadQuery workplane is the exception, and
[A CadQuery workplane](#a-cadquery-workplane) says why.

None of them is a bare name: each is a set reduced by the condition the phrase
states, so "the cutBlind operation with depth 3" and "a face whose area is greater
than 10" are the same sort of expression.

A form appears under the release scope that defines it. P0 is the first release;
P1 and P2 are defined but have not shipped. `missing: …` means no phrase exists at
that scope, and the entry names what is absent.

**Reading the phrase column.** The article is chosen at render time from what the
description selects in the program: `the` for exactly one element, `a` for a
condition that selects several. The examples use `a` because they are forms, not
program text. A set bound by an earlier clue is plural.

## P0

### The task target

The question names the category and the answer meaning, and states no condition.

| Category | Phrase | Example |
|---|---|---|
| Face | the target face | What is the area of the target face? |
| Edge | the target edge | What is the length of the target edge? |
| Vertex | the target vertex | What is the position of the target vertex? |
| Solid state | the target solid state | What is the volume of the target solid state? |
| Operation | the target operation | Which operation satisfies these conditions? |
| CadQuery profile | the target CadQuery profile | What is the area of the target CadQuery profile? |
| CadQuery workplane | the target CadQuery workplane | Which CadQuery workplane satisfies these conditions? |
| Region | the target region | What is the volume of the target region? |
| Feature | the target feature | Which feature satisfies these conditions? |

Vertex, CadQuery profile, CadQuery workplane, Region, and Feature are P0 and have
no task yet; the task-construction coverage view records those gaps.

An identity answer is a multiple-choice label, so an operation target is
answered by choosing a label; a CadQuery workplane target, if it ships, is too.
The LLM model never writes a variable name.

A scalar target is a measurement instance, not a phrase. The question still names
the subject's category ("What is the area of the target face?"), never "the
target measured value". In P0 a measurement of an entity records the entity as
the target, and no P0 task uses a scalar target (`task-structure.md` section
2.1).

A CadQuery workplane target can be answered by identity. Its other answer, the
`CadQuery workplane state`, is the frame — origin, x direction, and normal — and
is P1 with no question template yet.

### A face

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Face surface kind | a `<face surface kind>` face | a cylindrical face | the face surface kind has an adjective; `other` has none |
| Position | a face touching the `<position>` of the axis-aligned bounding box | a face touching the top of the axis-aligned bounding box | the face lies in that extreme plane |
| Direction, shorthand | a face facing `<axis>` | a face facing +z | the outward normal is along that axis |
| Direction, measured | a `<category>` whose outward normal is `<comparator>` `<value>` degrees of `<axis>` | a face whose outward normal is within 45 degrees of +z | the face is planar; the threshold sits between two candidate angles |
| Measurement | a `<category>` whose `<metric>` is `<comparator>` `<value>` | a face whose area is greater than 10 | one condition; the threshold sits between two candidate values |
| Centroid coordinate | a `<category>` whose `<metric>` is `<comparator>` `<value>` | a face whose centroid X coordinate is less than 0 | one condition; the metric names the axis |
| Earlier clue | the faces from clue `<n>` | the faces from clue 1 | the clue is not the first |
| Operation that created it | — | — | `missing`: no reference phrase; only the provenance clue says "created by" |

### An edge and a vertex

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Measurement | an `<category>` whose `<metric>` is `<comparator>` `<value>` | an edge whose length is greater than 10 | one condition; the threshold sits between two candidate values |
| Earlier clue | the edges from clue `<n>` | the edges from clue 1 | the clue is not the first |
| Operation that created it | — | — | `missing`: no reference phrase; attribution is also documented for faces only |

A vertex target is reached by containment in P0 ("an endpoint of an edge whose
length is greater than 10") and by a measurement clue on its own centroid in P0;
no phrase names a vertex as a reference. A literal coordinate would be a lookup
rather than a condition, and the graph need not carry a vertex at exactly that
point.

### A solid state

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Final state | the target solid state | the target solid state | the final state only |

In P0 the final solid state is the only one, so a solid state target carries no
clue: the task is one step and the question asks for a measurement of the final
state. A measurement threshold cannot narrow it, because there is nothing else to
narrow it to.

### An operation

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Method, indefinite | a `<method>` operation | a cutBlind operation | always |
| Method, definite | the `<method>` operation | the cutBlind operation | the program calls that method once |
| Method and argument | the `<method>` operation with `<argument>` | the cutBlind operation with depth 3 | the argument selects one |
| Place in the program | the `<method>` operation that appears last in the program | the box operation that appears last in the program | the program has a clear order |
| Feature it creates | — | — | `missing`: no reference phrase names a CAD feature |

The CadQuery workplane an operation runs on is not a discriminator. A program has
one named CadQuery workplane in almost every case, so the phrase would describe
the whole program rather than select an operation.

A phrase in this table refers to an operation; it does not assert one. No
predicate states the method, so a clue narrows an operation target by its effects
only: `volume change` and `topology change`.

### A CadQuery workplane

No reference form names a CadQuery workplane. A program builds on one named
CadQuery workplane in almost every case, so "the XY CadQuery workplane" selects
the whole program rather than a set of candidates; a face-derived or custom frame
has no phrase at all. A CadQuery workplane is still a graph entity, is named by
the `uses` and `derived_from` relations, and carries the `CadQuery workplane
state` answer at P1.

Whether a CadQuery workplane ships as a task target in the first release is open
in [`task-structure.md`](../task-structure.md) section 8. It is a task target
category in section 2.1; if it ships, its target phrase is
"the target CadQuery workplane" and it carries no clue.

### A CadQuery profile

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| CadQuery profile kind | a `<CadQuery profile kind>` CadQuery profile | a circular CadQuery profile | the CadQuery profile kind is one of the five with a noun |
| Measurement | a `<category>` whose `<metric>` is `<comparator>` `<value>` | a CadQuery profile whose area is greater than 10 | one condition |
| Unknown outline | — | — | `missing`: `other` has no noun, so a provenance clue cannot name that CadQuery profile |

### A region

| Thing | Phrase | Example | Usable when |
|---|---|---|---|
| Region | — | — | `missing`: no reference phrase, so a clue cannot name one |

### A point

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Coordinate literal | `(x, y, z)` | Is the point (0, 0, 0) inside the target solid state? | a membership question; the point is the question parameter, and membership is point-in-solid-state only |
| Point as a distance endpoint | — | — | `missing`: the distance meaning allows a point as one side, and no reference form or question template supplies one |

### Not a form

A variable name, a graph identifier, "the top face", "the annular face". None of
these is a condition, so none narrows the candidates.

### Relations are not reference forms

A relation is asserted of the target, not used to name an entity: "The target
face is adjacent to a face facing +z". The other side of the relation is a
reference and is built from the tables above. A measured-angle relation is the
same: the target and the reference are the two entities of the `Angle`
measurement, and "parallel" and "perpendicular" are renderings of 0 or 180 and
90 degrees, not relation values.

`parallel_to` and `perpendicular_to` are not relations. Three facts about the
relation table in [`graph-content.md`](../graph-content.md) section 3.2 follow:

- `adjacent_to` connects a face to a face only. A face and an edge are never
  adjacent in the graph, so "a face adjacent to an edge" does not exist.
- Containment is a clue, not a reference: "The target edge is an edge of a
  cylindrical face." It reads with the target on the contained side, because the
  phrase is prepositional (`an edge of`, `an endpoint of`).
- `has_face` has no phrase. It would be true of every face in the bound solid
  state and would narrow nothing.

## P1

### The task target

The P1 target categories have a question phrase but no task yet.

| Category | Phrase | Example |
|---|---|---|
| CadQuery program | the target CadQuery program | Which CadQuery program satisfies these conditions? |
| Edge endpoint | the target edge endpoint | Which edge endpoint satisfies these conditions? |
| Path | the target path | Which path satisfies these conditions? |
| Path point | the target path point | Which path point satisfies these conditions? |
| Path segment | the target path segment | Which path segment satisfies these conditions? |
| CadQuery selector result | the target CadQuery selector result | Which CadQuery selector result satisfies these conditions? |

### A face

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Extreme | the `<extreme>` of the faces from clue `<n>` | the largest of the faces from clue 1 | an `aggregated` reference; a rank reference has no phrase while `task-structure.md` section 8 leaves its direction words open |

### An edge and a vertex

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Extreme | — | — | `missing`: no phrase for an aggregated edge or vertex reference; only the face form exists |

### A solid state

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| After an operation | the solid state after `<operation>` | the solid state after the cutBlind operation that appears last in the program | one intermediate state, and the operation description follows the determiner rule |

A solid state is identified by the operation that produced it, so a second state
is nameable only when that operation is. Two `cutBlind` calls make "the solid
state after the cutBlind operation" ambiguous; the description needs an argument
("with depth 3") or the place in the program.

### A path and a CadQuery selector result

| Thing | Phrase | Example | Usable when |
|---|---|---|---|
| Path | — | — | `missing`: P1 scope, no reference phrase |
| CadQuery selector result | — | — | `missing`: P1 scope, no reference phrase |

## P2

### A solid state

| Form | Phrase | Example | Usable when |
|---|---|---|---|
| Before an operation | the solid state before `<operation>` | the solid state before the cutBlind operation that appears last in the program | the before side of a declared pair, and the operation description follows the determiner rule |

The before state is named by the operation it precedes, so the same determiner
rule applies.
