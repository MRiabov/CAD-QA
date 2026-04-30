# Extracting CADEvolve Features

CADEvolve executable CadQuery scripts are the primary source for CAD-QA.

Extraction proceeds in layers:

1. Normalize source text and assign a stable `source_id`.
2. Parse assignments and call chains with Python AST.
3. Create feature and operation nodes for CadQuery construction calls.
4. Create parameter nodes for literal and named arguments.
5. Extract profile nodes for `.circle(...)`, `.rect(...)`, and
   `.polyline(...).close()`.
6. Extract workplane frame nodes from default workplanes and explicit
   `cq.Plane(...)` constructors.
7. Link profiles to workplanes and to feature applications.
8. Attach snapshot-derived measurements when trace data is available.

The extractor should prefer conservative, explicit evidence over guessed
geometry. Unsupported relations should be emitted as diagnostics, not labels.
