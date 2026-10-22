# AST extraction result schema

**Parent:** [`README.md`](README.md).

This document fixes the AST extraction artifact schema produced by `02a`. Physical
partitioning is in [`artifacts.md`](artifacts.md); field meanings are in the
`ast/` documents.

`static_schema_version = "cadqa-static-v1"`.

## Common columns

Every AST extraction table carries:

- `program_id: STRING`;
- `program_sha256: STRING`;
- `normalization_version: STRING`;
- `extractor_version: STRING`;
- `static_schema_version: STRING`;
- `canonicalization_version: STRING`.

No AST extraction table carries timestamps, hostnames, process IDs, absolute paths, or
kernel handles.

## `static_program`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `static_status` | `STRING` enum `success`, `failure` | not null | Terminal result. |
| `import_alias` | `STRING` | null | Always `cq` on success. |
| `static_model_sha256` | `STRING` | null | Canonical hash of the complete CadQuery program AST extraction result. |
| `failure_kind` | `STRING` | null | AST rejection category. |
| `failure_message` | `STRING` | null | Failure message. |
| `failure_line` | `INT64` | null | One-based CadQuery program line. |

Exactly one row exists per `program_id`.

## `static_operations`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `operation_id` | `STRING` | not null | `op:<order:06d>`. |
| `order` | `INT64` | not null | Zero-based assignment index. |
| `source_line` | `INT64` | not null | One-based call start line. |
| `source_span` | `SourceSpan` | not null | Call span. |
| `result_var` | `STRING` | not null | Assigned variable. |
| `method` | `STRING` | not null | Allowlisted method or qualified constructor. |
| `operation_kind` | `STRING` enum `OperationKind` | not null | Operation category. |
| `receiver` | `StaticExpression` | null | Receiver expression. |
| `receiver_var` | `STRING` | null | Receiver name when it is a `Name`. |
| `args` | `LIST<StaticExpression>` | not null | Positional arguments. |
| `kwargs` | `MAP<STRING, StaticExpression>` | not null | Keyword arguments. |
| `input_vars` | `LIST<STRING>` | not null | Read variables in program order. |
| `is_state_producing` | `BOOLEAN` | not null | Solid state producing flag. |
| `feature_kind` | `STRING` | null | Required for solid state producing operations. |
| `solid_kind` | `STRING` | null | Required for solid state producing operations. |

## `static_aliases`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `alias_id` | `STRING` | not null | `alias:<order:06d>`. |
| `alias_kind` | `STRING` enum `name`, `subscript` | not null | Alias form. |
| `order` | `INT64` | not null | Zero-based assignment index. |
| `source_line` | `INT64` | not null | One-based assignment line. |
| `result_var` | `STRING` | not null | New variable. |
| `target_var` | `STRING` | null | Root target name. |
| `target_expression` | `StaticExpression` | null | Subscript target. |
| `source_span` | `SourceSpan` | not null | Assignment span. |

## `static_workplanes`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `workplane_id` | `STRING` | not null | `<operation_id>:<ordinal>`. |
| `operation_id` | `STRING` | not null | Creating operation. |
| `workplane_kind` | `STRING` enum `named`, `custom`, `face` | not null | CadQuery workplane category. |
| `named_plane` | `STRING` enum `xy`, `yz`, `xz` | null | Named plane. |
| `origin` | `Point3D` | null | AST frame origin. |
| `x_direction` | `Vector3D` | null | AST x direction. |
| `normal` | `Vector3D` | null | AST normal. |
| `frame_status` | `STRING` enum `explicit`, `derived`, `unknown` | not null | AST frame confidence. |
| `derived_from_workplane_id` | `STRING` | null | Receiver CadQuery workplane. |
| `source_selector_id` | `STRING` | null | Face CadQuery selector. |
| `offset` | `DOUBLE` | null | Offset. |
| `tag` | `STRING` | null | Tag. |
| `args` | `LIST<StaticExpression>` | not null | Unevaluated arguments. |
| `source_span` | `SourceSpan` | not null | Creating call span. |

