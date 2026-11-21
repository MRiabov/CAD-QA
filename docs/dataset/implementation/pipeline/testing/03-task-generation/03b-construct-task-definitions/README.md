# 03b construct task definitions — adversarial integration test (TDD)

**Parent:** [`../../00-testing-strategy.md`](../../00-testing-strategy.md).

**Contract under test:**
[`../../../03-task-generation/03b-construct-task-definitions/README.md`](../../../03-task-generation/03b-construct-task-definitions/README.md).

This folder mirrors the authoritative `03b` folder. The test contract for this pipeline stage is here; the
phase tests are the lettered sub-documents.

## Test inventory

| Doc | Test contract |
|---|---|
| [`a-construction.md`](a-construction.md) | Golden record, validity record, redundant clues, probe deficits, target ambiguity. |
| [`b-answer-semantics.md`](b-answer-semantics.md) | Answer resolution, choice pool, answer uniqueness. |
| [`c-definition-identity.md`](c-definition-identity.md) | Duplicate identity and definition immutability. |

The golden-record test in [`a-construction.md`](a-construction.md) is the
pipeline stage-level happy path: it reads the persisted `TaskDefinition` back through the
reader `04` uses and compares it per
[`../../golden/README.md`](../../golden/README.md).

## What this does not prove

- That the prompt renders. That is
  [`../../04-render-prompt-and-choices.md`](../../04-render-prompt-and-choices.md).
- That the release is balanced. That is
  [`../../05-validate-and-export-release.md`](../../05-validate-and-export-release.md).
- That a value is supported. That is [`../../00-support-tables.md`](../../00-support-tables.md).
