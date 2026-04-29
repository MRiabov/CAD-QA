# Multi-Hop QA Mock Experiment Notes

This first pass contains three hand-authored candidate samples. They are meant
to pressure-test the proposed architecture before any LLM rendering or
OpenRouter calls.

## Samples

### `mhqa_mock_001`: Repeated Top-Face Holes

Source shape: synthetic CadEvolve-style script with two boxes, an extrusion,
and three repeated top-face holes.

Gold answer: `hole_3`

Question shape:

```text
Given the CadQuery script, identify the feature that satisfies all of these
constraints:

- It is a subtractive hole feature.
- Its setup is made from the top face of the immediately previous result.
- It comes after two earlier hole features in the repeated pattern.
- Its center offset is on the positive-X side of the repeated holes.
- It removes material while leaving the global bounding box unchanged.

Return exactly one feature ID.
```

Initial read: this is the cleanest MVP sample. It uses current-ish trace
families: operation order, selector/workplane context, center offset, signed
volume delta, and bbox delta. The positive-X clue plus "after two earlier hole
features" may be a bit easy, but that is useful for calibration.

### `mhqa_mock_002`: Final Circular Boss On Helix

Source shape: real CadEvolve-C ArrayBossHelixWire-style script with a swept
helix body and repeated circular bosses unioned into it.

Gold answer: `wp37`

Question shape:

```text
Given the CadQuery script, identify the feature that satisfies all of these
constraints:

- It is an extruded circular boss, not the helical sweep and not a union step.
- Its circular profile has radius 5 and the extrusion distance is 8.
- Among the repeated boss workplanes, its workplane origin has the greatest Z
  coordinate.
- The final result is produced by unioning this boss into the accumulated swept
  body.

Return exactly one feature ID.
```

Initial read: realistic, but the final-union clue is probably too direct in
checklist form. It should be kept as a leakage calibration case. A better
version might remove the final-union clue and add a less direct spatial or
topological clue.

### `mhqa_mock_003`: Star Slots And Rectangular Blind Cuts

Source shape: real CadEvolve-P ShapeNet-style script with a box, star-shaped
through cuts on side faces, and rectangular blind cuts generated in a loop.

Gold answer: `slot_y_pos_upper_cut`

Question shape:

```text
Given the CadQuery script, identify the loop-expanded feature that satisfies
all of these constraints:

- It is a rectangular blind cut rather than one of the star-shaped through cuts.
- It is made from the positive-Y face selector.
- The rectangle uses the box length for one side and R_out * R_in for the other
  side.
- It is the positive-Z member of the repeated pair of rectangular cuts.
- It removes material without changing the outer bounding box.

Return exactly one loop-expanded feature ID.
```

Initial read: this is the most architecture-revealing sample. It looks like the
kind of question we want, but it depends on loop-expanded feature IDs that the
current public row contract may not support. Before sending this to LLMs, we
should decide whether loop-expanded feature IDs are valid public answers or
whether this sample should be converted to an enum/comparison task.

## First-Pass Takeaways

- Checklist style is good enough for inspecting hidden clause alignment.
- The mock query objects make distractors explicit, which is useful.
- The renderer should produce multiple variants for `mhqa_mock_002` because the
  current version leaks through the final-union clue.
- Loop-expanded feature IDs need an explicit policy before samples like
  `mhqa_mock_003` can become release candidates.
- The next useful step is not a live LLM call yet. First, run the mock scorer,
  inspect the critical judge failures, and revise the public sample text.
