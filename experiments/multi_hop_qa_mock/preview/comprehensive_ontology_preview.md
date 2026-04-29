# Comprehensive Ontology Preview

This preview is generated deterministically from mock ontology coverage.
It is intended for judging the clue vocabulary before adding it to the
main generator.

Public clue wording rule: every clue should be understandable from the
shown script alone by a small model. Ontology terms such as
`material_region`, `measurement`, `profile`, or `accumulated body` are
not acceptable in public prompts unless the wording also ties them to
visible CadQuery constructs such as `.extrude(...)`, `.union(...)`,
`.faces(...)`, `.polyline(...)`, or bounding-box comparisons.

## Selected Sources

### src_4381883289a33860

- Path: `CADEvolve-C/CADEvolve-C-core/ArrayBossHelixWire__02_25_emitted_centered_scaled_binarized/source_cadquery.py`
- Family: `cadevolve_cadevolve_c_cadevolve_c_core`
- Line count: `56`

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -72))
wp2 = wp1.splineApprox([[88, 0, 0], [77, 42, 6], [47, 74, 12], [6, 88, 17], [-37, 80, 23], [-71, 52, 29], [-87, 11, 35], [-82, -32, 40], [-56, -68, 46], [-16, -86, 52], [27, -84, 58], [64, -60, 63], [85, -22, 69], [85, 22, 75], [64, 60, 81], [27, 84, 86], [-16, 86, 92], [-56, 68, 98], [-82, 32, 104], [-87, -11, 109], [-71, -52, 115], [-37, -80, 121], [6, -88, 127], [47, -74, 133], [77, -42, 138], [88, 0, 144]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -72))
wp4 = wp3.moveTo(88, 0)
wp5 = wp4.circle(8)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, -62), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(5)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, -51), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(5)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(5)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(5)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(5)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, -10), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(5)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, 10), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(5)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(5)
wp38 = wp34.union(wp37)
wp39 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, 31), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp40 = wp39.circle(5)
wp41 = wp40.extrude(5)
wp42 = wp38.union(wp41)
wp43 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, 41), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp44 = wp43.circle(5)
wp45 = wp44.extrude(5)
wp46 = wp42.union(wp45)
wp47 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, 51), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp48 = wp47.circle(5)
wp49 = wp48.extrude(5)
wp50 = wp46.union(wp49)
wp51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp52 = wp51.circle(5)
wp53 = wp52.extrude(5)
wp54 = wp50.union(wp53)
result = wp54

```

### src_bb1d614881c83f67

- Path: `CADEvolve-P/ShapeNet-P/02924116+dc9c640221f58021c08550bf6ec9e732+models+model_normalized+r09+s75+t170+p95+k00/source_cadquery.py`
- Family: `cadevolve_cadevolve_p_shapenet_p`
- Line count: `38`

```python
import cadquery as cq
import math
A = 14.0
B = 26.0
C = 89.0
R_out = 4.0
R_in = 0.27
side_scale = 1.0

base = cq.Workplane("XY").box(A, B, C)

def star_points(n=5, inner=R_in, scale=1.0):
    pts = []
    total = n * 2
    for k in range(total):
        ang = 2 * math.pi * k / total
        rad = 1.0 if (k % 2 == 0) else inner
        pts.append((math.cos(ang) * rad * scale, math.sin(ang) * rad * scale))
    return pts

front_shape = star_points()
side_shape = star_points()

for face_tag in (">Y", "<Y"):
    base = base.faces(face_tag).workplane().polyline(front_shape).close().cutThruAll()
for face_tag in (">X", "<X"):
    base = base.faces(face_tag).workplane().polyline(side_shape).close().cutThruAll()

th = R_out * R_in
dY = min(R_out, B / 2.0)
dX = min(R_out, A / 2.0)
zpos = R_out + th / 2.0

for z in (zpos, -zpos):
    base = base.faces(">Y").workplane().center(0, z).rect(A, th).cutBlind(-dY)
    base = base.faces(">X").workplane().center(0, z).rect(B, th).cutBlind(-dX)

result = base

