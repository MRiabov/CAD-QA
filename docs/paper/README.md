# CAD-QA paper (CA2 report)

The written manuscript for CAD-QA: *CAD-QA: A Benchmark Verifying Geometry
Reasoning over Complex Procedural CAD Programs* (Maksym Riabov, Research in
Computing, National College of Ireland; Continuous Assessment 2). It is the
proposal that the code, dataset, and fine-tuning work implement.

## Files

- `CA2_Riabov_final.tex` — **authoritative manuscript.** LaTeX manuscript; the
  version submitted to Moodle.
- `CA2_Riabov_final.md` — Markdown mirror, kept in **parity** with the `.tex`
  (same prose, same Harvard reference list; only section-number prefixes and
  quote glyphs differ). Edit the `.tex` first, then bring the `.md` back into
  parity, or regenerate the `.md` with pandoc.
- `CAD-QA_report.md` — working scaffold for the MSc Research Project Report,
  following the NCI report template's section order (title page, abstract,
  introduction, related work, methodology, design, implementation, evaluation,
  conclusion, references). Sections are bullet-point outline notes inside HTML
  comments, not prose, and the header records the 4,000–6,000 word target
  (6,000 maximum).
- `CA2Img-GanttChart-mermaid.png` — the project-plan Gantt figure embedded by
  the manuscript.
- `supervisor-email-thread.md` — the supervisor correspondence (Raza Abidi) on
  the project's direction, from the September–October 2026 proposal thread
  through the November 2026 scope decisions.

## Parity check

Compare the two by normalizing to plain text:

```sh
pandoc CA2_Riabov_final.tex -f latex -t plain --wrap=none > /tmp/paper-tex.txt
pandoc CA2_Riabov_final.md  -f gfm   -t plain --wrap=none > /tmp/paper-md.txt
diff <(grep -v '^$' /tmp/paper-tex.txt) <(grep -v '^$' /tmp/paper-md.txt)
```

Expected: differences limited to the title/author/abstract block (LaTeX
metadata is not rendered to plain text), section-number prefixes, smart vs
straight quotes, and `~` vs `∼`.

## Word version for reviewers

The reviewers' copy is generated from the `.tex`:

```sh
pandoc CA2_Riabov_final.tex -f latex -t docx -o CA2_Riabov_final.docx --resource-path=.
```

## Provenance

Authoritative copy lives with the submission at
`~/Documents/College/semester_2/Practicum/ca2/`. This directory is the copy
referenced by the repository.
