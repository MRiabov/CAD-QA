# cadqa_coordinate_frame_6fc5fec0e50f913d

- **source**: original-pool
- **hop**: 0  |  **format**: text  |  **tool**: submit_text
- **gold**: `cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, what coordinate frame or workplane name is established by feature `wp23`? Answer with exactly one listed token.

Choices: XY, YZ, XZ, front, back, left, right, top, bottom, inherited, unknown, cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -89))
wp2 = wp1.splineApprox([[79, 0, 0], [69, 38, 7], [42, 66, 14], [5, 78, 21], [-33, 71, 29], [-64, 46, 36], [-78, 10, 43], [-73, -29, 50], [-50, -61, 57], [-15, -77, 64], [24, -75, 72], [57, -54, 79], [76, -20, 86], [76, 20, 93], [57, 54, 100], [24, 75, 107], [-15, 77, 114], [-50, 61, 122], [-73, 29, 129], [-78, -10, 136], [-64, -46, 143], [-33, -71, 150], [5, -78, 157], [42, -66, 164], [69, -38, 172], [79, 0, 179]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -89))
wp4 = wp3.moveTo(79, 0)
wp5 = wp4.circle(11)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(8)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, 53, -53), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(8)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, -53, -36), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(-2, -2, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(8)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, -18), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(8)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(8)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(8)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, -53, 54), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(-2, -2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(8)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(8)
wp38 = wp34.union(wp37)
result = wp38
```
```

## Model output (trace)

```
We need to identify the coordinate frame or workplane name established by feature `wp23`. In the script, `wp23` is defined as:

```python
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
```

This is an explicit plane definition, not a named standard plane (like XY, YZ, XZ, front, back, etc.). So the answer should be the string representation of that plane. Among the choices, there is an option: `cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))`. That matches exactly.

Thus answer is that string.

But note: The question says "what coordinate frame or workplane name is established by feature `wp23`?" and expects one listed token. The choices include that exact string. So answer: cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))

We'll provide it as text.

The workplane `wp23` is defined with an explicit plane, not a named standard plane. The plane's parameters match exactly one of the provided choices.

```json
{"name": "submit_text", "arguments": {"text": "cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}}
```
```