```

## Source Pattern Survey

### array_boss_helix_wire

Visible code shapes:

- `splineApprox(...)` path wire
- repeated `cq.Workplane(cq.Plane(...))` calls
- repeated `.circle(...).extrude(...)` bosses
- repeated `.union(...)` accumulation

Wording implications:

- Use 'path wire' instead of centerline unless a centerline label exists.
- Use 'running object produced by repeated `.union(...)` calls' instead of accumulated body.
- Avoid final-union clues unless the individual candidate gate passes.

### box_star_slots

Visible code shapes:

- box dimensions assigned to variables
- point lists built by trigonometry
- face selectors such as `.faces(">Y")` and `.faces(">X")`
- polyline through-cuts
- rectangular blind cuts at `zpos` and `-zpos`

Wording implications:

- Use 'points later passed to `.polyline(...)`' instead of star profile.
- Use selector text only when enough matching selectors exist.
- Use `zpos`/`-zpos` wording only when the repeated pair has enough candidates.

### tabs_fillets_chamfers

Visible code shapes:

- box base
- selected faces used to place tabs
- rectangular `.extrude(..., combine=False)` tabs
- `.edges(...)` followed by `.fillet(...)`
- `.edges().chamfer(...)` on a base body

Wording implications:

- Use 'the object created with `combine=False` and later joined' for tab solids.
- Use explicit `.edges(...)` selector wording for fillet/chamfer clues.
- Do not assume the model knows topology terms like rim, side face, or material region unless tied to visible calls.

## Node Type Clue Coverage

| Node Type | Mock Node | Source | Candidates | Gate | Canonical Clue |
|---|---|---|---|---|---|
| `source` | `source:primary` | `src_4381883289a33860` | 2 | `reject` | The target is the selected CadEvolve source script. |
| `feature` | `feature:wp37` | `src_4381883289a33860` | 12 | `pass` | The target is the variable assigned by one of the repeated `.extrude(...)` calls. |
| `operation` | `operation:extrude` | `src_4381883289a33860` | 11 | `pass` | The target is an `.extrude(...)` call that follows a `.circle(...)` call. |
| `parameter` | `parameter:radius_5` | `src_4381883289a33860` | 14 | `pass` | The target is the numeric `5` passed to a repeated `.circle(5)` call. |
| `workplane` | `workplane:boss_plane_high_z` | `src_4381883289a33860` | 12 | `pass` | The target is the `cq.Workplane(cq.Plane(...))` call whose plane origin has the largest Z value among the repeated boss planes. |
| `sketch` | `sketch:star_points` | `src_bb1d614881c83f67` | 2 | `reject` | The target is the list of 2D points returned by `star_points(...)` and then passed to `.polyline(...)`. |
| `profile` | `profile:circle_r5` | `src_4381883289a33860` | 12 | `pass` | The target is a circle made by `.circle(5)` immediately before an `.extrude(...)` call. |
| `solid` | `solid:accumulated_body` | `src_4381883289a33860` | 5 | `pass` | The target is the running object produced by repeatedly calling `.union(...)`. |
| `face` | `face:+Y` | `src_bb1d614881c83f67` | 4 | `reject` | The target is a face selected by `.faces(">Y")` before a cut. |
| `edge` | `edge:circular_boss_rim` | `src_4381883289a33860` | 12 | `pass` | The target is an edge selected by `.edges(...)` or created around a `.circle(...).extrude(...)` feature. |
| `vertex` | `vertex:profile_start` | `src_4381883289a33860` | 12 | `pass` | The target is a point on the circular profile made by `.circle(5)`. |
| `axis` | `axis:global_Z` | `src_4381883289a33860` | 6 | `pass` | The target is the Z coordinate used in the `cq.Vector(..., ..., z)` plane origins. |
| `centerline` | `centerline:swept_wire` | `src_4381883289a33860` | 6 | `pass` | The target is the path wire created by `splineApprox(...)` and used by `.sweep(...)`. |
| `material_region` | `material_region:boss_added` | `src_4381883289a33860` | 12 | `pass` | The target is the new solid volume introduced by an `.extrude(...)` that is later joined with `.union(...)`. |
| `selector` | `selector:faces_pos_y` | `src_bb1d614881c83f67` | 4 | `reject` | The target is the `.faces(">Y")` selector used before a cut operation. |
| `measurement` | `measurement:bbox_delta` | `src_bb1d614881c83f67` | 8 | `pass` | The target is whether a cut changes the final object's outer bounding box. |

## Relation Clue Coverage

| Relation | Source Node | Target Node | Candidates | Gate | Risk | Guard | Canonical Clue |
|---|---|---|---|---|---|---|---|
| `before` | `feature:early_boss_extrude` | `wp9` | 8 | `pass` | `normal` | side_range=8; min=5 | The target occurs before the first extrude operation. |
| `after` | `feature:late_boss_extrude` | `wp49` | 5 | `pass` | `normal` | side_range=5; min=5 | The target occurs after the 11th extrude operation. |
| `immediately_before` | `wp53` | `wp54` | 1 | `reject` | `high` |  | The target is the operation immediately before the final union operation. |
| `immediately_after` | `wp17` | `wp16` | 1 | `reject` | `normal` |  | The target is the operation immediately after the fourth circle operation. |
| `input_to` | `feature:wp37` | `operation:final_union` | 1 | `reject` | `high` |  | The target is one of the objects passed into a later `.union(...)` call. |
| `created_by` | `material_region:boss_added` | `feature:wp37` | 12 | `pass` | `normal` |  | The target is an `.extrude(...)` call that creates a new solid before that solid is joined with `.union(...)`. |
| `modified_by` | `face:+Y` | `feature:slot_cut` | 4 | `reject` | `normal` |  | The target is a cut made from a `.faces(">Y")` workplane, so it changes that side of the box. |
| `deleted_by` | `material_region:slot_removed` | `feature:slot_cut` | 4 | `reject` | `normal` |  | The target is a `.cutBlind(...)` or `.cutThruAll()` call that removes material from the box. |
| `bounded_by` | `edge:circular_boss_rim` | `face:boss_side` | 12 | `pass` | `normal` |  | The target creates a boundary visible from a preceding shape call, such as `.circle(...)` before `.extrude(...)` or `.rect(...)` before a cut. |
| `selected_by` | `face:+Y` | `selector:faces_pos_y` | 2 | `reject` | `normal` |  | The target uses `.faces(">Y")` before making a workplane or cut. |
| `located_on` | `profile:circle_r5` | `workplane:boss_plane_high_z` | 12 | `pass` | `normal` |  | The target is a `.circle(...)` call made on one of the repeated `cq.Workplane(cq.Plane(...))` planes. |
| `parallel_to` | `axis:boss_plane_normal` | `axis:global_Z` | 8 | `pass` | `normal` |  | The target uses a direction vector that is parallel to one of the script's coordinate axes, such as a `normal=(..., ..., z)` or an edge selector like `"|Z"`. |
| `perpendicular_to` | `axis:boss_plane_xdir` | `axis:boss_plane_normal` | 8 | `pass` | `normal` |  | The target's plane uses an `xDir` vector perpendicular to its `normal` vector. |
| `coaxial_with` | `centerline:boss` | `axis:boss_plane_normal` | 8 | `pass` | `normal` |  | The target extrusion follows the normal direction of the workplane where its circle was drawn. |
| `adjacent_to` | `face:+Y` | `edge:slot_boundary` | 4 | `reject` | `normal` |  | The target cut is made on the same side face that contains the boundary of the resulting slot. |
| `contained_in` | `vertex:slot_corner` | `face:+Y` | 4 | `reject` | `normal` |  | The target cut produces slot-corner points on the selected side face. |
| `intersects` | `profile:slot_rect` | `face:+Y` | 4 | `reject` | `normal` |  | The target's rectangle is drawn on a selected side face before the cut is applied. |
| `translated_by` | `profile:slot_rect` | `parameter:zpos` | 4 | `reject` | `normal` |  | The target rectangle is centered at either `zpos` or `-zpos` before the cut. |
| `rotated_by` | `workplane:boss_plane` | `parameter:plane_normal` | 12 | `pass` | `normal` |  | The target uses a `cq.Plane(...)` with an explicit `normal=...` vector rather than a default XY workplane. |
| `scaled_by` | `profile:star_shape` | `parameter:R_out` | 6 | `pass` | `normal` |  | The target uses a size variable such as `R_out`, `R`, or `tab_w` to scale geometry before a `.polyline(...)`, `.rect(...)`, or `.extrude(...)` call. |
| `parameter_of` | `parameter:R_out` | `profile:star_shape` | 8 | `pass` | `normal` |  | The target uses a named size parameter in a later geometry call such as `.polyline(...)`, `.rect(...)`, `.box(...)`, or `.extrude(...)`. |
| `has_measurement` | `feature:slot_cut` | `measurement:bbox_delta` | 8 | `pass` | `normal` |  | The target is a cut whose effect can be checked by comparing the outer bounding box before and after the operation. |
| `adds_material_to` | `feature:wp37` | `solid:accumulated_body` | 12 | `pass` | `normal` |  | The target is an `.extrude(...)` result that is later added to the running object with `.union(...)`. |
| `removes_material_from` | `feature:slot_cut` | `solid:base_box` | 4 | `reject` | `normal` |  | The target is a cut operation that removes material from the original box. |

## Parameter Entry And Exit Coverage

| Case | Entry Node | Relation | Exit Node | Candidates | Gate | Canonical Clue |
|---|---|---|---|---|---|---|
| `parameter_as_entry_node_to_profile` | `parameter:R_out` | `parameter_of` | `profile:star_shape` | 4 | `reject` | The target uses the outer radius parameter in points that are later passed to `.polyline(...)`. |
| `parameter_as_entry_node_to_operation` | `parameter:extrude_distance_8` | `parameter_of` | `operation:extrude` | 12 | `pass` | The target operation uses extrusion distance 8 as an input parameter. |
| `parameter_as_exit_node_from_operation` | `operation:circle` | `parameter_of` | `parameter:radius_5` | 12 | `pass` | The target parameter is the radius emitted by the circle operation descriptor. |
| `parameter_as_exit_node_from_measurement` | `measurement:bbox_delta` | `has_measurement` | `parameter:bbox_delta_zero` | 8 | `pass` | The target parameter is derived from a zero bounding-box delta measurement. |

## Canonical Question Preview Sets

### temporal_and_input

- Relations: `before`, `immediately_before`, `input_to`
- Individual clue gate: `reject`
- Failing relation types: `immediately_before`, `input_to`

```text
Given the CadQuery script, identify the feature that satisfies all of these constraints:
- The target occurs before the first extrude operation.
- The target is the operation immediately before the final union operation.
- The target is one of the objects passed into a later `.union(...)` call.
Return exactly one feature ID.
```

### geometry_and_selector

- Relations: `selected_by`, `located_on`, `adjacent_to`, `contained_in`
- Individual clue gate: `reject`
- Failing relation types: `selected_by`, `adjacent_to`, `contained_in`

```text
Given the CadQuery script, identify the feature that satisfies all of these constraints:
- The target uses `.faces(">Y")` before making a workplane or cut.
- The target is a `.circle(...)` call made on one of the repeated `cq.Workplane(cq.Plane(...))` planes.
- The target cut is made on the same side face that contains the boundary of the resulting slot.
- The target cut produces slot-corner points on the selected side face.
Return exactly one feature ID.
```

### metric_and_material

- Relations: `has_measurement`, `adds_material_to`, `removes_material_from`
- Individual clue gate: `reject`
- Failing relation types: `removes_material_from`

```text
Given the CadQuery script, identify the feature that satisfies all of these constraints:
- The target is a cut whose effect can be checked by comparing the outer bounding box before and after the operation.
- The target is an `.extrude(...)` result that is later added to the running object with `.union(...)`.
- The target is a cut operation that removes material from the original box.
Return exactly one feature ID.
```

### transform_and_parameter

- Relations: `translated_by`, `rotated_by`, `scaled_by`, `parameter_of`
- Individual clue gate: `reject`
- Failing relation types: `translated_by`

```text
Given the CadQuery script, identify the feature that satisfies all of these constraints:
- The target rectangle is centered at either `zpos` or `-zpos` before the cut.
- The target uses a `cq.Plane(...)` with an explicit `normal=...` vector rather than a default XY workplane.
- The target uses a size variable such as `R_out`, `R`, or `tab_w` to scale geometry before a `.polyline(...)`, `.rect(...)`, or `.extrude(...)` call.
- The target uses a named size parameter in a later geometry call such as `.polyline(...)`, `.rect(...)`, `.box(...)`, or `.extrude(...)`.
Return exactly one feature ID.
```


## Individual Prompt Previews

### Node Type Prompts

#### `node_prompt__source` coverage=`source` candidates=`2` gate=`reject`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the selected CadEvolve source script.
Return exactly one entity ID.
```

