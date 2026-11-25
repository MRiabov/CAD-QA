# Literature review: from CAD reconstruction to CAD program comprehension

**Status:** draft for the thesis, 2026-11-25. Writing input, not manuscript copy.
Anchored on work available by **August 2026**; the four items marked † are
concurrent additions and are not load-bearing for the argument. 25 references.

---

## 1. Three constructs, usually conflated

Work on language models and CAD is normally organised by modality: text,
images, point clouds, meshes. That organisation hides the more useful
distinction, which is by **construct**. Three different things are being
measured, and they fail for different reasons:

- **Generation and reconstruction** — produce a CAD model or program from a
  specification or a signal (text, an image, a point cloud, a drawing). These
  are the same construct with different input modalities.
- **Editing** — change an existing model or program under an instruction, which
  requires locating the affected entity and keeping the result valid.
- **Comprehension** — answer a question about an existing program or model by
  reasoning about the shape it builds.

Generation and reconstruction are evaluated by comparing the produced shape
with a reference, and editing by whether the edit succeeds. Comprehension is
evaluated by checking an answer against the program's geometry. The first two
have improved quickly; comprehension has barely been measured, and the
measurement that exists is shallow. That asymmetry is the subject of this
review.

## 2. Generation and reconstruction

DeepCAD established the representation that most later work still uses: a CAD
CAD model as a sequence of sketch-and-extrude operations, learned generatively
(Wu, Xiao and Zheng, 2021). Text2CAD turned that representation into a
text-conditioned task with beginner-to-expert prompts (Khan et al., 2024), and
CAD-Recode moved in the opposite direction, recovering CadQuery code from a
point cloud (Rukhovich et al., 2025). Later systems widened the input and
tightened the training: cadrille adds multi-modal reconstruction with
reinforcement learning (Kolodiazhnyi et al., 2026), CADENA decomposes reverse
engineering into steps (Kabisov et al., 2026), and CADBench supplies a
multimodal benchmark for program generation (Doris et al., 2026).

This line has produced two things the rest of the field depends on. First, a
usable program representation: CadQuery or a command sequence is now a normal
output format, which makes programs themselves an object of study. Second,
large supervised corpora: the same systems that generate also manufacture
training pairs at a scale human annotation cannot match.

What it has not produced is evidence about comprehension. Every one of these
systems is scored on the shape or the program it emits. An LLM model that generates
a plausible bracket has demonstrated that it can produce a program, not that it
can read one. The two abilities are separable, and the second is what an
assistant needs when a user asks which face is largest, how far a vertex sits
from a datum, or what an operation removed. The field has been optimising the
first and assuming the second.

## 3. Editing

Editing is the construct that makes the distinction concrete, because it
requires generation and comprehension at once. CAD-Editor formulates text-based
editing as locate-then-infill: find the region the instruction refers to, then
generate a replacement (Yuan et al., 2025). HistCAD evaluates editability over
180,495 parametric histories and reports instruction-guided edit success of
52.4% in academic settings and 29.0% in industrial ones (Dong, X. et al.,
2026). Its failure analysis is the important part: edits fail because
the LLM model cannot recover the history or the constraint that makes the change legal,
not because it cannot emit code.

That is comprehension of an existing CAD model, measured through an edit. An
assistant that cannot identify the face, edge or feature an instruction refers
to cannot edit reliably, whatever its generation quality. Editing is therefore
the strongest practical argument for measuring comprehension directly: the
editing benchmark measures the symptom, and a comprehension instrument can
measure the cause at a fraction of the compute.

## 4. Corpora that make comprehension checkable

The substrate for comprehension is the procedural corpus. DeepCAD's command
sequences supplied the first large one (Wu, Xiao and Zheng, 2021), and
CADEvolve made it both more realistic and more usable by generating CadQuery
programs through program evolution and publishing program families alongside
predicted mesh families (Elistratov et al., 2026). The family structure matters
beyond convenience: it gives a group-safe split unit, so the same design cannot
appear in both training and test.

Programs are the right substrate for a verifiable instrument for one reason:
the gold answer can be computed by executing the program and reading the built
shape. No human writes the label, and no LLM model judges it. That property is what
makes a large, exact, automatically graded dataset possible at all.

The substrate also has costs that a review should state. Program quality
varies, some programs fail to execute, and some build degenerate shapes; a
robust instrument records those as rejected rows rather than exceptions.
Public corpora also overlap: the same program families appear in the benchmarks
used to test generation, so any transfer evaluation has to exclude them by
family.

## 5. What comprehension benchmarks actually measure

