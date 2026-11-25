# Research gap: multi-step CAD program comprehension

**Status:** draft for owner review, 2026-11-25. Companion to
[`CAD-QA_report.md`](CAD-QA_report.md) §2.5.

**What this document is.** The record of how the gap claim was derived, which
neighbouring gaps were considered and rejected, and what evidence would refute
the claim. It is not a second literature review: §2 of the report carries the
review, and this document holds only the gap argument, its evidence and its
falsification conditions.

---

## 1. The claim

The field now has instruments for three things: generation quality (does the
produced shape match the target), single-fact comprehension (answer one numeric
question about a given program), and end-to-end agentic authoring (can an agent
work a real CAD application for tens of rounds). It has no instrument for
multi-step, distractor-rich comprehension of a CAD program, where answering
requires resolving intermediate entities over the CAD graph and the gold answer
is derived by rule from the program rather than written or judged by an LLM model.

The claim is deliberately narrow enough to be checkable. A benchmark occupies
this gap only if it meets all seven conditions:

| # | Condition | Why it is part of the claim |
|---|---|---|
| C1 | Input is a CadQuery program plus a rendered prompt, with no access to CadQuery in the primary setting | Makes comprehension, not execution, the measured capability |
| C2 | The step range reaches at least three dependent task reasoning steps and extends to ten | Separates it from single-fact numeric lookup |
| C3 | Distractor-rich candidate selection; the answer is not identifiable from a variable name or operation order | Forces resolution, not pattern matching |
| C4 | Answers are not restricted to numbers: entity references, CadQuery selectors, coordinates, booleans, structured objects | A numeric-only contract collapses most CAD graph questions into arithmetic |
| C5 | The gold answer is derived by rule or execution, and grading is exact | Removes the LLM judge and the noisy reward check |
| C6 | A task reasoning step curriculum with labels, and ideally a critical path | Supports training and diagnosis, not only ranking |
| C7 | Immutable, family-safe train/validation/test split | Makes the number a result rather than a demo |

A benchmark that meets four or five of these occupies a different gap. That
distinction matters: most of the 2026 literature meets C1 and C5 while failing
C2, C3 and C4, which is exactly why the gap survives the apparent crowding.

---

## 2. How the claim was checked

**Window.** 25 August to 25 November 2026, with earlier work cited only as
baseline and labelled as such.

**Sources.** The arXiv API for date-bounded discovery (199 abstracts matching
CAD in the window); the Hugging Face daily-papers index for full-text reading
(`hf papers search` and `hf papers read`); Semantic Scholar and OpenAlex for
venue and citation cross-checks; venue accepted-paper lists for NeurIPS 2026,
SIGGRAPH Asia 2026, CAD'26 and the ECCV 2026 manufacturing workshop; and the
repository's own research notes in `docs/research/`.

**Catalogue.** 24 in-window benchmarks and datasets and 6 evaluation-protocol or
metric proposals were read closely enough to record task shape, reasoning depth,
answer format and grading, alongside a 40-row evidence table of geometry-native
work. The committed synthesis behind this document is
`docs/research/reports/2026-cad-ai-sota-scan.md`; the per-paper evidence notes are local
working material and are not committed.

**Found after the scan.** `brep-bench` (`brepbench.org`, GitHub repo created
29 October 2026) was surfaced after the automated sweep and is recorded here as
a late-window reference. Its case count, tolerances and grading rules are taken
from the site and README, retrieved 25 November 2026; it is a community
benchmark, not a peer-reviewed paper.

**Phrase checks, used only as a signal, never as proof.**

- A whole-corpus search for `"CAD question answering"`, `"CAD VQA"` and
  `"CAD understanding"` returns 1, 1 and 3 papers in the 2026, 2025 and 2024
  windows. The field does not describe its own work in QA terms.
- A secondary census (CDFAM, LLM-compiled and not peer-reviewed) counts 29
  dedicated CAD benchmarks since 2024, 16 of them released between April and
  September 2026, and 5 peer-reviewed.

**Limits of the check.** `export.arxiv.org` rate-limited the survey host
(HTTP 429) for part of the session, so the headline counts were captured once
and not re-confirmed. The `cs.LG` and `cs.CE` listings were not swept, so a
paper filed only there could be missed. The acronym "CAD" is a four-way
homonym: 31% of Semantic Scholar computer-science hits were medical
(coronary artery disease, computer-aided diagnosis, dentistry), and EDA plus
the USD/CAD currency pair add two more. Every count used here is either
term-matched on the mechanical sense or explicitly filtered.

