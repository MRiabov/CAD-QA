# row:graph:src_66f7d69e9876eb33:synth:v4:parameterized_feature_rank

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp40`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 12, -46))
wp2 = wp1.box(94, 104, 91)
wp3 = cq.Workplane('YZ', origin=(0, 12, -46))
wp4 = wp3.circle(11)
wp5 = wp4.extrude(117)
wp6 = wp5.rotate([0, 12, -46], [0, 13, -46], 90)
wp7 = wp6.rotate([0, 12, -46], [0, 12, -44], -90)
wp8 = wp7.translate([-47, 0, 0])
wp9 = wp2.cut(wp8)
wp10 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 44, 41), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 1, 1)))
wp11 = wp10.circle(12)
wp12 = wp11.extrude(48)
wp13 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 44, 41), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 1, 1)))
wp14 = wp13.circle(11)
wp15 = wp14.extrude(48)
wp16 = wp12.cut(wp15)
wp17 = wp9.union(wp16)
wp18 = cq.Workplane(cq.Plane(origin=cq.Vector(-20, 0, 51), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 0, 2)))
wp19 = wp18.circle(12)
wp20 = wp19.extrude(48)
wp21 = cq.Workplane(cq.Plane(origin=cq.Vector(-20, 0, 51), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 0, 2)))
wp22 = wp21.circle(11)
wp23 = wp22.extrude(48)
wp24 = wp20.cut(wp23)
wp25 = wp17.union(wp24)
wp26 = cq.Workplane(cq.Plane(origin=cq.Vector(-7, -35, 23), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -1, 1)))
wp27 = wp26.circle(12)
wp28 = wp27.extrude(48)
wp29 = cq.Workplane(cq.Plane(origin=cq.Vector(-7, -35, 23), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -1, 1)))
wp30 = wp29.circle(11)
wp31 = wp30.extrude(48)
wp32 = wp28.cut(wp31)
wp33 = wp25.union(wp32)
wp34 = cq.Workplane(cq.Plane(origin=cq.Vector(7, -35, -23), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -1, -1)))
wp35 = wp34.circle(12)
wp36 = wp35.extrude(48)
wp37 = cq.Workplane(cq.Plane(origin=cq.Vector(7, -35, -23), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -1, -1)))
wp38 = wp37.circle(11)
wp39 = wp38.extrude(48)
wp40 = wp36.cut(wp39)
wp41 = wp33.union(wp40)
wp42 = cq.Workplane(cq.Plane(origin=cq.Vector(20, 0, -51), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 0, -2)))
wp43 = wp42.circle(12)
wp44 = wp43.extrude(48)
wp45 = cq.Workplane(cq.Plane(origin=cq.Vector(20, 0, -51), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 0, -2)))
wp46 = wp45.circle(11)
wp47 = wp46.extrude(48)
wp48 = wp44.cut(wp47)
wp49 = wp41.union(wp48)
wp50 = cq.Workplane(cq.Plane(origin=cq.Vector(34, 44, -41), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 1, -1)))
wp51 = wp50.circle(12)
wp52 = wp51.extrude(48)
wp53 = cq.Workplane(cq.Plane(origin=cq.Vector(34, 44, -41), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 1, -1)))
wp54 = wp53.circle(11)
wp55 = wp54.extrude(48)
wp56 = wp52.cut(wp55)
wp57 = wp49.union(wp56)
result = wp57
```

Identify the target feature that satisfies all of these constraints:
- The target feature satisfies face count greater than 3.0.
- The target feature can be described by its centroid height.
- Within the narrowed set, select the 4th candidate in decreasing centroid height order.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Candidate solids with face count >3: box wp2 (6 faces, centroid z=-46), hollow cylinders wp16, wp24, wp32, wp40, wp48, wp56 (each 4 faces, centroids: wp24=75, wp16≈57.97, wp32≈39.97, wp40≈-39.97, wp48=-75, wp56≈-57.97), cut box wp9 (centroid~ -46), and unions (centroids~ -46). Descending centroid z order: wp24 (75), wp16 (57.97), wp32 (39.97), wp40 (-39.97). 4th candidate is wp40.

{"name": "submit_text", "arguments": {"text": "wp40"}}
```
