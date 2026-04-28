# CAD-QA Paper Draft Notes

This directory contains the working manuscript scaffold for epic 12. It is a
draft artifact, not a final paper. Keep quantitative claims tied to generated
release artifacts and leave placeholders when the current local run is only a
smoke or release-candidate probe.

## Files

- `cadqa_draft.md`: section-level draft for abstract, introduction, related
  work, dataset construction, tasks, experiments, discussion, and conclusion.

## Refresh Checklist

Before using text from this draft in a public manuscript:

1. Regenerate the release-candidate dataset and run `cadqa validate`.
2. Rebuild `dataset_stats.json`, `failure_report.json`, and the dataset card.
3. Rebuild baseline and model comparison reports with
   `scripts.experiments.compare_experiment_runs`.
4. Replace all `[RESULT: ...]`, `[CITE: ...]`, and `[TABLE: ...]` placeholders.
5. Confirm limitations still match `docs/implementation_status.md`.