#### `node_prompt__feature` coverage=`feature` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the variable assigned by one of the repeated `.extrude(...)` calls.
Return exactly one entity ID.
```

#### `node_prompt__operation` coverage=`operation` candidates=`11` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is an `.extrude(...)` call that follows a `.circle(...)` call.
Return exactly one entity ID.
```

#### `node_prompt__parameter` coverage=`parameter` candidates=`14` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the numeric `5` passed to a repeated `.circle(5)` call.
Return exactly one entity ID.
```

#### `node_prompt__workplane` coverage=`workplane` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the `cq.Workplane(cq.Plane(...))` call whose plane origin has the largest Z value among the repeated boss planes.
Return exactly one entity ID.
```

#### `node_prompt__sketch` coverage=`sketch` candidates=`2` gate=`reject`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the list of 2D points returned by `star_points(...)` and then passed to `.polyline(...)`.
Return exactly one entity ID.
```

#### `node_prompt__profile` coverage=`profile` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is a circle made by `.circle(5)` immediately before an `.extrude(...)` call.
Return exactly one entity ID.
```

#### `node_prompt__solid` coverage=`solid` candidates=`5` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the running object produced by repeatedly calling `.union(...)`.
Return exactly one entity ID.
```

#### `node_prompt__face` coverage=`face` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the entity described by this clue: The target is a face selected by `.faces(">Y")` before a cut.
Return exactly one entity ID.
```

