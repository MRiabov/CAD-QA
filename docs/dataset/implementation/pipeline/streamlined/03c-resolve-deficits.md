# 03c resolve deficits — cheapest effective loop

> Authoritative: `../03-task-generation/03c-resolve-deficits.md`

READ:
- `DeficitLedger` from `03b`
- `TaskQuotaPlan` → `family_profiles`, `plan_version`, `expansion_tier`
- `ProgramMetadata`

TRANSFORM:
- `03b` records a `DeficitClass` directly; `03c` classifies each `03a` allocation detail by this table:
  - `coverage_infeasible`, `answer_meaning_infeasible` → `structural_deficit`
  - `cap_conflict` → `plan_conflict`
  - `split_capacity_short`, `family_quota_short`, `family_quota_target_conflict` → `capacity_deficit`
  - `quota_target_family_unassigned` → `capability_deficit` when no family profile has the capability, otherwise `capacity_deficit`
- `DeficitClass` is closed: `capability_deficit, probe_deficit, capacity_deficit, construction_deficit, constructor_deficit, plan_conflict, structural_deficit`
- capability lookup: read `family_profiles`; at least one family has the capability → `capacity_deficit`; no family has it → `capability_deficit`; a capability that yields no valid task is a `construction_deficit` or `constructor_deficit`
- `capacity_deficit` → `ProgramReassignmentRequest` first; `ProgramRequest` only when the split itself is short
- `construction_deficit` → `ProgramReassignmentRequest` to raise the attempt budget; a persistent high rate is a `03b` fix
- `constructor_deficit`, `plan_conflict`, and `structural_deficit` → neither loop helps; fix `03b` or the plan
- `probe_deficit` is per state: drop membership for that state and record it; escalate only when no family profile reports a state with a surviving probe
- escalation order: `ProgramReassignmentRequest` to `03a`, then `ProgramRequest` to `01b`, then accept the miss
- fast loop: `03a` residual replan → `03b` resume; no fetch, normalize, or execute
- slow loop: `01b` supplemental selection → `01c` fetch delta → `01d` normalize delta → `02` build graphs for delta → `03a` update family profiles and residual plan → `03b` resume
- an expansion round adds at most 20% of the current program pool; after three rounds stop and record an `AcceptedMiss`
- the round count and growth cap come from `expansion` in `balance.yaml`, stamped into the plan by `03a`
- stop when the deficit is filled, the expansion budget is reached, the deficit is structurally infeasible, or the owner accepts the miss
- record every request, delta, and accepted miss with its plan version
- render nothing and write no release rows

WRITE:
- `ProgramReassignmentRequest` → originating quota target, current family assignment and quota, accepted and remaining counts, unassigned families or unused capacity, requested change, retry budget, plan version
- `ProgramRequest` → originating quota target, missing graph capability, accepted and remaining counts, useful feature tags, collections or family constraints, `extend | target`, requested program count, maximum graph-build budget, reason, plan version
- `AcceptedMiss` → quota target, remaining count, reason, owner, plan version