---

## 3. Candidate gaps and verdicts

| Gap | Who is working on it | Evidence it is open | Verdict |
|---|---|---|---|
| **G1** Generation fidelity | The largest stream: roughly 63 text-to-CAD and program-synthesis papers in the window (3.2× the 2024 window), plus agentic reconstruction | Scores still move, but several splits are near ceiling and the metrics are contested | Crowded; not a gap |
| **G2** B-rep validity and representation | GraphCAD, UniBRep, canonical region graphs, equivariant encoders, brep-bench | Reported validity is 80–97% on incomparable splits, and kernel self-checks did not certify until brep-bench measured exported solids independently | Open, but a methods and metric gap; not an instrument this project can build |
| **G3** Editing and design history | 3DCodeEdit, HistCAD, AutoTimeline, CAD-Editor | 37% instruction-guided success; 29% industrial edit prediction | Real and measured, but needs kernel or serialized history; P1 extension, not P0 |
| **G4** Learned constraint solving | Nobody in the window | No paper proposes a learned or hybrid solver; systems reward or call the kernel's solver | The largest unclaimed prize, and out of scope for a dataset paper |
| **G5** Evaluation of evaluation | Nobody in the window | No survey or audit of CAD evaluation; no contamination audit; no held-out test server | Real meta-gap; would be a different thesis |
| **G6** Multi-step comprehension | BenchCAD (single-fact), MechReason (multi-image) | BenchCAD's own catalogue stops at one-step counterfactuals; phrase check returns one paper | **Chosen** |
| **G7** Downstream paperwork | Nobody in the window | No BOM extraction, cost accuracy, version diff, tolerance stack-up or CAD-to-CAD translation result | Empty, but not a reasoning instrument; future work |
| **G8** Transfer and conciseness | Sparse | Transfer results are rare and mostly generation-side | Not a gap in measurement; a property of whatever instrument exists |

Two of these deserve a sentence each because they shape the positioning.

**G2 looks like the strongest competition and is not.** The 2026 result that
matters is not that B-rep generation improved; it is that the validity check
underneath it is a kernel-acceptance test. A mathematics preprint of 13 November
defines a realization of a tolerant B-rep and shows that OpenCascade 8.0.1's
standard checks accept a sewn wedge with no realization and a thick pipe with
two non-homeomorphic realizations (DOI `10.5281/zenodo.24203268`). That
undercuts every "96% valid" claim, but it does not produce a comprehension
instrument, and building one would require a geometry kernel rather than a
generator.

One counter-movement arrived late in the window. **brep-bench**
(`brepbench.org`, first public 29 October 2026, code at
`github.com/bmander/brep-bench`) is an independent board of 300+ modelling cases
that grades the exported STEP file's solid rather than the kernel's own report:
volume, area, centroid and inertia within 1e-6 relative of a closed form, with a
refusal ranked above a wrong answer. It is the closest thing to a validity
oracle for B-rep kernels, and it shows the measurement problem is solvable. It
does not close G2 for this project: it grades hand-written kernel runners, not
LLM-generated B-reps, and it has no task, no gold answer over a program, and no
comprehension construct.

**G3 is the best argument that G6 matters.** Instruction-guided editing fails at
roughly one in three, industrial edit prediction at 29%, and GUI work at 17.5%.
All three failure analyses land on the same cause: the LLM model cannot identify
which entity the instruction refers to, or cannot recover the constraint that
makes the edit legal. That is comprehension. The editing benchmarks measure the
symptom; a comprehension instrument can measure the cause at a fraction of the
compute, which is why G6 is the better P0 and G3 is the natural extension.

---

## 4. The chosen gap in detail

### 4.1 BenchCAD does not close it

BenchCAD is the nearest neighbour and the reason the original CA2 claim had to
change. It provides 17,900 execution-verified CadQuery programs, four tasks, and
a no-kernel numeric Code QA task with deterministic grading. That is the base
task shape, and it is done well.

It does not close the gap for a structural reason, not a scale reason. The Code
QA catalogue is single-fact extraction with light arithmetic: counts, extrema,
ratios of two named dimensions, and one-step counterfactuals. No item requires
resolving an intermediate entity whose identity must be discovered before the
final step, chaining two dependent resolutions, selecting among distractors, or
disambiguating a CadQuery selector. BenchCAD 2.0 and 2.1 moved the benchmark to
reconstruction, assemblies and PCB wiring and added no comprehension task, so
the depth did not arrive with the newer line either.

