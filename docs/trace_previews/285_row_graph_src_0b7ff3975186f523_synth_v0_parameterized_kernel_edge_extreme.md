# row:graph:src_0b7ff3975186f523:synth:v0:parameterized_kernel_edge_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: candidate_label  |  **tool**: submit_label
- **gold**: `"B"`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -28))
wp2 = wp1.box(102, 129, 112)
wp3 = cq.Workplane('XY', origin=(0, 0, -28))
wp4 = wp3.box(94, 122, 108)
wp5 = wp4.translate([0, 0, 2])
wp6 = wp2.cut(wp5)
wp7 = cq.Workplane('XY', origin=(0, 0, -28))
wp8 = wp7.box(94, 2, 108)
wp9 = wp8.translate([0, 64, 58])
wp10 = wp6.union(wp9)
wp11 = cq.Workplane('XY', origin=(0, 0, -28))
wp12 = wp11.workplane(offset=4)
wp13 = wp12.rect(156, 2)
wp14 = wp13.extrude(108)
wp15 = wp14.rotate([0, 0, -28], [0, 0, -26], 52)
wp16 = wp15.translate([49, -38, 0])
wp17 = wp10.union(wp16)
wp18 = cq.Workplane('XY', origin=(0, 0, -28))
wp19 = wp18.workplane(offset=4)
wp20 = wp19.rect(156, 2)
wp21 = wp20.extrude(108)
wp22 = wp21.rotate([0, 0, -28], [0, 0, -26], 52)
wp23 = wp22.translate([38, -29, 0])
wp24 = wp17.union(wp23)
wp25 = cq.Workplane('XY', origin=(0, 0, -28))
wp26 = wp25.workplane(offset=4)
wp27 = wp26.rect(156, 2)
wp28 = wp27.extrude(108)
wp29 = wp28.rotate([0, 0, -28], [0, 0, -26], 52)
wp30 = wp29.translate([27, -21, 0])
wp31 = wp24.union(wp30)
wp32 = cq.Workplane('XY', origin=(0, 0, -28))
wp33 = wp32.workplane(offset=4)
wp34 = wp33.rect(156, 2)
wp35 = wp34.extrude(108)
wp36 = wp35.rotate([0, 0, -28], [0, 0, -26], 52)
wp37 = wp36.translate([16, -13, 0])
wp38 = wp31.union(wp37)
wp39 = cq.Workplane('XY', origin=(0, 0, -28))
wp40 = wp39.workplane(offset=4)
wp41 = wp40.rect(156, 2)
wp42 = wp41.extrude(108)
wp43 = wp42.rotate([0, 0, -28], [0, 0, -26], 52)
wp44 = wp43.translate([5, -4, 0])
wp45 = wp38.union(wp44)
wp46 = cq.Workplane('XY', origin=(0, 0, -28))
wp47 = wp46.workplane(offset=4)
wp48 = wp47.rect(156, 2)
wp49 = wp48.extrude(108)
wp50 = wp49.rotate([0, 0, -28], [0, 0, -26], 52)
wp51 = wp50.translate([-5, 4, 0])
wp52 = wp45.union(wp51)
wp53 = cq.Workplane('XY', origin=(0, 0, -28))
wp54 = wp53.workplane(offset=4)
wp55 = wp54.rect(156, 2)
wp56 = wp55.extrude(108)
wp57 = wp56.rotate([0, 0, -28], [0, 0, -26], 52)
wp58 = wp57.translate([-16, 13, 0])
wp59 = wp52.union(wp58)
wp60 = cq.Workplane('XY', origin=(0, 0, -28))
wp61 = wp60.workplane(offset=4)
wp62 = wp61.rect(156, 2)
wp63 = wp62.extrude(108)
wp64 = wp63.rotate([0, 0, -28], [0, 0, -26], 52)
wp65 = wp64.translate([-27, 21, 0])
wp66 = wp59.union(wp65)
wp67 = cq.Workplane('XY', origin=(0, 0, -28))
wp68 = wp67.workplane(offset=4)
wp69 = wp68.rect(156, 2)
wp70 = wp69.extrude(108)
wp71 = wp70.rotate([0, 0, -28], [0, 0, -26], 52)
wp72 = wp71.translate([-38, 29, 0])
wp73 = wp66.union(wp72)
wp74 = cq.Workplane('XY', origin=(0, 0, -28))
wp75 = wp74.workplane(offset=4)
wp76 = wp75.rect(156, 2)
wp77 = wp76.extrude(108)
wp78 = wp77.rotate([0, 0, -28], [0, 0, -26], 52)
wp79 = wp78.translate([-49, 38, 0])
wp80 = wp73.union(wp79)
result = wp80
```

Identify the target edge that satisfies all of these constraints:
- The target edge is one of the model edges.
- The target edge has a value for midpoint Y coordinate.
- From the remaining candidates, choose the one with the largest midpoint Y coordinate.

Candidate labels:
- A: endpoints (-47, -61, -80) to (-47, -61, 28); midpoint (-47, -61, -26); length 108; midpoint distance to origin 81.277303
- B: endpoints (20.233584, 83.0805, -24) to (20.233584, 83.0805, 84); midpoint (20.233584, 83.0805, 30); length 108; midpoint distance to origin 90.618803
- C: endpoints (47, -61, -82) to (47, 61, -82); midpoint (47, 0, -82); length 122; midpoint distance to origin 94.514549
- D: endpoints (-47, -61, -82) to (47, -61, -82); midpoint (0, -61, -82); length 94; midpoint distance to origin 102.200783
- E: endpoints (-47, -61, 26) to (47, -61, 26); midpoint (0, -61, 26); length 94; midpoint distance to origin 66.309879
- F: endpoints (-47, 61, -82) to (47, 61, -82); midpoint (0, 61, -82); length 94; midpoint distance to origin 102.200783
- G: endpoints (-47, 61, 26) to (47, 61, 26); midpoint (0, 61, 26); length 94; midpoint distance to origin 66.309879

Return exactly one candidate label from the list above, for example `A`.
```

## Model output (trace)

```
The script starts with a large box (102×129×112), then subtracts a smaller box (94×122×108) shifted up 2 mm, creating a shell.  
Then a thin bar (94×2×108) is added at offset (0,64,58).  
After that, many identical rectangular extrusions (156×2, extruded 108) are rotated 52° around the Z axis and translated in a pattern.  

The candidate edges are all axis-aligned or possibly slanted.  
We need edges with a midpoint Y coordinate, and among those, the largest Y.  

Candidate A: endpoints at y = -61 → midpoint y = -61.  
Candidate B: endpoints at y ≈ 83.08 → midpoint y ≈ 83.08.  
C: midpoint y = 0.  
D: y = -61.  
E: y = -61.  
F: y = 61.  
G: y = 61.  

The largest Y is 83.08 from candidate B.  

```json
{"name": "submit_label", "arguments": {"label": "B"}}
```
```
