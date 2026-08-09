# row:graph:src_d42a84549ea74920:synth:v2:parameterized_feature_rank

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp6`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -100))
wp2 = wp1.splineApprox([[85, 0, 1], [85, 5, 3], [84, 11, 5], [83, 16, 7], [82, 21, 9], [81, 26, 11], [79, 31, 13], [77, 36, 15], [74, 41, 17], [72, 45, 19], [69, 50, 21], [65, 54, 23], [62, 58, 25], [58, 62, 27], [54, 65, 29], [50, 69, 31], [45, 72, 33], [41, 74, 35], [36, 77, 37], [31, 79, 39], [26, 81, 41], [21, 82, 43], [16, 83, 45], [11, 84, 47], [5, 85, 49], [0, 85, 51], [-5, 85, 53], [-11, 84, 55], [-16, 83, 57], [-21, 82, 59], [-26, 81, 61], [-31, 79, 63], [-36, 77, 64], [-41, 74, 66], [-45, 72, 68], [-50, 69, 70], [-54, 65, 72], [-58, 62, 74], [-62, 58, 76], [-65, 54, 78], [-69, 50, 80], [-72, 45, 82], [-74, 41, 84], [-77, 36, 86], [-79, 31, 88], [-81, 26, 90], [-82, 21, 92], [-83, 16, 94], [-84, 11, 96], [-85, 5, 98], [-85, 0, 100], [-85, -5, 102], [-84, -11, 104], [-83, -16, 106], [-82, -21, 108], [-81, -26, 110], [-79, -31, 112], [-77, -36, 114], [-74, -41, 116], [-72, -45, 118], [-69, -50, 120], [-65, -54, 122], [-62, -58, 124], [-58, -62, 126], [-54, -65, 128], [-50, -69, 130], [-45, -72, 132], [-41, -74, 134], [-36, -77, 135], [-31, -79, 137], [-26, -81, 139], [-21, -82, 141], [-16, -83, 143], [-11, -84, 145], [-5, -85, 147], [0, -85, 149], [5, -85, 151], [11, -84, 153], [16, -83, 155], [21, -82, 157], [26, -81, 159], [31, -79, 161], [36, -77, 163], [41, -74, 165], [45, -72, 167], [50, -69, 169], [54, -65, 171], [58, -62, 173], [62, -58, 175], [65, -54, 177], [69, -50, 179], [72, -45, 181], [74, -41, 183], [77, -36, 185], [79, -31, 187], [81, -26, 189], [82, -21, 191], [83, -16, 193], [84, -11, 195], [85, -5, 197], [85, 0, 199]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -100))
wp4 = wp3.moveTo(85, 0)
wp5 = wp4.rect(3, 3)
wp6 = wp5.sweep(wp2, isFrenet=True)
wp7 = cq.Workplane('XY', origin=(0, 0, -100))
wp8 = wp7.circle(86)
wp9 = wp8.extrude(200)
wp10 = wp9.cut(wp6)
result = wp10
```

Identify the target feature that satisfies all of these constraints:
- The target feature can be described by its centroid Y coordinate.
- Within the narrowed set, select the 3rd candidate in increasing centroid Y coordinate order.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Let’s reason it through.  

The script builds a sweep (wp6) of a 3×3 rectangle (wp5) along a 3D spline path (wp2), then cuts that sweep from a large extruded cylinder (wp9).  
The target is to identify a “feature” by its centroid Y coordinate, then pick the 3rd candidate in increasing Y order.

The only workplanes explicitly named that have a clear Y-related geometry are the workplane definitions: `wp1`, `wp3`, `wp7`. But these are just coordinate systems, not features with centroids. However, "features" here likely refers to the solids generated — the main result is the cut object (wp10), but also intermediate items like wp6 (sweep) and wp9 (cylinder).  

The cut removes the sweep from the cylinder, leaving a hole; the **sweep** itself is a long, twisted, helix-like solid whose centroid Y coordinate can be ordered among different parts.  

The only named variable representing a solid feature whose Y centroid location varies meaningfully in this script is `wp6`.  
Ordering features by centroid Y and picking 3rd yields `wp6`.

```json
{"name": "submit_text", "arguments": {"text": "wp6"}}
```
```
