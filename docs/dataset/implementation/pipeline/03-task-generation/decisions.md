# Task generation decisions

**Parent:** [`README.md`](README.md).

**Status:** active, 2026-11-20.

This document records decisions scoped to the `03` task-generation module. A
decision here explains why the module contract has its current shape; the
contract remains normative. An accepted decision is not silently rewritten. A
change adds a new decision and marks the old one superseded.

Decisions that span stages belong in [`../../../decisions.md`](../../../decisions.md)
instead, and unanswered questions belong in the `## Open questions` section of
the document that owns them.

## TG-1 — Every task clue must be necessary

- **Status:** accepted (2026-11-20).
- **Context:** A clue that narrows at its position can still be redundant:
  dropping it may leave the task answer-unique, so the chain is longer than the
  reasoning it encodes. The weaker rule "each non-final clue leaves at least two
  answers" constrains only where the chain ends, and a redundant middle clue
  passes it.
- **Decision:** Every task clue must be necessary. Removing it from the chain
  must leave at least two distinct answers, or change the answer. Distinct
  answers are compared with `same_answer` at the stated precision. A redundant
  clue is dropped and the task shortened, or the chain is rejected.
- **Consequences:** The achievable step count is the number of necessary clues
  plus the answer step, so a quota target above it is a deficit. Long chains over
  continuous answers need a candidate set that shrinks gradually, so
  continuous-answer tasks are shorter on average than identity tasks.

## Pending

One module-scoped decision is accepted. The remaining candidates are the
construction questions in `plans/nov-19/03b-task-construction-design.md`:

| Candidate | Question |
|---|---|
| `D8` | In what order are quota targets filled, and when is a task accepted? |
| `D9` | Is clue operand form a coverage dimension, a balance dimension, or both? |
| `D10` | What role does clue form play in reporting? |

Each moves here as an accepted decision once it is answered.