#### `node_prompt__edge` coverage=`edge` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is an edge selected by `.edges(...)` or created around a `.circle(...).extrude(...)` feature.
Return exactly one entity ID.
```

#### `node_prompt__vertex` coverage=`vertex` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is a point on the circular profile made by `.circle(5)`.
Return exactly one entity ID.
```

#### `node_prompt__axis` coverage=`axis` candidates=`6` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the Z coordinate used in the `cq.Vector(..., ..., z)` plane origins.
Return exactly one entity ID.
```

#### `node_prompt__centerline` coverage=`centerline` candidates=`6` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the path wire created by `splineApprox(...)` and used by `.sweep(...)`.
Return exactly one entity ID.
```

#### `node_prompt__material_region` coverage=`material_region` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the new solid volume introduced by an `.extrude(...)` that is later joined with `.union(...)`.
Return exactly one entity ID.
```

#### `node_prompt__selector` coverage=`selector` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the entity described by this clue: The target is the `.faces(">Y")` selector used before a cut operation.
Return exactly one entity ID.
```

#### `node_prompt__measurement` coverage=`measurement` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the entity described by this clue: The target is whether a cut changes the final object's outer bounding box.
Return exactly one entity ID.
```

### Relation Prompts

#### `relation_prompt__before` coverage=`before` risk=`normal` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target occurs before the first extrude operation.
Return exactly one ID.
```

