# Paper figures

## Example CAD-QA task

`task-example.png` is the report's worked example: the full question on the
left, the final solid state on the right, and the target plus the entity each
clue names in distinct colours with numbered badges. It is generated from the
checked-in gold record
[`box-with-hole-edge-length.json`](../../dataset/implementation/pipeline/testing/oracles/task-construction/box-with-hole-edge-length.json),
so the wording, clues, and answer are the reviewed ones, not retyped for the
figure.

### Build

Requirements: CadQuery 2.8+ (the `cadquery` extra), Blender 5.x on `PATH`, and
Pillow 12+. The fonts are Noto Sans and DejaVu Sans Mono.

```bash
uv run --extra cadquery python docs/paper/figures/task_figure.py
```

If Pillow is not in the environment, install it first (`uv pip install pillow`).

The command writes:

| Path | Content |
|---|---|
| `docs/paper/figures/task-example.png` | the final 1890 × 680 figure at 300 dpi |
| `runs/manual_verification/paper_figure/<slug>/scene.json` | the typed geometry, colours, camera, and labels |
| `runs/manual_verification/paper_figure/<slug>/render.png` | Blender's transparent render |
| `runs/manual_verification/paper_figure/<slug>/projection.json` | label positions projected through the render camera |

`--skip-blender` reuses the last render and only recomposes the panel, which is
useful while adjusting typography. `--oracle <slug>` selects another gold
record; the label anchors are tuned for a face or edge target, so a different
category needs an anchor in `_label_position`.

### How it works

`task_figure.py` is the entry point. It calls `figure_scene.build_figure`,
which executes the oracle's CadQuery program, binds the answer's target and the
entity named by each clue through the record's own filters, tessellates those
entities, and returns the typed scene and panel; `task_figure.py` writes
`scene.json`. `blender_render.py` runs inside Blender, builds meshes and materials, an
orthographic camera, and renders flat technical shading with Workbench. The same
script projects the label anchors to pixels.
Back in `task_figure.py`, Pillow lays out the question, clue list, program,
answer, legend, and badges.

The 3D picture is Blender's; this directory contains no renderer. The geometry
selection is the only CAD-specific step.

The render is deterministic: the record, tessellation tolerance, camera, and
shading settings are fixed in the two scripts. The program is not part of the
figure: at 160 mm text width a 25 % code column forces roughly 4 pt type, which
is the readability failure this layout fixes. The prose or a separate listing
carries the program.
