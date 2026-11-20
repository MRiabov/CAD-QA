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

## TG-2 — Fill targets by priority, then scarcity, and reject overfill

- **Status:** accepted (2026-11-20).
- **Context:** One task counts toward several quota targets at once: target
  category, clue type, answer meaning, answer format, and task reasoning step
  count. `03a` defines a minimum, a target count, and a maximum for each target,
  plus a priority tier (coverage, then balance, then volume), but it does not
  define the order in which targets are filled or what to do when one acceptance
  would affect several targets at once.
- **Decision:** Fill targets in the `03a` priority order, and within a tier
  process the scarcest targets first, where scarcity is the number of active
  programs whose graph can support the target. A task is accepted when it fills
  an unfilled target and does not push any cell past its maximum. An acceptance
  that would overfill is rejected and recorded.
- **Consequences:** The scheduler is deterministic given the plan, the ledger,
  and the program order. Scarcity-first takes rare targets early, so a later
  supply-driven sweep cannot starve them. Overfill is visible in the ledger
  rather than silently absorbed.

## TG-3 — Definition identity excludes assignment

- **Status:** accepted (2026-11-20).
- **Context:** A definition carries both content and assignment. The content is
  the task: state scope, binding, clues, answer, evidence, choices. The
  assignment is which plan version, family, split, and subset the task landed
  in. `03a` re-enters with a new plan version whenever a deficit is resolved,
  and accepted definitions must stay valid across that re-entry. Hashing the
  whole record would change every `definition_sha256` on every replan, so the
  immutability rule in `03a` could never hold.
- **Decision:** `definition_sha256` covers the content and the inputs that
  change it — program hash, graph schema version, runtime extraction hash,
  constructor version, definition schema version, and construction seed. It
  excludes `plan_version`, the program family, the split, and the subset.
  `task_id` covers the canonical task identity only, so it is stable across a
  replan. `answer_sha256` covers the answer and scoring fields and excludes
  answer evidence.
- **Consequences:** A replan preserves accepted definitions and their hashes. A
  hash mismatch means the content or one of its inputs changed, and the
  provenance block names which. Assignment changes are visible in the plan and
  the release row, not in the definition hash.

## Pending

Three module-scoped decisions are accepted, and no module-scoped question is
pending. Feature-wide construction decisions live in
[`../../../decisions.md`](../../../decisions.md).
