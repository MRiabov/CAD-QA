# BenchCAD: programmatic CAD benchmark and its Code QA overlap (2026)

**Status:** external study note, not our result. Added 2026-10-09 to record the BenchCAD task
suite, its frontier scores, its overlap with CAD-QA, and the timing consequence.

## Citation

Zhang, H., Liu, K., Chen, M., Li, L., Yang, S., Peng, C. and Chen, H. (2026) 'BenchCAD: A
Comprehensive, Industry-Standard Benchmark for Programmatic CAD', arXiv preprint
arXiv:2605.10865. Available at: `arxiv.org/abs/2605.10865`. Website and leaderboard:
`benchcad.com`; harness: `github.com/BenchCAD/BenchCAD-main`; data:
`huggingface.co/datasets/BenchCAD/BenchCAD`. BenchCAD 2.0 preview (no paper yet):
`benchcad.com/benchcad-2`, `github.com/BenchCAD-org/benchcad-2`.

- Reference: `prior-art.md`, reference [33].
- Provenance: `[preprint]`. Leaderboard figures are benchmark-author or provider data; figures
  marked provider-reported are **not re-graded** and use a different split, and are labelled so
  below.

## What it is

A four-task benchmark built on **17,900 execution-verified CadQuery programs** across 106
industrial part families and 47 ISO/DIN/EN/ASME/IEC standard codes. Grading is
execution-grounded and deterministic — no LLM judge. BenchCAD has two lines: **1.0** (the four
tasks below, with the arXiv paper) and **2.0** (reconstruction-only, 2026-09; see Findings).

| Task | Input → output | Metric |
|---|---|---|
| Vision2Code | four renders → CadQuery program | voxel IoU vs ground-truth STEP |
| Code Edit | instruction + program → edited program | headroom-normalised IoU |
| Vision QA | renders + numeric question → number | symmetric ratio accuracy |
| **Code QA** | **CadQuery program + numeric question → number** | **symmetric ratio accuracy** |

- **Code QA is the CAD-QA-adjacent task.** 2,400 numeric questions (dimensions, counts,
  ratios) over 200 parts; the same 2,400 questions are asked in an image mode and a code mode.
  Questions come from a per-family question bank hand-authored by a domain author (6–12
  question templates per family), parameterised by each family's exposed parameters.
- Grading: symmetric ratio accuracy `min(pred, gt) / max(pred, gt)` for dimensions and ratios;
  exact match for integer, count, and boolean. Ratio accuracy is partial credit; CAD-QA's
  structured-answer scoring is exact match.
- Capability hierarchy: L1 recognition → L4 spatial/code reasoning.

## Findings

### Code QA scores (frontier, code mode)

| Axis | Best | Notes |
|---|---|---|
| CadQuery code recognition | 0.914 (Gemini 3.1 Pro) | near ceiling |
| CAD operation understanding | 0.805 | high |
| Industrial parametric abstraction | 0.876 | high |
| **Spatial Reasoning** | **0.731 (GPT-5.3)** | Gemini 0.537, Opus 0.595–0.632; **blind baseline 0.42** |
| Total | 0.838 (Gemini 3.1 Pro) | Opus 4.7 thinking 0.829, GPT-5.3 0.823 |

- The comprehension task is **not saturated on spatial reasoning** (0.54–0.73 against a 0.42
  blind baseline), unlike the recognition/abstraction axes (0.79–0.91).
- The authors name the image−code gap the **Holistic Spatial and Detailing Deficit**.

### Question catalog and reasoning depth (checked 2026-10-09)

Each record is one part (columns: `stem`, `family`, `gt_code`, `composite_png`, `standard`,
`qa`, `qa_level`, `qa_id`). The `qa` column is a JSON object holding the question, the numeric
answer, a value class (ratio / count / dimension / boolean), a provenance tag, and the
capability level; the bank has about 12 questions per part (200 parts × 12 = 2,400). The
observed catalog:

- **Counts:** hole, chamfer, fillet, extrusion, union, and coil operations; distinct sketch-frame
  calls.
- **Lookup / extremum:** largest chamfer; largest or smallest hole, cylinder, or fillet argument;
  primary extrusion axis; base frame; 1-indexed line of the first chamfer, hole, fillet, or
  revolve operation; family and symmetry booleans.
- **Ratios** of two named dimensions (outer/shaft, flange/thread, plate height/width, tip/root,
  and similar) — roughly 60% of the bank.
- **Comparisons:** smallest cylinder radius against half the largest; any chamfer against the
  largest hole radius; maximum extrusion depth against a fixed value.
- **Aggregates:** the sum of all extrusion / cutBlind depth values.
- **One-step counterfactuals (the hardest, tagged L4):** "if you delete the last hole
  operation, how many holes remain?"; "if all `.union()` operations were removed, how many
  separate solid bodies would remain?"

