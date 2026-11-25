# Prompt examples

**Status:** derived view, 2026-11-25. Eight prompts, as `04` renders them from
`generator/config/prompts.yaml`, each with the program it builds on and the answer
it asks for. The rules are [`prompt-content.md`](../prompt-content.md) and
[`task-structure.md`](../task-structure.md); the copy is `prompts.yaml`. This
document owns no rule.

A prompt example is not a gold record. A [gold record](../../implementation/pipeline/testing/oracles/task-construction/README.md)
carries the clue chain, narrowing counts, answer-equivalent set, and a gold query.
A prompt example exists to make the prompt text inspectable end to end: the shell, the
program, the question, the numbered clues, and the answer instruction, with real
numbers.

Each block below is the prompt exactly as it renders, so it can be pasted as it
stands without editing. The outer fence is `text` only so the reader sees the
prompt as text; the inner `python` fence is part of the prompt.

**Rendering conventions.** Every block uses variant 0 of its template. Articles
follow the renderer rule: `the` when the description selects one element of its
category in the program, `a` when it selects several, plural for a set bound by an
earlier clue. A non-multiple-choice answer has no choice block, and a task with no
clue has an empty clue list; both leave a blank line, which is not shown here.

Every clue is necessary (`task-structure.md` §2.2): each **Counts** line records
what dropping the clue leaves, so the chain can be checked without rebuilding it.

