# CAD-QA Paper Draft Notes

This directory contains the working manuscript scaffold for the CAD-QA paper.
The paper frame is now: **CAD-QA is the BrowseComp of CAD**. Low-hop rows and
high-hop rows are difficulty slices of one typed CAD ontology graph plus
deterministic query/verifier system.

This is a draft artifact, not a final paper. Keep quantitative claims tied to
generated release artifacts and leave placeholders when the current local run
is only a smoke or release-candidate probe.

## Files

- `cadqa_draft.md`: section-level draft for the graph-first CAD BrowseComp
  thesis, benchmark design, dataset construction, evaluation, training signal,
  limitations, and conclusion.
- `PAPER_RESULTS.md` in a run directory: generated smoke/release-candidate
  counts, release composition tables, baseline numbers, oracle key checks, and
  quarantine summary from `experiment_report.json`.

## Refresh Checklist

Before using text from this draft in a public manuscript:

1. Regenerate the graph-first release-candidate dataset and run validation.
2. Rebuild row statistics by hop slice, relation family, measurement scope, and
   split.
3. Rebuild verifier failure, quarantine, leakage, and dataset-card artifacts.
4. Rebuild baseline, grading, and model comparison reports.
5. Run `rtk uv run cadqa experiment paper-results --run runs/experiment_smoke`
   and use the generated `PAPER_RESULTS.md` for current smoke/release-candidate
   tables.
6. Replace all `[RESULT: ...]`, `[CITE: ...]`, and `[TABLE: ...]`
   placeholders.
7. Confirm limitations still match the current implementation status and
   relation coverage.
