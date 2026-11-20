# 02a extract CadQuery AST — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../02a-extract-cadquery-ast.md`](../02a-extract-cadquery-ast.md),
with the accept and reject boundary in
[`../extraction/validation.md`](../extraction/validation.md) and the
classification in
[`../extraction/ast/algorithm/pipeline.md`](../extraction/ast/algorithm/pipeline.md).

## Happy-path integration test (test-first, adversarial)

`test_02a_extract_happy_path_adversarial` — extracts the golden program in
[`golden/box-with-hole.json`](golden/box-with-hole.json) and asserts the persisted
`CadQueryAstExtractionResult` read back through the reader `02c` build CAD graph
uses.

**Given** the golden program's normalized text, which is one CadQuery call per
assignment.

**When** `02a` extracts it.

**Then** assert the persisted result:

- `program_id`, `program_sha256`, and `normalization_version` equal the
  normalized program row;
- `imports` holds exactly one `import cadquery as cq`;
- six operations, with `order` 0 to 5, `operation_id` `op:000000` to `op:000005`,
  `source_line` 3 to 8, and `result_var` `wp`, `box`, `top`, `plane`, `hole`,
  `result`;
- `receiver_var` is null for the `cq.Workplane` constructor and names the earlier
  variable for the other five;
- the classification is `workplane`, `solid`, `cadquery_selector`, `workplane`,
  `sketch`, `modifier`;
- `is_state_producing` is true only for `box` and `cutBlind`, and each of them
  carries `feature_kind` and `solid_kind`: `add_material` and `primitive`, then
  `remove_material` and `modifier`;
- `input_vars` is in first-use order, so `box` reads `wp`, and `cutBlind` reads
  `hole`;
- the CadQuery selector record has category `face`, expression `>Z`, and
  receiver `box`;
- the CadQuery workplane record for `cq.Workplane("XY")` names the `XY` plane and
  records an explicit frame status;
- no column carries a volume, area, length, state ID, or entity ID: extraction
  states what the program says, not what the kernel returns.

`test_02a_expression_tree_is_not_evaluated` — a program whose workplane is built
from a plane and two vectors yields one operation. Its first argument is a call
expression, the plane call has `origin` and `normal` keyword expressions, and
each of those is a vector call carrying three literals. The operation count stays
one: nested constructors are expressions, not operations. The test asserts the
tree shape, never a resolved coordinate.

`test_02a_selector_forms` — three programs write the same CadQuery selector as
a string, as an implicit no-argument call, and as a `cq.NearestToPointSelector`
call. Each produces one CadQuery selector record with the face category, and none
resolves the CadQuery selector to an entity, because evaluation belongs to `02b`.

`test_02a_alias_is_not_an_operation` — `alias = box` produces an alias with an
`alias_id`, no operation ID, and it consumes an assignment index, so the next
operation is `op:000002`. `result = alias` satisfies the final-`result` rule and
carries the copied category and frame status.

**TDD pin:** pins the six-operation golden extraction, the state-producing pair,
the CadQuery selector and workplane records, the expression tree, and the alias
rule
before `02a` exists.

## Failure-mode tests

- `test_02a_chained_call` — the same box with a hole written as one chained call
  is rejected as `chained_call`. This is the regression guard for the fixture:
  the golden program is flat because the accepted subset is flat.
- `test_02a_rejection_is_whole_program` — a program with a loop is rejected as
  `module_shape` and writes no operations, aliases, workplanes, profiles, paths,
  or selectors.
- `test_02a_no_execution` — a program that calls `open` is rejected as
  `unsupported_call` and the test's canary file is untouched; a program whose
  body would raise at run time still extracts, because nothing is imported or
  called.
- `test_02a_failure_precedence` — a program with an unknown method and a
  duplicate target reports `unknown_method`, and one with a syntax error and an
  unknown method reports `syntax`, following the documented order rather than
  the order of discovery.
- `test_02a_failure_record` — the rejection carries `pipeline_stage`
  `02a_extract_cadquery_ast`, the reason code from the closed set,
  `source_line` and `source_span`, and the same `failure_id` on a re-run.
- `test_02a_unknown_method_is_not_a_partial_extraction` — one allowlisted call
  before one unknown call yields no operations, not the first one.

## What this does not prove

- That the program runs. That is
  [`02b-execute-cadquery.md`](02b-execute-cadquery.md).
- That the extracted entities form a graph. That is
  [`02c-build-cad-graph.md`](02c-build-cad-graph.md).
- That the text is canonical. That is
  [`01d-normalize-programs.md`](01d-normalize-programs.md).
