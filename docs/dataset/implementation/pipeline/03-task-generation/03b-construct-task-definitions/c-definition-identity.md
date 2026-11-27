# Definition identity

**Parent:** [`README.md`](README.md).

## Enumeration and identity

`03b` constructs task definitions from the graph into the task quota plan using typed
constructors. Construction is supply-driven: it builds from the facts the graph
has and samples them into the quota targets (`TG-6`). A cell-level demand query
is a deficit-path last resort, not the default. Construction is deterministic for
a given graph, plan version, definition-schema version, and seed. Constructor
order is stable and fixed by `constructor_version`. A quota target that cannot be filled becomes a deficit for `03c`.

Canonical task identity is:

```text
(program_sha256, target binding identity, canonical task clue sequence, answer meaning)
```

For a scalar target, the target binding identity is the measurement name. The
subject is not part of it, because several subjects can share that measurement
value.

`task_id` remains binding-specific: two equal-answer witnesses with the same
canonical clue sequence are different definitions. Construction keeps one by
prompt identity (`DS-REQ-35`), so the release does not carry both.

The canonical task clue sequence preserves dependency order first, then orders
independent clues broad-to-narrow by the size of the narrowed set, descending,
with a stable hash as the tie-break (`TG-7`). The gold answer, answer format,
choices, and prompt wording are not part of `task_id`; they are part of the
definition or a later presentation step. The harness's answer instruction is not
definition content at all.

Validity checks and the narrowing record use the canonical sequence. A later
presentation step may render a permutation that respects reference dependencies;
the permutation does not change `task_id`, and clue wording uses presentation
positions.

Definitions with identical canonical identity are duplicates. `03b` keeps one
and records the duplicate. Invalid definitions go to the failure record and do
not consume quota.

### Canonical serialization

One definition serializes to one canonical JSON object. Its bytes are the hash
input, so every rule below is part of the contract:

- keys sorted by byte order, so the field table can be reordered without changing
  a hash;
- UTF-8 bytes, no byte-order mark, `,` and `:` with no surrounding space, no
  trailing newline;
- non-ASCII characters written as raw UTF-8, not as `\u` escapes. Go disables
  HTML escaping, which would otherwise write `<`, `>`, and `&` as `\u003c`,
  `\u003e`, and `\u0026`;
- a string containing U+2028 or U+2029 is rejected at construction, because Go
  and Python escape those two characters differently;
- absent values written as `null`, never omitted;
- integers written as JSON integers; every other number written as canonical
  decimal text, never as a JSON number;
- UUIDs as lowercase hyphenated text;
- lists keep their recorded order, and the clue list is the canonical clue
  sequence.

`task_id` and `definition_sha256` are excluded from their own hash input.

The definition has no binary float fields. The answer precision rule already
produces canonical decimal text, and the release stores the same `number_text`
and `value_text` fields. Clue
thresholds, ranges, points, and choice answers reuse it. The hash therefore
never formats a float, which is what makes it reproducible across languages:
Go and Python disagree on `1e17` (`100000000000000000` against `1e+17`), on the
exponent's leading zero (`1e-9` against `1e-09`), and on negative zero.

The rule is scoped to the task definition. Graph tables keep native float
columns: they are measured once, read in bulk, and never hashed.

Python serializes with `orjson` and sorted keys; Go uses `encoding/json` with
HTML escaping disabled. Because the definition has no float fields, the library
choice does not change the bytes: only strings, integers, and structure reach
the hash.

### Three hashes

| Hash | Input | Used for |
|---|---|---|
| `task_id` | the canonical task identity | duplicate detection, release key, split-isolation check |
| `definition_sha256` | the canonical task content | accepted-definition immutability, duplicate content, reproduction check |
| `answer_sha256` | the answer and scoring fields | release answer column integrity |

`definition_sha256` covers `state_scope`, `possible_answer_count`,
`target_binding`, `task_clues`,
`clue_reduction_form_profile`, `answer_meaning`, `answer_parameter`,
`gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`, `answer_evidence`,
and `choice_pool` in construction order. It also covers the inputs that change
that content: `program_sha256`, `graph_identity_sha256`, `graph_schema_version`,
`runtime_extraction_sha256`, `constructor_version`, `definition_schema_version`,
and `construction_seed`.

It does not cover `plan_version`, `cadevolve_program_family_id`, `split`, or
`subset`. Those are assignment: `03a` re-enters with a new plan version without
changing an accepted definition, so hashing them would invalidate every accepted
definition on every replan (`TG-3`).

`answer_sha256` covers `gold_answer`, `answer_unit`, `tolerance`,
`scoring_rule`, and `answer_schema_version`. For a multiple-choice task it also
covers the `candidate` of the entry whose label is `gold_answer`, because a label
is a position and does not identify the answer on its own. It excludes
`answer_evidence`, because evidence is audit data and a change to its
representation must not change the answer identity. `04` copies the hash; it does
not recompute it.

`choice_pool` is hashed in construction order, labels included. `04` renders that
order and must not write a new one back.

### Provenance

`provenance` records the inputs the hash depends on, so a mismatch names the input
that moved:

| Field | Meaning |
|---|---|
| `runtime_extraction_sha256` | The CadQuery program runtime extraction result the graph was built from. |
| `graph_identity_sha256` | The `02c` unit identity for the program: the AST result, runtime result, graph schema, builder, tolerance policy, and implementation scope. |
| `constructor_version` | The typed constructor set that produced the definition. |
| `construction_seed` | The seed the constructor sampled with. |
| `plan_version` | The `TaskQuotaPlan` that assigned the quota target. |
| `balance_policy_version` | The balance policy the plan was computed from. |

Rendering provenance — render seed, template version, and `prompts.yaml` hash —
belongs to `04` render prompt and choices, not to the definition (`TG-7`). `05`
validate and export release records those values in the manifest. The template
schema is in [`../../../prompt-templates.md`](../../../prompt-templates.md).