#### `relation_prompt__after` coverage=`after` risk=`normal` candidates=`5` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target occurs after the 11th extrude operation.
Return exactly one ID.
```

#### `relation_prompt__immediately_before` coverage=`immediately_before` risk=`high` candidates=`1` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is the operation immediately before the final union operation.
Return exactly one ID.
```

#### `relation_prompt__immediately_after` coverage=`immediately_after` risk=`normal` candidates=`1` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is the operation immediately after the fourth circle operation.
Return exactly one ID.
```

#### `relation_prompt__input_to` coverage=`input_to` risk=`high` candidates=`1` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is one of the objects passed into a later `.union(...)` call.
Return exactly one ID.
```

#### `relation_prompt__created_by` coverage=`created_by` risk=`normal` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is an `.extrude(...)` call that creates a new solid before that solid is joined with `.union(...)`.
Return exactly one ID.
```

#### `relation_prompt__modified_by` coverage=`modified_by` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is a cut made from a `.faces(">Y")` workplane, so it changes that side of the box.
Return exactly one ID.
```

#### `relation_prompt__deleted_by` coverage=`deleted_by` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is a `.cutBlind(...)` or `.cutThruAll()` call that removes material from the box.
Return exactly one ID.
```

#### `relation_prompt__bounded_by` coverage=`bounded_by` risk=`normal` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target creates a boundary visible from a preceding shape call, such as `.circle(...)` before `.extrude(...)` or `.rect(...)` before a cut.
Return exactly one ID.
```