The closest dedicated instrument is QueryCAD, which answers measurement
questions about CAD models by having an LLM model write Python against a CAD-shaped
API, with part selection grounded by a segmentation network (Kienle et al.,
2024). On its 111 questions GPT-4o answered 44 correctly; of the 67 non-correct
cases, 52 were segmentation errors and only one was a reasoning error. That
decomposition is the important result: the bottleneck was perception, not
reasoning about the program. It also shows how narrow the task is — the
questions ask for measurements of parts, not for relationships across a build.

GeoGramBench moves closer to program reasoning: 500 problems that translate
procedural drawing code into spatial answers, organised into three levels of
geometric complexity (Luo et al., 2025). Its taxonomy is complexity, not
reasoning depth, so it cannot say how performance changes as a chain of
dependent resolutions gets longer.

BenchCAD is the reference point for programmatic CAD and the benchmark this
project must position against (Zhang, H. et al., 2026). It provides 17,900
execution-verified CadQuery programs across 106 industrial families and four
tasks. Code QA is the comprehension task: a CadQuery program and a numeric
question, answered with no access to CadQuery and graded by symmetric ratio
accuracy. Its best total is 0.838, but its Spatial Reasoning axis is 0.537 to
0.731 against a 0.42 blind baseline — the one public comprehension number that
is not saturated. The catalogue, however, is shallow: counts, extrema, ratios
of two named dimensions, and one-step counterfactuals. No item requires
resolving an intermediate entity before the final step, chaining two dependent
resolutions, selecting among distractors, or disambiguating a
CadQuery selector. BenchCAD 2.0 and 2.1 moved the benchmark to reconstruction,
assemblies and PCB wiring and added no comprehension task.

CADTestBench is the closest test-verified neighbour: it grades generated CAD
programs against executable tests rather than visual similarity, and its tasks
require at most two or three steps (Mallis et al., 2026). It evaluates
generation, not comprehension of a given program, but it is the right
methodological precedent — executable checks instead of a judge.

Two adjacent families complete the picture without closing the gap. DesignQA
evaluates understanding of engineering documentation (Doris et al., 2025), and
SiT-Bench tests spatial reasoning from textual scene descriptions (Guo et al.,
2026); neither takes a program as input. MechReason is the nearest multi-hop
neighbour, with multi-image mechanical questions and a best score of 62.89% for
the strongest model (Wang et al., 2026), but its input is images rather than
code. †Three concurrent benchmarks measure end-to-end artefact production —
CADWorld's 200 GUI tasks (17.5% against an 87.0% expert reference), RealCADBench's
industrial intents, and Parametric CAD Bench v3's 100 authoring tasks (61.03
mean reward, 39.69 on create-and-edit) (Dong et al., 2026; Li, G. et al., 2026;
Chen, M. et al., 2026). They establish that the capability gap is real and
expensive, but a failure in any of them could come from the interface, the tool
policy, the plan, or the geometry, so none isolates comprehension.

## 6. Verifiable reasoning and small LLM models

The methodological literature supplies the design constraints. Chain-of-thought
prompting established that making intermediate steps explicit improves
multi-step reasoning (Wei et al., 2022), and hard, automatically graded
benchmarks such as BrowseComp showed that a verifiable task can drive large
gains without human annotation (Wei et al., 2025). Reinforcement learning with
verifiable rewards turned that into a training recipe at scale (DeepSeek-AI,
2025).

Two findings from 2026 discipline the design. First, SFT and RL do different
things: SFT broadens the reasoning the LLM model can reach, RL sharpens it onto
high-probability paths, which is why the two-phase SFT-then-RL order works and
why RL from a cold policy can collapse (Matsutani et al., 2026). Second, data
must match the training phase: SFT is for skills the LLM model cannot yet reach, RL
for skills it can partially reach, and hard data during RL produces all-zero
reward and no signal (He et al., 2026). Together they imply that a benchmark
intended as a training target must be labelled by difficulty, not just scored.

That is the connection the CAD literature has not made. BenchCAD labels
capability axes L1–L4, not reasoning depth. GeoGramBench labels geometric
complexity. Neither provides a per-task count of dependent reasoning steps, so
neither can support a curriculum or a calibrated RL-eligible range.

## 7. The gap

Read together, the literature establishes four things. Program representations
and large procedural corpora exist. Generation and reconstruction are measured
well and are improving. Comprehension is measured, but only at the level of
single-fact numeric lookup. And the methodology for verifiable, difficulty-
calibrated training is mature in adjacent fields.

