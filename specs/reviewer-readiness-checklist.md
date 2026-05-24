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
- Every generated release task family contributes between 1% and 10% of the
  exported rows. Families outside that band block release unless explicitly moved
  to review-only/calibration artifacts.
- Intended release task families with zero generated rows are listed from an
  intended-family manifest or called out manually as unfinished coverage.
- Prompt-template distribution and clue-shape distribution pass release
  thresholds; no single checklist shape dominates the benchmark.
- Parameterized families report healthy sampled coverage over axis, sign,
  min/max direction, comparison relation, aggregation metric, value bucket,
  target type, reference type, and rendered wording.
- Exact public measurement values do not usually identify a unique answer by
  themselves. Rows where they do must be tagged and counted as low-hop or
  calibration-style value-bearing rows.
- Value-bearing measurement and cross-feature value-bearing rows are present in
  the default training export above the configured coverage thresholds.
- Tool-assisted results, if any, are labeled as upper bounds.
- Kernel-sensitive labels include CadQuery, OCP, and OpenCascade versions.
- Quarantined rows are excluded from headline benchmark scores.
- Synthetic fixtures do not dominate release rows.
- Group-safe splits prevent source-family and counterfactual leakage.
- If all rows collapse into a single protected split group, the artifact is
  labeled as a fine-tuning-format export rather than a multi-split benchmark.