Two programs appear, each inside the prompt's own `python` fence: a 10 by 20 by 5
box, and the same box with a blind hole of radius 2 and depth 2 cut into its top
face. Both are the program text the [gold records](../../implementation/pipeline/testing/oracles/task-construction/README.md)
carry, so an example and the record for the same shape cannot drift apart.
Numbers are the graph values, computed with CadQuery 2.8.0; the script in
[Checking the numbers](#checking-the-numbers) prints them.

## P0

All eight examples are P0. The P1 section lists the forms that are defined
but not shown.

### 1. Volume of the final solid state

The warmup shape: the question names the only candidate, so there is no clue.

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

result = cq.Workplane("XY").box(10, 20, 5)
```

What is the volume of the target solid state?

Return exactly one number. Use mm^3; round to 4 significant figures.
````

**Answer:** `1000` mm^3. **Counts:** 1 possible answer, no clues.

### 2. Membership of a point

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

result = cq.Workplane("XY").box(10, 20, 5)
```

Is the point (0, 0, 0) inside the target solid state?

Return exactly one of `true` or `false`.
````

**Answer:** `true`. **Counts:** 1 possible answer, no clues. The point is a probe
the graph classifies, not a reference.

### 3. Area of a face, one measurement range

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

wp = cq.Workplane("XY")
box = wp.box(10, 20, 5)
top = box.faces(">Z")
plane = top.workplane()
hole = plane.circle(2)
result = hole.cutBlind(-2)
```

What is the area of the target face?

1. The target face has an area between 150 and 190.

Return exactly one number. Use mm^2; round to 4 significant figures.
````

**Answer:** `187.4` mm^2, the top annular face. **Counts:** 8 possible answers
(the faces of the final state), 1 clue: 8 → 1. Each bound sits between two
adjacent candidate areas: 150 between 100 and 187.43, 190 between 187.43 and 200.
Dropping the clue leaves all 8 faces, so it is necessary.

### 4. Length of an edge, two containment clues

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

wp = cq.Workplane("XY")
box = wp.box(10, 20, 5)
top = box.faces(">Z")
plane = top.workplane()
hole = plane.circle(2)
result = hole.cutBlind(-2)
```

What is the length of the target edge?

1. The target edge is an edge of the face touching the top of the axis-aligned bounding box.
2. The target edge is an edge of the cylindrical face.

Return exactly one number. Use mm; round to 4 significant figures.
````

**Answer:** `12.57` mm, the circle where the hole meets the top face.
**Counts:** 15 possible answers (the edges of the final state), clue 1: 15 → 5
(the four outer edges of the top face and the circle), clue 2: 5 → 1. Necessity:
dropping clue 1 leaves the three edges of the cylindrical face, the two circles
and the seam, so the answer is not unique; dropping clue 2 leaves the five edges
of the top face.

The second clue leaves one, so it is the final clue.

### 5. Centroid of a face, a position clue

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

wp = cq.Workplane("XY")
box = wp.box(10, 20, 5)
top = box.faces(">Z")
plane = top.workplane()
hole = plane.circle(2)
result = hole.cutBlind(-2)
```

What is the face centroid of the target face?

1. The target face touches the front of the axis-aligned bounding box.

Return exactly one coordinate tuple `(x, y, z)` in the program frame; round each value to 4 significant figures.
````

**Answer:** `(0, -10, 0)`, the front face. **Counts:** 8 possible answers, 1 clue:
8 → 1. Dropping the clue leaves all 8 faces, so it is necessary.

The position clue says "front", from the frame table: `min_y` is front. The graph
stores `min_y`, and `04` renders the word. On both example programs every
bounding-box extreme plane holds one face, so a position clue leaves one answer on
its own; a second clue would make it redundant, so it stands alone here
(the P0 gaps table).

### 6. Angle between two faces, a direction clue

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

result = cq.Workplane("XY").box(10, 20, 5)
```

What is the angle between the target face and the face touching the front of the axis-aligned bounding box?

1. The angle between the outward normal of the target face and +z is less than 1 degree.

Return exactly one number. Use degrees; round to 4 significant figures.
````

**Answer:** `90` degrees, between the top face and the front face.
**Counts:** 6 possible answers, 1 clue: 6 → 1. Dropping the clue leaves all 6
faces, so it is necessary.

The clue is a measured direction, not a categorical value. One degree selects
the face whose outward normal is along +z; a side face is 90 degrees away and the
bottom face is 180 degrees away, because the angle is measured to the directed
axis.

### 7. Area of a face, a comparison clue

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

result = cq.Workplane("XY").box(10, 20, 5)
```

What is the area of the target face?

1. The area of the target face is less than the area of the face touching the bottom of the axis-aligned bounding box.
2. The target face has an area greater than 50.

Return exactly one number. Use mm^2; round to 4 significant figures.
````

**Answer:** `100` mm^2, the left and right faces. **Counts:** 6 possible answers,
clue 1: 6 → 4 (both 100 mm^2 sides and both 50 mm^2 sides are smaller than the 200
mm^2 bottom), clue 2: 4 → 2 (the two 100 mm^2 sides, which share one answer).
Necessity: dropping clue 1 leaves 4 faces with 100 and 200 mm^2; dropping clue 2
leaves 4 with 100 and 50 mm^2.

The comparison clue names its reference by a condition, not by a part name. "The
bottom face" is not available; "the face touching the bottom of the
axis-aligned bounding box" is. A position clue would select one face on its own,
so it could not follow the comparison: dropping the comparison would leave the
same answer. The chain ends on the two faces with the same area, which is one
answer (`DS-REQ-15`). The target is one face; the answer-equivalent set holds
both 100 mm² faces. The other witness renders the same question and clue
sequence, so construction keeps one (`DS-REQ-35`).

### 8. Area of a face, provenance and surface kind

````text
Directions use the program frame: +x is right, +y is back, +z is up.

```python
import cadquery as cq

wp = cq.Workplane("XY")
box = wp.box(10, 20, 5)
top = box.faces(">Z")
plane = top.workplane()
hole = plane.circle(2)
result = hole.cutBlind(-2)
```

What is the area of the target face?

1. The target face was created by the cutBlind operation.
2. The target face is planar.

Return exactly one number. Use mm^2; round to 4 significant figures.
````

**Answer:** `12.57` mm^2, the hole floor. **Counts:** 8 possible answers, clue 1:
8 → 2 (the hole wall and the hole floor are the faces the cut created), clue 2:
2 → 1. Necessity: dropping clue 1 leaves 7 planar faces with 200, 187.4, 100, 100,
50, 50, and 12.57 mm^2; dropping clue 2 leaves the two cut faces with 25.13 and
12.57 mm^2.

The provenance clue names an operation by its method: the program calls
`cutBlind` once, so `the cutBlind operation` selects it. The second clue then
separates the two faces the cut created: the wall is cylindrical and the floor is
planar.

### What the P0 examples do not show

| Not shown | Why |
|---|---|
| Multiple choice | The choice block adds no new clue type; the identity case needs five candidates and is the gold-record gap. |
| A count answer | The integer instruction is one line and adds no prompt structure; the meaning is covered by the gold records. |
| A position clue in a chain | On both programs every bounding-box extreme plane holds one face, so a position clue leaves one answer on its own and a second clue would make it redundant; section 5 shows it alone. |
| Distance between two entities | The question template takes a reference and is the same shape as the angle one; the gold records cover it. |

### Checking the numbers

This script prints every answer value used above. It uses plain CadQuery and no
generator code.

```python
import cadquery as cq
import math


def canon(value: float) -> str:
    if abs(value) < 1e-9:
        return "0"
    return format(value, ".4g")


box = cq.Workplane("XY").box(10, 20, 5)
print("volume", canon(box.val().Volume()))
print("faces", canon(len(box.faces().vals())))
print("inside", box.val().isInside(cq.Vector(0, 0, 0), 1e-6))

top = box.faces(">Z").val().normalAt()
front = box.faces("<Y").val().normalAt()
print("angle", canon(math.degrees(top.getAngle(front))))

for face in box.val().Faces():
    print(
        "box face",
        face.geomType(),
        canon(face.Area()),
        canon(face.Center().x),
        canon(face.Center().y),
        canon(face.Center().z),
    )

wp = cq.Workplane("XY")
b = wp.box(10, 20, 5)
top = b.faces(">Z")
plane = top.workplane()
hole = plane.circle(2)
solid = hole.cutBlind(-2).val()
for face in solid.Faces():
    print(
        "face",
        face.geomType(),
        canon(face.Area()),
        canon(face.Center().x),
        canon(face.Center().y),
        canon(face.Center().z),
    )
for edge in solid.Edges():
    print("edge", edge.geomType(), canon(edge.Length()))
```

## P1

### What the P1 examples do not show

| Not shown | Why |
|---|---|
| Extreme and rank | A rank clue has no string yet because `task-structure.md` section 8 leaves its ordering measurement and direction words open. |
| A solid state after an operation | P1. |
