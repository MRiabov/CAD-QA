# Clue list

**Status:** derived view, 2026-11-25. A list of clues and the string each one
renders to. Every rule here comes from [`task-structure.md`](../task-structure.md)
section 2.2 and [`prompt-content.md`](../prompt-content.md) section 4. The
implementation contract is
[`prompt-templates.md`](../../implementation/prompt-templates.md)
and the data is `generator/config/prompts.yaml`; both follow the requirements.

This list and the implementation artifacts are derived. If this list disagrees
with a requirement, the requirement is right. If `prompt-templates.md` or
`prompts.yaml` disagrees with a requirement, the implementation is the defect.
The full precedence rule is in [`README.md`](../README.md#precedence).

This list owns no rule and no open question. A missing row is a question for
`task-structure.md` or `prompt-content.md`, not a rule to add here.

A clue string appears under the release scope that defines it. P0 is the first
release; P1 and P2 are defined but have not shipped.

## P0

### Clue strings

| Clue type | Clue | String | Example |
|---|---|---|---|
| Property | Measurement, threshold | `The <target> has a <metric> <comparator> <value>.` | The target face has an area greater than 10. |
| Property | Measurement, range | `The <target> has a <metric> between <min> and <max>.` | The target face has an area between 150 and 190. |
| Property | Face surface kind | `The <target> is <face surface kind>.` | The target face is cylindrical. |
| Property | Angle to an axis | `The angle between the outward normal of the <target> and <axis> is <comparator> <value> degrees.` | The angle between the outward normal of the target face and +z is less than 1 degree. |
| Property | Position | `The <target> touches the <position> of the axis-aligned bounding box.` | The target face touches the top of the axis-aligned bounding box. |
| Relation | Relation, named | `The <target> is <relation> <reference>.` | The target face is adjacent to a face facing +z. |
| Relation | Angle | `The angle between the <target> and <reference> is <comparator> <value> degrees.` | The angle between the target face and the face touching the top of the axis-aligned bounding box is 180 degrees. |
| Comparison | Comparison | `The <metric> of the <target> is <comparator> the <metric> of <reference>.` | The area of the target face is greater than the area of a face touching the bottom of the axis-aligned bounding box. |
| Provenance | Operation | `The <target> was created by the <operation>.` | The target face was created by a cutBlind operation. |
| Provenance | CadQuery profile | `The <target> uses the <CadQuery profile>.` | The target face uses a circular CadQuery profile. |

### Containment

A containment clue reads with the target on the contained side: `The target edge
is an edge of a cylindrical face`, or `The target vertex is an endpoint of an
edge whose length is greater than 10`.

### Phrases for a second entity

| Form | Phrase | Example |
|---|---|---|
| `filtered` | a condition over the category | a face facing +z, a cylindrical face, a face touching the top of the axis-aligned bounding box |
| `selected_in_earlier_clue` | the set an earlier clue left | the faces from clue 1 |

## P1

### Clue strings

| Clue type | Clue | String | Example |
|---|---|---|---|
| Aggregation | Extreme | `Among the remaining <categories>, choose the one with the <extreme> <metric>.` | Among the remaining faces, choose the one with the largest area. |

Aggregation is P1, so no aggregation template ships in the first release. A rank
clue has no string yet: `task-structure.md` section 8 leaves its ordering
measurement and direction words open.

### Phrases for a second entity

| Form | Phrase | Example |
|---|---|---|
| `aggregated` | an extreme of that set | the largest of the faces from clue 1 |

## P2

### Phrases for a second entity

| Form | Phrase | Example |
|---|---|---|
| `cross_state` | a before/after pair | the solid state before the cutBlind operation and the solid state after it |