What is missing is the intersection: a benchmark that asks multi-step,
distractor-rich questions over the full CAD graph — operations, solid states,
faces, edges, vertices, CadQuery profiles, CadQuery workplanes and regions —
with a rule-derived gold answer, a non-numeric answer contract, no access to
CadQuery, and a reasoning-step curriculum. BenchCAD occupies the base task
shape and does it well; this project occupies the depth above it. The depth is
where editing, agentic work and industrial use fail, which is why it is worth
measuring rather than assuming.

## Table 1. Closest prior work

| Work | Construct | Input → output | Grading | Max reasoning steps | Curriculum |
|---|---|---|---|---|---|
| DeepCAD (2021) | generation | command sequence → shape | reconstruction error | — | no |
| Text2CAD (2024) | generation | text → CAD sequence | similarity / validity | — | no |
| CAD-Recode (2025) | reconstruction | point cloud → CadQuery | code + geometry | — | no |
| cadrille (2026) | reconstruction | image / points → code | geometry | — | no |
| CADBench (2026) | generation benchmark | image / text → program | geometric metrics | — | no |
| QueryCAD (2024) | comprehension | question + CAD model → measurement | answer accuracy | 1–2 | no |
| GeoGramBench (2025) | program reasoning | drawing code → spatial answer | answer accuracy | 1–3 (complexity tiers) | no |
| CADTestBench (2026) | generation, test-graded | text → program | executable tests | 2–3 | no |
| CAD-Editor (2025) | editing | instruction + program → edited program | success / validity | — | no |
| HistCAD (2026) | editing benchmark | history + instruction → edited history | edit success | — | no |
| BenchCAD Code QA (2026) | comprehension | program + numeric question → number | ratio accuracy | 1–2 | no |
| **CAD-QA (this project)** | comprehension | program + question → structured answer | exact match | **1–10** | step curriculum + critical path |

## Scope note

The review stops at August 2026 deliberately. The field's output roughly
doubled in the following quarter, but most of that growth is variation on the
themes above: more text-to-CAD systems, more agent harnesses, more benchmarks.
None of it changes the four established facts in §7, and building the argument
on the newest preprints would make it age badly. The † items are included
because they are the first independent measurements of end-to-end CAD work, and
they corroborate the gap rather than define it.

## References