**Assessment:** every item is single-fact extraction from the program with light arithmetic; the
hardest are one-step counterfactuals over a single operation category. No item requires
resolving an intermediate entity whose identity must be discovered before the final step,
chaining two or more dependent resolutions, selecting among distractor candidates, or
disambiguating a CadQuery selector. The published L1–L4 labels are a capability hierarchy
(recognition → operation understanding → parametric abstraction → synthesis), not a count of
Reasoning hops. BenchCAD Code QA therefore occupies the *numeric QA over CadQuery programs
with no access to CadQuery, deterministic grading* base task, but not the multi-hop, CAD ontology resolution space CAD-QA
targets.

### Vision2Code scores and the saturation trajectory

- **Re-graded, no tools (the public, comparable series):** execution rate up to 96.5% (Opus
  4.7), but voxel IoU-score (`voxel IoU × exec%`) only ~0.27–0.29 (Gemini 3.1 Pro 0.289). Code
  runs; geometry is wrong.
- **Provider-reported, no tools** (random 1,000-file subset, not re-graded): newest models'
  plain voxel IoU 0.49–0.75 — Sonnet 5.5 0.747, Opus 5.5 0.730, Haiku 5.5 0.670, Fable 5.1
  0.606, Opus 5 0.497.
- **Provider-reported, with tools** (agentic sandbox, iterate before submitting): 0.87–0.96 —
  Sonnet 5.5 0.963, Opus 5.5 0.962, GPT-6 Astra 0.959, Fable 5.1 0.926, Opus 5 0.899, Haiku
  5.5 0.870.
- **Metric caveat.** The 0.49–0.96 figures use a different metric (plain voxel IoU) and a
  different split from the re-graded series and are provider self-reported. They must not be
  plotted as one comparable curve with the re-graded 0.27–0.29.
- Code Edit: best headroom-normalised accuracy 0.865 (GPT-5.3); no-change baseline 0.0.

### BenchCAD 2.0 (reconstruction-only, 2026-09)

BenchCAD 2.0 (`github.com/BenchCAD-org/benchcad-2`, "2.0-preview", repo created 2026-09-11) is
six **reconstruction** tasks (T1–T6), each scored by execution with no LLM judge: T1 drawing →
part; T2 supplied parts + assembly drawing + BOM → assembly; T3 four renders → part (orientation
pinned); T4 mechanism renders → parts + assembly; T5 five drawings + sixteen STEPs → parts +
assembly; T6 PCB renders → terminal-net graph. Headlines: `part_v1 = 0.5·iou_term + 0.3·surf_f1
+ 0.2·pix_fg`, `asm_v1` (per-part leave-one-out voxel IoU gain), and `ecad_v2`. The LLM model
works in a sandbox for 30 rounds per case, with `export`, `export_part`, `use_part`,
`submit_assembly`, and `crop`; a 300-family held-out set stays private.

**Why it does not change the overlap.** 2.0 is generation/reconstruction only — it adds
assemblies and PCB wiring, not comprehension. It carries no numeric-QA or multi-hop task, so the
closest BenchCAD task to CAD-QA remains 1.0 Code QA. It matters as context: the benchmark's
center of gravity is reconstruction and assemblies, which leaves multi-hop comprehension as the
unoccupied corner.

### Comparison with CAD-QA

| Dimension | CAD-QA | BenchCAD 1.0 Code QA | BenchCAD 2.0 (T1–T6) |
|---|---|---|---|
| Purpose | multi-hop reasoning over given CadQuery programs | numeric comprehension of CadQuery programs | reconstruction of parts, assemblies, and PCB wiring |
| Input | CadQuery program + rule-rendered prompt | CadQuery program + numeric question | part/assembly drawings, renders, supplied STEP + BOM |
| Output | short structured answer (entity references, CadQuery selectors, coordinates, numbers, integers, booleans, candidate labels, JSON) | one number (JSON array of numbers) | CadQuery solid / assembly / terminal-net graph |
| Reasoning depth | Reasoning hops 0→10, distractors, candidate resolution | single-fact lookup + light arithmetic; hardest is a one-step counterfactual | generation/assembly planning with agentic iteration |
| Grading | exact structured-answer match | symmetric ratio accuracy (partial credit) | voxel IoU, surface F1, netlist — execution-grounded |
| Construction | automated graph-derived (AST → CAD ontology → Gold query program) | hand-authored 6–12 templates per family | parametric generator per design family |
| Scale | 1,445 now; 10,000 target | 2,400 questions over 200 parts | ~100 public / ~100 private cases; 150 public families + 300 held-out |
| Curriculum / conciseness | Reasoning hop curriculum + critical-path labels | capability axes L1–L4 only | none |
| Tools | `no_tools` / `numpy` / `cadquery` LLM harness modes | answer-only | agentic sandbox, 30 rounds per case |
| Corpus | procedural CAD programs + synthetic | industrial standards, 106 families | real engineering drawings, assemblies, PCBs |

The base task shape of BenchCAD 1.0 Code QA — read a CadQuery program, answer a geometry
question, grade deterministically with no LLM judge and no kernel — is the same as CAD-QA.
CAD-QA differs in reasoning depth, answer surface, and automated construction; BenchCAD 2.0 is
a different construct entirely (reconstruction).

