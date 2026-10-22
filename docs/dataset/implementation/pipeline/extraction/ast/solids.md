# AST solids

**Parent:** [`extraction/README.md`](../README.md).

These fields specialize a `StaticOperation` for solid-producing calls.

| Field | Field type | Origin | Required | Meaning | Consumer |
|---|---|---|---|---|---|
| `operation_id` | string | AST | yes | Operation identity. | 02b, 02c |
| `feature_kind` | FeatureKind | AST | yes | Add material, remove material, modify, or construction. | 02c |
| `solid_kind` | SolidKind | AST | yes | Primitive, extrude, loft, sweep, revolve, twist, text, boolean, assembly, modifier, or transform. | 02c |
| `receiver_var` | string or null | AST | no | Input solid variable. | 02b |
| `operand_vars` | list of string | AST | yes | Other solid variables read by the call. | 02b |
| `parameters` | map of string to StaticExpression | AST | yes | Unevaluated feature parameters. | 02c |
| `result_var` | string or null | AST | no | Output variable. | 02b, 02c |
| `source_span` | SourceSpan | AST | yes | Span of the call. | review |

## Mapping

- Primitives: `box`, `cylinder`, `sphere`, `cq.Solid.makeSphere`.
- Swept solids: `extrude`, `loft`, `sweep`, `revolve`, `twistExtrude`.
- Text: `text`.
- Booleans: `union`, `cut`, `intersect`.
- Assembly: `combine`, `newObject`, `add`, `cq.Solid.fuse`, `cq.Compound.fuse`.
- Modifiers: `cutBlind`, `cutThruAll`, `hole`, `cskHole`, `cboreHole`, `fillet`,
  `chamfer`, `shell`, `split`, `clean`, `rarray`.
- Transforms: `translate`, `rotate`, `mirror`, `transformed`.

`feature_kind` and `solid_kind` are static classifications. The complete method
table is in [`algorithm.md`](algorithm.md). Runtime material change and topology
change are measured in [`cadquery/effects.md`](../cadquery/effects.md).