- Chen, M., Xia, Y. and Mao, H. (2026) 'Parametric CAD Bench v3: Evaluating Agentic Parametric CAD Authoring from Text and Engineering Drawings', arXiv preprint arXiv:2611.02659.
- DeepSeek-AI (2025) 'DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning', *Nature*, 645, pp. 633–638. doi: 10.1038/s41586-025-09422-z.
- Dong, X., Li, C., Zheng, P., Han, C., Jing, J., Shen, H., Song, Y. and Yang, Z. (2026) 'HistCAD: Constraint-Aware Parametric CAD Histories for Evaluating Editability', arXiv preprint arXiv:2602.19171.
- Dong, Z., Liu, Y., Ma, Z., Zhan, Q., Kong, D., Li, G. and Li, K. (2026) 'CADWorld: Computer-Use Benchmark for Long-Horizon Computer-Aided Design', arXiv preprint arXiv:2609.16251.
- Doris, A.C., Sony, J.T., Nehme, G., Syla, E., Heyrani Nobari, A. and Ahmed, F. (2026) 'CADBench: A Multimodal Benchmark for AI-Assisted CAD Program Generation', arXiv preprint arXiv:2605.10873.
- Doris, A.C., Grandi, D., Tomich, R., Alam, M.F., Ataei, M., Cheong, H. and Ahmed, F. (2025) 'DesignQA: A Multimodal Benchmark for Evaluating Large Language Models' Understanding of Engineering Documentation', *Journal of Computing and Information Science in Engineering*, 25(2), Art. no. 021009. doi: 10.1115/1.4067333.
- Elistratov, M., Barannikov, M., Ivanov, G., Khrulkov, V., Konushin, A., Kuznetsov, A. and Zhemchuzhnikov, D. (2026) 'CADEvolve: Creating Realistic CAD via Program Evolution', arXiv preprint arXiv:2602.16317.
- Guo, Z., Yang, Z., Li, Y., Zhang, X., Gao, W., Wang, J., Li, C., Liu, X. and Jian, P. (2026) 'Can LLMs See Without Pixels? Benchmarking Spatial Intelligence from Textual Descriptions', arXiv preprint arXiv:2601.03590.
- He, C., Zhang, R., Wang, Z. and Li, X. (2026) 'Learning What to Learn: Stage-Specific Data Sets for SFT-then-RL in Small Language Model Reasoning', arXiv preprint arXiv:2606.04466. <!-- dont-say: allow: bibliographic title -->
- Kabisov, S., Savrasov, G., Elistratov, M., Rodriguez, A., Ignatiev, D., Gavrilov, N., Uzdenov, R., Boyko, A.I., Pasechnik, I., Konushin, A. and Kuznetsov, A. (2026) 'CADENA: Stepwise CAD Reverse Engineering', arXiv preprint arXiv:2608.00799.
- Khan, M.S., Sinha, S., Sheikh, T.U., Stricker, D., Ali, S.A. and Afzal, M.Z. (2024) 'Text2CAD: Generating Sequential CAD Designs from Beginner-to-Expert Level Text Prompts', *Advances in Neural Information Processing Systems*, 37.
- Kienle, C., Alt, B., Katic, D., Jäkel, R. and Peters, J. (2024) 'QueryCAD: Grounded Question Answering for CAD Models', arXiv preprint arXiv:2409.08704.
- Kolodiazhnyi, M., Tarasov, D., Zhemchuzhnikov, D., Nikulin, A., Zisman, I., Vorontsova, A., Konushin, A., Kurenkov, V. and Rukhovich, D. (2026) 'cadrille: Multi-modal CAD Reconstruction with Reinforcement Learning', *International Conference on Learning Representations (ICLR)*.
- Li, G., Huang, Z., Yu, H., Long, Y., Liu, H., Cai, L., Hong, Q., Li, Z., Wang, W., Zhong, X. and Wang, Y. (2026) 'RealCADBench: Benchmarking Parametric CAD Modeling from Industrial Design Intents', arXiv preprint arXiv:2609.03773.
- Luo, S., Zhu, Z., Yuan, Y., Yang, Y., Shan, L. and Wu, Y. (2025) 'GeoGramBench: Benchmarking the Geometric Program Reasoning in Modern LLMs', arXiv preprint arXiv:2505.17653.
- Mallis, D., Wang, M., Karadeniz, A.S., Ricci, E., Kacem, A. and Aouada, D. (2026) 'Text-to-CAD Evaluation with CADTests', arXiv preprint arXiv:2605.07807.
- Matsutani, K., Takashiro, S., Minegishi, G., Kojima, T., Iwasawa, Y. and Matsuo, Y. (2026) 'RL Squeezes, SFT Expands: A Comparative Study of Reasoning LLMs', *International Conference on Learning Representations (ICLR)*.
- Rukhovich, D., Dupont, E., Mallis, D., Cherenkova, K., Kacem, A. and Aouada, D. (2025) 'CAD-Recode: Reverse Engineering CAD Code From Point Clouds', *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)*. doi: 10.1109/ICCV51701.2025.00914.
- Wang, T., An, K., Du, C., Yang, Z., Zhu, Y., Yang, X., Zhu, H., Wang, Z., Qian, F., Yang, Y. and Ren, Q. (2026) 'MechReason: Benchmarking Multi-Image Multi-Hop Reasoning in Mechanical Engineering', arXiv preprint arXiv:2609.16012.
- Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q. and Zhou, D. (2022) 'Chain-of-Thought Prompting Elicits Reasoning in Large Language Models', *Advances in Neural Information Processing Systems*, 35, pp. 24824–24837.
- Wei, J., Sun, Z., Papay, S., McKinney, S., Han, J., Fulford, I., Chung, H.W., Passos, A.T., Fedus, W. and Glaese, A. (2025) 'BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents', arXiv preprint arXiv:2504.12516.
- Wu, R., Xiao, C. and Zheng, C. (2021) 'DeepCAD: A Deep Generative Network for Computer-Aided Design Models', *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)*, pp. 6772–6782. doi: 10.1109/ICCV48922.2021.00670.
- Yuan, Y., Sun, S., Liu, Q. and Bian, J. (2025) 'CAD-Editor: A Locate-then-Infill Framework with Automated Training Data Synthesis for Text-Based CAD Editing', arXiv preprint arXiv:2502.03997.
- Zhang, H., Liu, K., Chen, M., Li, L., Yang, S., Peng, C. and Chen, H. (2026) 'BenchCAD: A Comprehensive, Industry-Standard Benchmark for Programmatic CAD', arXiv preprint arXiv:2605.10865.
- Zhang, L., Le, B., Akhtar, N., Lam, S.-K. and Ngo, T. (2026) 'Large Language Models for Computer-Aided Design: A Survey', *ACM Computing Surveys*, 58(9), pp. 1–39. doi: 10.1145/3787499.
