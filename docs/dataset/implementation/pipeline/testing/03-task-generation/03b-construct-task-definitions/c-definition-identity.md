# 03b/c definition identity — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03b-construct-task-definitions/c-definition-identity.md`](../../../03-task-generation/03b-construct-task-definitions/c-definition-identity.md).

## Tests

`test_03b_duplicate_definition` — a second definition with the same canonical
identity is recorded as `definition_unique` and does not consume quota.

`test_03b_definition_immutable` — a re-run with the same input versions produces
a byte-identical definition and `definition_sha256`; a changed `plan_version`
does not change either.

`test_03b_hash_boundaries` — `definition_sha256` changes when a content field or
an input version changes, and does not change when `plan_version`, `split`,
`subset`, or `cadevolve_program_family_id` changes. `answer_sha256` changes when
an answer or scoring field changes and does not change when
`answer_evidence` changes.

`test_03b_canonical_json_is_stable` — two runs serialize the same definition to
identical bytes: sorted keys, no spaces, raw UTF-8, no trailing newline, no
binary floats. A string containing U+2028 or U+2029 is rejected.

**TDD pin:** pins duplicate detection, the hash boundaries, and canonical
serialization before `03b` exists.

## What this does not prove

- That the answer is right. That is [`b-answer-semantics.md`](b-answer-semantics.md).
- That `04` copies the hash instead of recomputing it. That is
  [`../../04-render-prompt-and-choices.md`](../../04-render-prompt-and-choices.md).