Adding more Code QA items would not close it. Depth is a property of the
dependency structure, not of the item count: a million single-fact questions are
still single-fact questions.

### 4.2 Agentic benchmarks do not close it

CAD Bench V3, CADWorld, EngiWorld and RealCADBench measure end-to-end
artifacts. They are the strongest evidence that the field's capability is
uneven — 61.03 overall with 39.69 on create-and-edit, 17.5% against an 87.0%
expert reference, 44.3 out of 100 with 3.6% cross-application success, and
face-level IoU of 0.112 to 0.217 on industrial intents — but a failure in any of
them is confounded. The LLM model may have failed at the interface, the tool
policy, the plan, the geometry, or the comprehension of an existing part. None
isolates the comprehension step, and none can be used as a training target at
the compute of a small LLM model because each needs a kernel, a GUI or a long agent loop.

The useful reading is the reverse of competition: these benchmarks show that the
capability gap is real and expensive, while leaving its cause unmeasured.

### 4.3 Visual and question-answering benchmarks do not close it

DesignQA evaluates engineering documentation and standards compliance; SiT-Bench
and Real-3DQA test spatial reasoning from textual scene descriptions; MechReason
is the nearest multi-hop neighbour at 62.89% for the best LLM model but takes
multiple images as input. CivilCADBench reads drawing sets well above 90% on
clean single sheets. None takes a program as input, and none grades a CadQuery
entity or selector, so none measures the construct in C1 and C4.

### 4.4 The metric critique makes the gap more urgent, not less

Three 2026 results say the field's dominant scores are weaker than they look:

- DrawScore formalises IoU, Chamfer distance and F-score as one integral and
  shows a local error of size *s* is weighted as *s* to the power *(k+q)*, so a
  0.9 mm bolt-hole shift can leave F-score at 100%.
- RealCAD shows DeepCAD's local normalisation lets an LLM model earn parameter
  accuracy from value priors rather than perception.
- The tolerant-B-rep result shows "valid" often means the kernel accepted the
  file.

If geometric similarity is blind to the errors engineers care about, then an
instrument that grades exact answers against a rule-derived gold is not a
weaker proxy for shape quality; it measures a different and more decision-
relevant property. That is the argument for C4 and C5, and it is stronger after
the 2026 critiques than before them.

---

### 4.5 What changed since CA2

The gap statement descends directly from the Research Niche section of
`CA2_Riabov_final.tex` (winter/spring 2026), which named three problems: shallow
reasoning, no measure of the shortest required reasoning path, and clean
one-step tasks that avoid real noise. All three survive the 2026 scan unchanged.
Two things changed:

- The claim "there isn't an open dataset which could reliably measure ...
  CAD code question answering beyond simple questions" is retired. BenchCAD Code
  QA measures exactly that, and it is good. The claim narrows to depth.
- A fourth differentiator is added: a non-numeric answer contract. In 2026 the
  field's dominant scores were shown to be blind to local geometry error, so an
  exact answer over entity references and CadQuery selectors is now a
  methodological position, not only a task-design preference.

The contribution list in CA2 was dataset plus construction method, conciseness
and critical-path supervision, and a labelled curriculum. That list stands; only
the "first dataset" framing of the first item changes.

---

## 5. What would refute the claim

The claim is falsifiable, and each condition below is checkable before
submission.

1. **BenchCAD extends Code QA.** If a future BenchCAD release adds three or more
   dependent steps, distractors and non-numeric answers, the gap narrows to the
   curriculum and transfer claims. Check the 2.x line and the leaderboard before
   submission.
2. **A new benchmark already does this.** The search terms are fixed: CAD
   question answering, CAD comprehension, multi-hop CAD, program comprehension,
   CAD reasoning. Check arXiv, the ECCV manufacturing workshop, NeurIPS 2026 and
   CAD'26.
3. **The instrument cannot reach the depth it claims.** If the synthesis pilot
   cannot produce at least two real candidates at six to ten steps, or manual
   review rejects the chains, the release falls back to one to five steps and the
   "up to ten" claim is withdrawn, as the dataset requirements already state.
4. **Base LLM models are at ceiling.** If a current cost-effective LLM model
   scores near ceiling on the immutable release without training, the gap is not
   live for that class of LLM model and the instrument has no headroom to train into.