#### `relation_prompt__selected_by` coverage=`selected_by` risk=`normal` candidates=`2` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target uses `.faces(">Y")` before making a workplane or cut.
Return exactly one ID.
```

#### `relation_prompt__located_on` coverage=`located_on` risk=`normal` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is a `.circle(...)` call made on one of the repeated `cq.Workplane(cq.Plane(...))` planes.
Return exactly one ID.
```

#### `relation_prompt__parallel_to` coverage=`parallel_to` risk=`normal` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target uses a direction vector that is parallel to one of the script's coordinate axes, such as a `normal=(..., ..., z)` or an edge selector like `"|Z"`.
Return exactly one ID.
```

#### `relation_prompt__perpendicular_to` coverage=`perpendicular_to` risk=`normal` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target's plane uses an `xDir` vector perpendicular to its `normal` vector.
Return exactly one ID.
```

#### `relation_prompt__coaxial_with` coverage=`coaxial_with` risk=`normal` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target extrusion follows the normal direction of the workplane where its circle was drawn.
Return exactly one ID.
```

#### `relation_prompt__adjacent_to` coverage=`adjacent_to` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target cut is made on the same side face that contains the boundary of the resulting slot.
Return exactly one ID.
```

#### `relation_prompt__contained_in` coverage=`contained_in` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target cut produces slot-corner points on the selected side face.
Return exactly one ID.
```

#### `relation_prompt__intersects` coverage=`intersects` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target's rectangle is drawn on a selected side face before the cut is applied.
Return exactly one ID.
```

#### `relation_prompt__translated_by` coverage=`translated_by` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target rectangle is centered at either `zpos` or `-zpos` before the cut.
Return exactly one ID.
```

#### `relation_prompt__rotated_by` coverage=`rotated_by` risk=`normal` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target uses a `cq.Plane(...)` with an explicit `normal=...` vector rather than a default XY workplane.
Return exactly one ID.
```

#### `relation_prompt__scaled_by` coverage=`scaled_by` risk=`normal` candidates=`6` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target uses a size variable such as `R_out`, `R`, or `tab_w` to scale geometry before a `.polyline(...)`, `.rect(...)`, or `.extrude(...)` call.
Return exactly one ID.
```

#### `relation_prompt__parameter_of` coverage=`parameter_of` risk=`normal` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target uses a named size parameter in a later geometry call such as `.polyline(...)`, `.rect(...)`, `.box(...)`, or `.extrude(...)`.
Return exactly one ID.
```

#### `relation_prompt__has_measurement` coverage=`has_measurement` risk=`normal` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is a cut whose effect can be checked by comparing the outer bounding box before and after the operation.
Return exactly one ID.
```

#### `relation_prompt__adds_material_to` coverage=`adds_material_to` risk=`normal` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is an `.extrude(...)` result that is later added to the running object with `.union(...)`.
Return exactly one ID.
```

#### `relation_prompt__removes_material_from` coverage=`removes_material_from` risk=`normal` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the feature or entity that satisfies this relation clue:
- The target is a cut operation that removes material from the original box.
Return exactly one ID.
```

### Parameter Entry/Exit Prompts

#### `parameter_prompt__parameter_as_entry_node_to_profile` coverage=`parameter_as_entry_node_to_profile` candidates=`4` gate=`reject`

```text
Given the CadQuery script, identify the parameter or entity described by this clue:
- The target uses the outer radius parameter in points that are later passed to `.polyline(...)`.
Return exactly one ID.
```

#### `parameter_prompt__parameter_as_entry_node_to_operation` coverage=`parameter_as_entry_node_to_operation` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the parameter or entity described by this clue:
- The target operation uses extrusion distance 8 as an input parameter.
Return exactly one ID.
```

#### `parameter_prompt__parameter_as_exit_node_from_operation` coverage=`parameter_as_exit_node_from_operation` candidates=`12` gate=`pass`

```text
Given the CadQuery script, identify the parameter or entity described by this clue:
- The target parameter is the radius emitted by the circle operation descriptor.
Return exactly one ID.
```

#### `parameter_prompt__parameter_as_exit_node_from_measurement` coverage=`parameter_as_exit_node_from_measurement` candidates=`8` gate=`pass`

```text
Given the CadQuery script, identify the parameter or entity described by this clue:
- The target parameter is derived from a zero bounding-box delta measurement.
Return exactly one ID.
```
