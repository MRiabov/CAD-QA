# Support and capability derivations

**Parent:** [`README.md`](README.md).

## Program capability census

`03a` derives the [program capability census](../algorithm/program-capability-census.md)
from the graphs it already reads. The census is not an input and not an artifact:
it is one function, called here and in `03b` construct task definitions.

For each active program the census answers which target categories, clue
constructors, clue operand forms, measurements, answer meanings, and point probes
the graph has. `03a` derives it once per graph batch, stores the per-program
census in `program_census` and the union per family in `family_profiles`, and
assigns quota targets from that projection. `03b` reads the program's entry
rather than deriving the census again.

A fast-loop replan does not derive the census again: the graph batch has not
changed and both `program_census` and `family_profiles` are already in the plan. A
slow-loop round derives it only for the programs the round adds. `03c` resolve
deficits reads `family_profiles` rather than the census.

## Support-table derivation

`03a` calls the same derivation that writes the task reasoning step support
tables; it does not read the tables as data (`TG-4`). The derivation is defined
in [`../../../task-step-support.md`](../../../task-step-support.md).

- `supported_values(task_reasoning_step_count, quota_dimension)` is the
  support-table derivation's output. `03a` calls that derivation in-process;
  `05` validate and export release reads the tables it writes. There is one
  derivation, not a scope file plus a grammar model. The derivation takes
  `implementation_scope` from the requirement marks, so a value above the
  release scope has no row.
