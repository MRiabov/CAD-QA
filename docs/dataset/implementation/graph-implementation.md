# Graph implementation

**Status:** draft, 2026-10-21. This document defines technical implementation
questions for the CAD graph. The graph requirements are in
[`../requirements/graph-content.md`](../requirements/graph-content.md).

## 1. Scope

The implementation must build the graph elements the requirements define, attach
evidence, represent selector results, and choose which measurements are derived
or measured. It does not define task text, answer format, or release layout.

## 2. Open questions

- **Q2.** Should CadQuery selector results be stored as entities, as a relation,
  or both?
  - **Option A — entity only.** A CadQuery selector-result entity, with no membership
    edges.
  - **Option B — relation only.** `selected_by` edges from entities, with no
    result-set entity.
  - **Option C — both.** A CadQuery selector-result entity for counts and aggregation,
    plus `selected_by` edges for membership.
  - **Recommendation:** C. Example: `.faces(">Z")` produces one CadQuery selector-result
    entity, a `selected_from` edge to the solid state, and `selected_by` edges to
    the selected faces. Counts read the CadQuery selector-result entity; “which face was selected” reads
    the edges.

- **Q3.** Which measurements can be derived exactly from the program text, and
  which must always be measured by CadQuery?
  - **Option A — measure everything.** Simple, but loses exact syntax evidence.
  - **Option B — derive everything possible from syntax.** Fast, but wrong when
    later operations change the geometry.
  - **Option C — derive only exact syntax values; measure geometry.** Use exact
    rules for literals, operation counts, and selector membership; measure
    volumes, areas, distances, and topology after operations.
  - **Recommendation:** C, with the evidence recording which path was used.
    Example: `.box(10, 20, 5)` gives a volume of 1000 only if no later
    operation changes it; a fillet volume is measured. A derived value must
    carry the rule that produced it.
