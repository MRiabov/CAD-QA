# Reviewer Readiness Checklist

Before public paper or dataset release, verify:

- The paper states the CAD BrowseComp thesis clearly.
- Every public row has a matching private row with hidden query program and
  candidate-set trace.
- Every prompt clue maps to a hidden clause.
- Row counts are reported by hop slice, relation family, measurement scope, and
  split.
- Static shortcut baselines are reported.
- Main benchmark and training rows are not solvable from syntax-only clues.
- Syntax-only calibration rows are excluded from headline training/benchmark
  counts or capped by an explicit quota.
- Prompt-family distribution, answer distribution, and geometry-hop coverage
  pass release thresholds.
- Tool-assisted results, if any, are labeled as upper bounds.
- Kernel-sensitive labels include CadQuery, OCP, and OpenCascade versions.
- Quarantined rows are excluded from headline benchmark scores.
- Synthetic fixtures do not dominate release rows.
- Group-safe splits prevent source-family and counterfactual leakage.