## `static_profiles`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `profile_id` | `STRING` | not null | `<operation_id>:<ordinal>`. |
| `operation_id` | `STRING` | not null | Creating operation. |
| `profile_kind` | `STRING` enum `ProfileKind` | not null | CadQuery profile category. |
| `dimensions` | `MAP<STRING, StaticExpression>` | not null | Named dimensions. |
| `points` | `LIST<Point2D>` | null | Fixed points. |
| `is_closed` | `BOOLEAN` | not null | Closed boundary flag. |
| `workplane_id` | `STRING` | null | CadQuery workplane. |
| `source_span` | `SourceSpan` | not null | Creating call span. |

## `static_paths`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `path_id` | `STRING` | not null | `<operation_id>:<ordinal>`. |
| `operation_id` | `STRING` | not null | Creating operation. |
| `path_kind` | `STRING` enum `PathKind` | not null | Path category. |
| `points` | `LIST<Point3D>` | null | Fixed points. |
| `segments` | `LIST<PathSegment>` | not null | Segment records. |
| `is_closed` | `BOOLEAN` | not null | Closed path flag. |
| `workplane_id` | `STRING` | null | CadQuery workplane. |
| `source_span` | `SourceSpan` | not null | Creating call span. |

`PathSegment` is defined in
[`ast/algorithm/shape-derivation.md`](ast/algorithm/shape-derivation.md).

## `static_selectors`

| Column | Parquet value category | Null | Meaning |
|---|---|---|---|
| `selector_id` | `STRING` | not null | `sel:<operation_id>:<ordinal>`. |
| `operation_id` | `STRING` | not null | Evaluating operation. |
| `selector_kind` | `STRING` enum `string`, `call`, `filter`, `implicit` | not null | CadQuery selector category. |
| `selected_entity_category` | `STRING` enum `face`, `edge`, `vertex` | not null | Selected entity category. |
| `selector_expression` | `STRING` | null | CadQuery selector string. |
| `receiver_var` | `STRING` | not null | Receiver variable. |
| `filter_predicate` | `FilterPredicate` | null | Filter predicate. |
| `source_span` | `SourceSpan` | not null | CadQuery selector call span. |

## Nested models

```text
SourceSpan = STRUCT<
  start_line: INT64,
  start_column: INT64,
  end_line: INT64,
  end_column: INT64
>

Point2D = STRUCT<x: DOUBLE, y: DOUBLE>
Point3D = STRUCT<x: DOUBLE, y: DOUBLE, z: DOUBLE>
Vector3D = STRUCT<x: DOUBLE, y: DOUBLE, z: DOUBLE>

DictEntry = STRUCT<
  key: StaticExpression,
  value: StaticExpression
>

FilterPredicate = STRUCT<
  attribute: STRING,
  comparator: STRING,
  threshold: DOUBLE
>

StaticExpression = STRUCT<
  expression_kind: STRING,
  source_span: SourceSpan,
  literal_value: STRING | NULL,
  name: STRING | NULL,
  value_expression: StaticExpression | NULL,
  attribute: STRING | NULL,
  subscript: StaticExpression | NULL,
  callee: StaticExpression | NULL,
  args: LIST<StaticExpression>,
  kwargs: MAP<STRING, StaticExpression>,
  elements: LIST<StaticExpression>,
  entries: LIST<DictEntry>,
  operator: STRING | NULL,
  operand: StaticExpression | NULL,
  lambda_parameter: STRING | NULL,
  lambda_body: StaticExpression | NULL
>
```

`literal_value` uses a tagged string encoding for hash and Parquet stability:
`int64:<value>`, `double:<canonical decimal>`, `string:<value>`, `bool:true`,
`bool:false`, or `null`.

Expression trees are nested values. They are never JSON strings on the bulk
data path.

## AST extraction result hash

`static_model_sha256` is the SHA-256 of the canonical JSON of all AST extraction rows for
one program, using [`canonicalization.md`](canonicalization.md). Rows are sorted
by their table key. It covers the program row, operations, aliases, CadQuery
workplanes, CadQuery profiles, paths, and CadQuery selectors.

An AST rejection has `static_model_sha256 = null` and no downstream table rows.