## Saturation and timing

Generation-task scores rose fast through 2026: re-graded Vision2Code voxel IoU is still ~0.27,
but provider-reported voxel IoU with no access to CadQuery is now ~0.49–0.75 and agentic is ~0.87–0.96. The
BenchCAD generation framing is therefore approaching saturation. The **comprehension** framing
is not: BenchCAD's own Code QA Spatial Reasoning axis is 0.537–0.731 against a 0.42 blind
baseline, so a comprehension gap remains open. CAD-QA's premise is comprehension, not
generation; the window is narrower than the original proposal assumed and must be measured
against the frozen hard slice before any gap claim stands.

## Why it matters for CAD-QA

- **Positioning.** The paper's claim that no open dataset reliably measures CAD program
  comprehension with no access to CadQuery is now false: BenchCAD Code QA already does
  no-access-to-CadQuery, exact/deterministic, code-conditioned numeric QA. The paper cites BenchCAD only as a
  generate-and-edit benchmark and must cite the Code QA/Vision QA tasks. The defensible
  contribution shifts to multi-hop, distractor-rich, non-numeric-typed reasoning over the
  CAD ontology with automated graph-derived synthesis and a hop curriculum / critical path.
- **Transfer target.** `qa_code` is text-in and unsaturated on spatial reasoning, so it is a
  usable independent transfer benchmark; Vision2Code/`code_gen` is image-in (not usable by a
  text-only base LLM model) and near-saturated, so it is a poor transfer target.
- **Contamination.** BenchCAD `code_gen` is a prospective `domain_3d` priming set
  (`fine-tuning-data-plan.md` §2.6). Training on BenchCAD programs and then evaluating transfer
  on BenchCAD Code QA leaks (shared 17,900-program / 200-part base); exclude BenchCAD items
  from training or keep the transfer evaluation disjoint.
- **Comparable baseline.** Report the CAD-QA hard slice and BenchCAD Code QA side by side, and
  run the current frontier models on the frozen CAD-QA hard slice to establish whether the
  multi-hop gap is still live.

## Landscape — works citing BenchCAD and adjacent benchmarks (2026-10-09)

BenchCAD is already cited by a set of 2026 works, which confirms it as a reference point and
surfaces adjacent benchmarks (Semantic Scholar, 2026-10-09):

| Work | arXiv | What it is | Modality |
|---|---|---|---|
| CADFather | 2610.09127 | agentic reconstruction coordinating tools; evaluates on CADENA-Bench, CADBench, BenchCAD | mesh |
| CADWorld | 2609.16251 | long-horizon FreeCAD computer-use, 200 tasks, executable checks; best agent 17.5% vs 87% expert | GUI |
| RealCADBench | 2609.03773 | parametric CAD from industrial design intents; executability + IoU + visual-semantic | text/image |
| MechReason | 2609.16012 | multi-image multi-hop reasoning in mechanical engineering; best 62.89% | multi-image |
| P3D-Bench | 2606.11152 | parametric 3D generation and structural reasoning from a text/visual spec | text/visual |
| DepthBenchCAD | 2609.15122 | how audit depth changes conclusions for CAD parameter edits | — |
| 3DHarnessBench | 2609.06535 | agentic 3D-to-code (Blender Python) from frontier vision-language agents | vision |
| VisCAD | 2609.03811 | multimodal industrial CAD foundation suite | multimodal |
| CAD-CodeVerify | ICLR | self-verification of VLMs on CAD code generation | vision + code |

**Additional text-in candidates** (not in the citation pull above, but credible for the transfer
end/defect axis):

- **Text2CAD-Bench** (arXiv:2605.18430): 600 human-curated text→CadQuery examples in four tiers
  L1–L4; Chamfer distance, Invalidity Rate, IoU; sandboxed execution with retries. Best fit for the
  end/defect axis.
- **Text-to-CadQuery** (arXiv:2505.06507): 170K text–CadQuery pairs; Chamfer distance, Invalid Rate,
  exact match.
- **CAD-Editor** (ICML 2025, arXiv:2502.03997): locate-then-infill text-based CAD editing.
- **CAD-Coder** (NeurIPS 2025, arXiv:2505.19713): text-to-CAD with chain-of-thought + geometric
  reward; reconstruction IoU ~92% on legacy DeepCAD splits (saturated).
- **Zero-to-CAD** (arXiv:2604.24479) and **3DCodeBench** (arXiv:2606.01057): agentic program
  synthesis with executability and geometric metrics.

**Implication.** BenchCAD `qa_code` remains the best-fit means target; `Text2CAD-Bench` is the best
text-in end/defect candidate. `MechReason` and `CADWorld` are credible and corroborate that
multi-hop / agentic CAD is hard, but their modality (multi-image, GUI) is out of reach for a
text-only base LLM model — use them as context, not targets (`plans/oct-8/evaluation-plan.md` §5.1).

## Related

- `2025-geogrambench-program-to-geometry.md`
- `2026-noregeo-non-reasoning-geometry-benchmark.md`
- `2024-querycad-cad-question-answering.md`
