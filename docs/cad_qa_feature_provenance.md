# Feature Provenance In CAD-QA

Feature provenance is represented as ontology relations and scoped
measurements, not as a standalone task pipeline.

Useful relation families:

- `created_by`;
- `modified_by`;
- `deleted_by`;
- `adds_material_to`;
- `removes_material_from`;
- `bounded_by`;
- `uses_profile`;
- `used_by`.

Release-grade provenance requires explicit evidence. Conservative source-order
or adjacent-snapshot evidence may be used for diagnostics, but rows that cannot
distinguish exact builder history from merged or ambiguous geometry must carry
a quarantine reason.

Public prompts should describe visible CadQuery evidence such as
`.extrude(...)`, `.union(...)`, `.cutBlind(...)`, `.cutThruAll()`, and
`.faces(...)` rather than private provenance jargon.
