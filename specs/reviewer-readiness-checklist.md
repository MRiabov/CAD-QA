# Reviewer Readiness Checklist

Before public paper or dataset release, verify:

- The paper states the CAD BrowseComp thesis clearly.
- The artifact is being judged against the `benchmark-release` tier. Smoke and
  release-candidate artifacts are development evidence and are not sufficient
  for public benchmark or real fine-tuning claims.
- Every public row has a matching private row with hidden query program and
  candidate-set trace.
- Every prompt clue maps to a hidden clause.
- Row counts are reported by hop slice, relation family, measurement scope, and
  split.
- Benchmark-release artifacts meet the numeric tier in `specs/dataset-spec.md`:
  at least 10,000 release rows, at least 10,000 default SFT rows, at least 95%
  geometry-hop-positive rows, at least 90% `logical_hop_count >= 3` rows, at
  least 99% geometry-critical default SFT rows, 0% syntax-only default SFT rows,
  and no more than 2% syntax-only benchmark rows unless calibration is separated.
- The benchmark-release release report has `valid_for_release=true` and no
  blocking gates, and the matching default SFT report passes
  `--release-tier benchmark-release`.
- Static shortcut baselines are reported.
- Main benchmark and training rows are not solvable from syntax-only clues.
- Syntax-only calibration rows are excluded from headline training/benchmark
  counts or capped by an explicit quota.
- Prompt-family distribution, answer distribution, and geometry-hop coverage
  pass release thresholds.
- At least 10 generated release task families are present, and every generated
  release task family contributes between 1% and 10% of the exported rows.
  Families outside that band block release unless explicitly moved to
  review-only/calibration artifacts.
- Intended release task families with zero generated rows are listed from an
  intended-family manifest or called out manually as unfinished coverage.
- Sparse direct extrema, such as selector-count or selected-entity-count tasks,
  are implemented through graph-hop narrowing instead of being dropped merely
  because the global model rarely has a unique largest/smallest candidate.
- Candidate traces for these narrowed tasks show nontrivial intermediate
  distractors and exactly one final answer.
- Prompt-template distribution and clue-shape distribution pass release
  thresholds; no single checklist shape dominates the benchmark.
- Parameterized families report healthy sampled coverage over axis, sign,
  min/max direction, comparison relation, aggregation metric, value bucket,
  target type, reference type, and rendered wording.
- Exact public measurement values do not usually identify a unique answer by
  themselves. Rows where they do must be tagged and counted as low-hop or
  calibration-style value-bearing rows.
- Value-bearing measurement and cross-feature value-bearing rows are present in
  the default training export above benchmark-release thresholds: 15%-30%
  value-bearing measurement rows and 5%-15% cross-feature value-bearing rows.
- At least 20 prompt templates are present, prompt-template max share is at most
  5%, answer entropy is at least 8 bits, and at least 1,000 unique gold answers
  are present.
- High-hop candidate traces have at least 2 candidates before the final selector,
  with median pre-final breadth at least 4.
- Parameterized families keep each sampled parameter value at or below 35%, and
  each supported axis/direction value at or above 20%, unless the report marks
  that dimension geometry-limited.
- Tool-assisted results, if any, are labeled as upper bounds.
- Kernel-sensitive labels include CadQuery, OCP, and OpenCascade versions.
- Quarantined rows are excluded from headline benchmark scores.
- Synthetic fixtures do not dominate release rows.
- Group-safe splits prevent source-family and counterfactual leakage.
- If all rows collapse into a single protected split group, the artifact is
  labeled as a fine-tuning-format export rather than a multi-split benchmark.
- Benchmark-release split manifests include train/validation/test splits, at
  least 3 protected groups per split, and no train-only collapse.
