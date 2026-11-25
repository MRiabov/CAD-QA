# Oracles

**Status:** draft, 2026-11-21. This directory holds checked-in expected-output
records for pipeline stages, used to calibrate a checker against an independent
expectation.

## What an oracle is

An oracle is a JSON file that pins what a pipeline stage must produce for one
program, verified by a human or by an independent tool. A checker compares a
pipeline stage's actual output with the oracle; a mismatch is a pipeline stage
defect, not a data condition.

An oracle is not a pipeline artifact. The generator never reads it, and the
release never contains it. It is test data with a reviewed diff.

## Why there are many

Different pipeline stages answer different questions, so each has its own oracle kind:

| Oracle kind | Pins | Independent expectation | Owner |
|---|---|---|---|
| [`extraction-graph/`](extraction-graph/) | the CAD graph for one program | plain CadQuery and OCP, plus the program text | `02c` |
| [`task-construction/`](task-construction/) | one hand-authored gold task and its answer | a gold query executed with plain CadQuery, plus a human reading | `03b` |
| `prompt-render/` | the rendered prompt and choices | the prompt contract and a human reading | `04` |

`extraction-graph` and `task-construction` exist. An oracle kind is added when
its pipeline stage has a checker; a record gates a release only when a human
verifies it.

## Naming and layout

```text
pipeline/testing/oracles/<oracle-kind>/<slug>.json
```

`<oracle-kind>` names a pipeline stage and a fact kind, lower-case and hyphenated.
`<slug>` is a stable lower-case slug that matches the file stem. The file is
UTF-8 JSON with a trailing newline.

A new oracle kind gets its own `README.md` with its schema. The schema is
versioned by `schema_version` in each file.

## Rules

- **Reviewed like code.** A diff that adds, removes, or changes an expectation is
  a claim. The reviewer asks which upstream record establishes it. Do not edit an
  oracle to make a failing pipeline stage pass without a contract change.
- **Environment-pinned.** An oracle records the versions that produced it. A
  version change makes it `stale`, and it is re-derived and re-verified, not
  silently reused.
- **Status is explicit.** `proposed` means machine-checked and not yet approved.
  `verified` means a named human approved it. `stale` means the environment or
  contract moved. A `proposed` oracle cannot gate a release.
- **Machine proposes, human disposes.** Derive the expectation from the
  independent record when the oracle kind is machine-derived. A hand-authored
  oracle kind, such as task-construction, writes the expectation by hand and
  proves it with the independent query. Then verify it. Do not author a graph by
  hand.

## Relationship to the other test data

| Path | Holds | Independent expectation |
|---|---|---|
| [`fixtures/`](../fixtures/) | coverage and rejection programs | the pinned corpus |
| [`golden/`](../golden/) | pinned construction results | the construction contract |
| `oracles/` | pinned pipeline stage outputs | the kernel, the program text, and a human |

A golden record pins what `03b` did construct, so a change is visible. A
[task-construction oracle](task-construction/) pins what it should construct,
written by hand and proved by a gold query. An extraction-graph oracle pins what
an earlier pipeline stage should have produced. They are different artifacts and
different owners; do not overload the word "golden."