5. **The no-kernel setting measures nothing beyond reading.** The step-9
   diagnostic partly addresses this: nine number tasks carry the gold value as a
   literal, and the kernel arm scored 7/9 on them versus 46/51 (90.2%) on tasks
   without a literal, so literal matching does not explain the result. A larger
   literal audit on the release is still required.

If any of 1, 3 or 4 holds, the honest outcome is a narrower paper, not a
rewritten claim.

---

## 6. Risks to the claim

- **Moving target.** BenchCAD 2.x could add comprehension; a 2027 benchmark
  could occupy the space. The claim is therefore dated: "as of 25 November 2026,
  no reviewed instrument meets all seven conditions".
- **Saturation.** Generation moved fast in 2026. Comprehension has not, but that
  is an observation about one quarter, not a law.
- **Contamination.** Public CADEvolve programs overlap the BenchCAD base, so a
  transfer result on BenchCAD `qa_code` requires a family-safe audit.
- **"The no-kernel setting is artificial."** The objection is fair and already
  recorded in the dataset requirements. The answer is cost (a kernel call is a
  round trip, a sandbox and context), the skill being measured (writing a
  CadQuery selector is useful work in its own right), and the closed CAD
  environments where the same reasoning applies. Kernel access remains an upper
  bound, not a claim that kernels are unavailable.
- **"This is multi-hop QA applied to CAD."** Partly true, and the multi-hop
  literature is the right framing. The difference is that every step is grounded
  in geometry the program builds, the gold comes from execution, and the answers
  are CAD entities and CadQuery selectors rather than spans of text.
- **Small cells.** The step-9 diagnostic is one LLM model, one sample per task,
  and 60 tasks. It locates the problem; it does not estimate the release.

---

## 7. What the gap implies for the instrument

| Condition | Instrument decision |
|---|---|
| C1 no kernel | Primary LLM harness mode has no access to CadQuery; NumPy allowed; kernel-assisted mode is an upper bound |
| C2 three to ten steps | Target mix 1:5%, 2:10%, 3:30%, 4:25%, 5:15%, 6:7%, 7:4%, 8:2%, 9:1%, 10:1%; six to ten gated by a release gate |
| C3 distractors | Clue chains with necessary clues, distinct wrong answers, and an answer candidate set that shrinks by construction |
| C4 non-numeric answers | Seven answer formats, including entity references and CadQuery selectors; numeric-only is treated as a failure of coverage |
| C5 rule-derived gold | AST plus kernel-backed extraction; exact structured-answer match; one scorer, no LLM judge |
| C6 curriculum | Task reasoning step labels, warmup subset, critical-path evidence |
| C7 immutable split | 70/15/15 target, family-safe, immutable split manifest, test never trained on |

The dataset requirement IDs that implement the table are R-1 to R-19 in
[`../dataset/requirements/PRD.md`](../dataset/requirements/PRD.md).

---

## 8. Claims that survive, and claims to avoid

**Survive, subject to the checks in §5.**

- As of 25 November 2026, no reviewed instrument combines multi-step
  comprehension, distractor-rich selection over the CAD graph, non-numeric
  answers, a rule-derived exact gold, a no-kernel setting and a reasoning-step
  curriculum. BenchCAD occupies the base task shape; CAD-QA occupies the depth.
- The graph-derived generator is a method contribution independent of the
  headline result: it turns a program corpus into verified tasks without human
  annotation.
- The step-9 diagnostic locates the failure in entity selection rather than
  syntax, which is a finding about the capability, not only about the
  instrument.

**Avoid.**

- "No open dataset exists." BenchCAD Code QA exists.
- "State of the art." Not a claim this instrument can make about itself.
- "CAD question answering is unstudied." The window has one paper, not zero.
- "Kernels are unavailable." The setting is a deliberate constraint.
- "Generalises across CAD." One corpus, one generator, one family-safe split.

---

## 9. Open questions for the owner

1. Is "depth above BenchCAD" sufficient for the contribution, or does the paper
   need the transfer result before the gap claim is credible?
2. Does citing the 2026 metric critique strengthen the motivation or invite a
   comparison the instrument cannot win?
3. If the six-to-ten release gate fails, does the gap statement stay at "up to
   five steps" in the abstract, or is the abstract rewritten around the
   curriculum?
4. Where does this document belong in the submission — appendix, internal note,
   or omitted in favour of the report's §2.5?
