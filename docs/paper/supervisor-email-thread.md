# Supervisor email thread
<!-- dont-say: allow-file: verbatim correspondence; quotes are not ours to edit -->

Email correspondence between Maksym Riabov and his academic supervisor,
SM Raza Abidi (PhD), about the CAD-QA master's project.

- **Supervisor:** SM Raza Abidi (PhD), Associate Faculty Lecturer, National
  College of Ireland (`Syed.Abidi@ncirl.ie`)
- **Student:** Maksym Riabov (`x25194372@student.ncirl.ie`)

## Provenance

Reconstructed from two Outlook PDF exports in `~/Downloads`:

- `Email - Maksym Riabov with syed abidi EARLIER - Outlook.pdf` (thread
  *Proposal from Maksym Riabov*, 23 September – 23 October 2026)
- `Email - Maksym Riabov syed abidi later - Outlook.pdf` (thread
  *Thesis update*, 11 – 14 November 2026)

The final exchange was not part of either PDF; it was pasted into the OpenCode
thread *Supervisor email thread on CadQuery dataset* on 15 November 2026 and is
reproduced in the last section.

Messages are ordered chronologically. Each message appears once, with the
quoted history of earlier messages removed. Outlook page headers, footers, and
URLs have been stripped; wording, typos, and signatures are otherwise verbatim.
Images and attachments are noted inline but not reproduced.

## Thread: Proposal from Maksym Riabov

### 23 September 2026, 10:56 — Maksym → Raza

> Hello Syed, you've asked for my proposal. It's already well-defined, just need
> to complete the LLM fine-tuning part... as well as debugging.
>
> Thank you,
> Maksym Riabov

### 5 October 2026, 22:41 — Raza → Maksym

> Dear Maksym,
>
> I have thoroughly checked your attached proposal and will discuss on
> Wednesday. Please share the (.docx) file and follow the same file throughout
> preparing your research report.
>
> Kind regards,
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

### 8 October 2026, 10:15 — Maksym → Raza

> Hello Syed, the docx you've asked for.
> I acknowledge it is to be reworked and from our presentations, I roughly
> understand where. I think if you wish to edit something, presently that would
> be for yourself first; I know where to make my edits.
>
> Thank you.
>
> (By the way: instead of asking me or anybody for docx, you could simply paste
> the PDF file into any agent and it would do the docx for you... so that you
> are not blocked by it... just saying.)

### 8 October 2026, 11:46 — Raza → Maksym

> Dear Maksym,
>
> Thank you for sending the DOCX version.
>
> Just to clarify, I am aware that a PDF can be converted into Word using
> various tools. That is not the reason I requested the Word file. I would like
> you to prepare and maintain the research report properly as an editable Word
> document from your side.
>
> The purpose is that I can review your actual working document and provide
> detailed feedback, suggestions, and corrections using Track Changes and
> comments. This is much more useful for the research-writing process than
> converting a final PDF into an editable format.
>
> Please therefore continue working on the report in the Word document and make
> your revisions there. I will review the updated version and use Track
> Changes/comments to provide my feedback where necessary.
>
> Also, please do not assume that you should wait for me to make the changes
> myself. The report is your work, so you should make the required revisions
> based on the feedback and guidance we have discussed. My role is to review,
> identify issues, and provide suggestions; you are responsible for implementing
> the changes in the report.
>
> Please also make sure that the Word document remains the main working version
> of your research report going forward.
>
> Thank you.
>
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

### 21 October 2026, 10:40 — Maksym → Raza

> Hello Syed, I left shortly after I joined on the meeting; I'm in a train and
> could barely hear the conversation so I'll go through materials myself.
>
> Status update: I'm working on re-specifying much of my code because I've found
> some critical issues in it. This includes both the dataset and the model.
>
> Also, I'm concerned with what can I do to actually prove that my dataset is
> useful; so proving that training on the dataset is useful. In practice, the
> usefulness is proven by training a LLM on it, then evaluating the model to
> show it. And I will, however only to a certain extent;
>
> I'm concerned that:
>
> 1. To reach an improvement I will need much more compute power than I would
>    like to spend (let's say, my budget is 100$),
> 2. If I make a mistake I'll need to re-spend my budget, which involves
>    training a number of ablations on models.
> 3. And that there is also lots and lots (1-2 full-time weeks?) of work to
>    re-do the paper since the previous iteration didn't work.
> 4. And that I'm fine-tuning the LLMs for the first time, and I'll nearly
>    definitely make mistakes, or something in the training will not work out.
> 5. (And that I also have two full-time jobs at the moment, and it compounds
>    the difficulty),
>
> I haven't updated the paper since the last update since I'm focused on
> practical part first. Maybe I would need to pick a smaller target.
>
> Probably nothing that you can act on so far.
>
> Thank you,
> Maksym Riabov

### 22 October 2026, 12:52 — Raza → Maksym

> Hi Maksym,
>
> Thank you for the update. I understand your concerns regarding the technical
> issues, computing budget, time constraints and the challenges of fine-tuning
> an LLM.
>
> I suggest reviewing the project scope and identifying a more manageable
> approach that allows you to demonstrate your dataset's usefulness through a
> feasible set of experiments. Please focus on resolving the critical issues
> first and propose a realistic plan for the remaining work.
>
> Furthermore, please focus your ablation experiments only on the components
> necessary to address your research question.
>
> Additionally, the Word file you sent me appears to be a copy of your proposal.
> Please remove the project plan from it and transfer your research report into
> the research report template provided. Send me the completed document
> (Introduction and Literature Review which you have already done) in Word
> (.docx) format for review and feedback.
>
> Kind regards,
>
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

### 22 October 2026, 16:59 — Maksym → Raza

> Hello Syed,
> I have validated my dataset today and it turns out that, while the research
> was relevant a few months ago when I started it, today, it's largely solved.
> The field went from sccess rates of 5-6% on some popular benchmark to 95% from
> January to September. I will need to change my approach.
> In my personal tests today, I found that open-source, released in October LLM
> models solve it at 93% success rates, so I will need to change my dataset.
>
> I have a question:
> here is a paper which I know would be a decent paper - something that I've
> done earlier but doesn't exist as ubiquitously in research literature today.
> It's a benchmark paper - testing whether models can solve a certain problem
> today; and if they can't, show that they can't (prove a direction for other
> researchers)
>
> Solving it requires synthetic data which I don't have; so I will stop at
> showing that models are incapable (or are capable to a degree)
>
> My question: would a benchmark paper be appropriate for a Master's thesis?
> Where we would not train a model, but only evaluate models of others on our
> data.
>
> Note: the file attached is only the proposal, so it just is kept in history of
> email conversation; I can't remove it.
>
> Thank you,
> Maksym

### 23 October 2026, 11:36 — Raza → Maksym

> Hi Maksym,
>
> Thank you for the update. A benchmark-based study could be suitable for a
> Master's thesis, provided it has a clear research gap, a well-defined research
> question, and a rigorous evaluation methodology. However, the revised approach
> and its expected contribution should be clearly established before proceeding.
>
> Regarding the document, I understand that the original proposal is retained in
> the email history. I am referring to the Word file you sent me. Please remove
> the Project Plan section from that Word file and transfer the remaining content
> (Introduction, Literature Review, Methodology sections etc. which you have
> already written) into the NCI research report template provided. Then send me
> the revised document in Word (.docx) format for review and feedback.
>
> Kind regards,
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

## Thread: Thesis update

### 11 November 2026, 07:23 — Maksym → Raza

> Hello Syed,
> Sorry for being silent for 2-3 weeks - I have developed and changed two topics
> for the final submission, so I was busy coding it.
>
> I'm attaching a work in progress draft - many sections are incomplete yet but
> it's a deep/complex topic so it takes a while to write.
>
> In short, I'm writing a thesis on a task on a job that I was given - finding of
> feasible and profitable products to launch, and forecasting their revenue, and
> costs such as manufacturing, shipment and Amazon fees. My thesis will be the
> first work to:
>
> - completely estimate features of a physical product worth improving
> - to attainable market share, revenue metrics
> - all associated costs
> - And crucially, make it cheap enough that we can repeat the scan over many
>   product categories to find the best product.
>
> I've spent around 900 hours on this project on the job so I'll write about it.
>
> What concerns me:
>
> 1. There is no real way to evaluate such a product. Backtests and other metrics
>    don't really apply here as we don't know e.g. how much we and other will
>    spend on ads or how good are the ads which leads to unknown qty of clients
>    acquired,
> 2. This project does not train a single machine learning model. We are using AI
>    to only extract some data and make some very closed and simple decisions
>    (deliberately).
>
> Will these two concerns not destroy my thesis?
>
> Thank you,
> Maksym

### 11 November 2026, 10:20 — Maksym → Raza

> Hello Syed,
> I'll just note that:
>
> 1. I'll refocus the thesis on strong evaluation and to be aligned to other
>    similar papers, as right now it's too lengthy and carries too much detail
>    which I can simply reference as from others,
> 2. And currently as it stands, there is no clear description of advantages of
>    my system over other systems. I.e. I haven't defined them myself yet; but
>    practically it's: repeatability, interpretability and falsifiability and
>    cost.
>
> Maybe the thesis is a bit premature for a review. I mostly sent it to you yet
> to notify of the change of topic and to show the direction of the system.

### 11 November 2026, 10:28 — Maksym → Raza

> To add to the previous message:
>
> 1. what to evaluate beyond:
>
>    - repeatability and consistency of recommendation,
>    - cost of researching one market,
>    - Sensitivity analysis
>    - (And describing the benefits of falsifiability & interpretability)
>
>    Is quite unclear to me as I haven't researched sufficiently yet, and it's
>    definitely not in the thesis. Further, point estimates of any models cannot
>    be evaluated end-to-end easily as we don't have the same datasets as Amazon
>    researchers have, for example.
>
> 2. If the evaluation will remain unclear, I may need to switch a topic again.
>
> Also, not sure if that matters, I'm aiming for 80-90% mark for the thesis.
>
> Thank you,
> Maksym

### 11 November 2026, 16:49 — Maksym → Raza

> Hello,
> Syed, after digging for more hours (since the morning) and going over 20-30
> papers I'm not that sure there is a research gap. While nobody has done the
> system, numerous papers exist on the topic although I personally didn't see
> the system embodied into software yet.
>
> Searched across relevant topics:
>
> - Decision-based design which is a study about how to exactly design products
>   given market constraints. It also answers my cost estimation, etc.
> - I didn't introduce any novelty in sentiment analysis,
> - I probably did a slightly unique system with regards to data acquisition, but
>   it iself is likely a weak study
> - The field of idea generation from aspects is pretty populated,
>
> I didn't find a open system and/or an open implementation of it, which may be
> the use-case. I also considered creating a benchmark on how well LLMs can
> suggest product ideas, and there are open datasets/papers evaluating idea
> generation... though I didn't find one doing deep research over marketplace and
> whether the resulting ideas still are coherent and cite the ground truth (as
> found by a more deterministic system) problems found.
>
> So practically:
> Practically I may need to switch topics; or rather go back to the topic I
> already had.
>
> Long story short the last week I've been designing a robot that can clean
> windows. Ths is it in simulation:
>
> *[image omitted]*
>
> I've already made a simulated environment and the approximate hardware design.
> Now only the policy remains.
> I'm afraid the 3d environment reconstruction and navigation in the open
> environment will be difficult. ... but I don't know whether a different thesis
> topic wouldn't take longer than to finish this.

### 11 November 2026, 17:53 — Raza → Maksym

> Dear Maksym,
>
> Thank you for the updates and for sharing your thoughts on both research
> directions. I appreciate the time you have spent reviewing the literature and
> exploring different possibilities.
>
> Having considered your emails, I would advise you to avoid changing your
> research topic repeatedly at this stage. Each new topic requires additional
> literature review, research planning, implementation, and evaluation, which
> can significantly affect your ability to complete the project within the
> available timeframe.
>
> Regarding your product research system, I understand your concerns about the
> research gap and evaluation. However, you do not necessarily need to develop
> an entirely new technology or a completely unprecedented system for an MSc
> research project. You need to identify a clear research problem, establish a
> justified contribution, and demonstrate its effectiveness through an
> appropriate and objective evaluation.
>
> The proposed advantages, such as repeatability, interpretability,
> falsifiability, and cost-effectiveness, could potentially form part of your
> contribution, provided that you define them clearly and demonstrate how they
> can be measured and compared against existing approaches.
>
> Regarding the window-cleaning robot, although it is an interesting idea, I am
> concerned that the scope may be too ambitious. Developing the simulated
> environment, hardware design, 3D reconstruction, navigation, and
> decision-making policy could introduce several technical challenges. You
> should carefully consider whether all these components can realistically be
> completed, implemented, and evaluated within your MSc project timeframe.
>
> I would also like to remind you that you have already developed and submitted
> your research proposal as part of Practicum Part 1, and it was approved.
> Therefore, before making any further changes to your research topic, you
> should discuss the proposed change with the person who reviewed and approved
> your original proposal. You should also bring this matter to the attention of
> your Programme Director to ensure that the appropriate academic approval
> process is followed. Please do not assume that you can change the approved
> topic without consultation.
>
> I would encourage you to keep the scope of your MSc Research Project
> manageable. An MSc project does not need to be as extensive or complex as a
> PhD research project or a commercial product. It is more important to have a
> clearly defined research question, achievable objectives, a working
> implementation, and a sound evaluation methodology. A focused and well-executed
> project is generally a better approach than an overly ambitious project that
> may be difficult to complete.
>
> I understand that you are aiming for a high mark (80–90%), but increasing the
> complexity of the project does not necessarily increase the likelihood of
> achieving that result. Strong research justification, methodological rigour,
> implementation quality, critical analysis, and a well-written report are much
> more important.
>
> My recommendation is that you do not proceed with another topic change until
> we have discussed and agreed on a realistic direction. Please focus on
> identifying which of your existing research directions can be completed most
> effectively within the remaining time, with a clear contribution and
> measurable evaluation criteria.
>
> Kind regards,
>
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

### 12 November 2026, 13:58 — Maksym → Raza

> Hello Syed, thank you for the answer,
> Sorry for adding you workload, it's just that earlier the unexpected happened -
> researchers started publishing in the same field that my approved thesis was
> and, essentially, my research project became obselete. While similar to my own
> research wasn't published, I practically could not contribute to the field; or
> at least the models could scale my dataset with ease (95% pass rate on an eval
> set of 100).
>
> Okay, so I have researched and found a genuinely good gap that isn't studied in
> literature - I'm attaching a 2-page proposal/overview of a paper that I
> suggest. It's a well-defined, not large in implementation LLM capability
> question on market analysis and data extraction (referencing a part of my
> product launch recommendation pipeline).
>
> It's self-descriptive, so you won't need additional research to understand it.
>
> Let me know what you think. Yes, I'll speak to the program coordinator if you
> confirm it's OK.
>
> Thank you!
> Maksym

### 12 November 2026, 22:54 — Raza → Maksym

> Dear Maksym,
>
> Thank you for explaining the situation and for sharing your revised proposal.
> I understand your concerns about the developments in the research field and how
> they may have affected the originality and potential contribution of your
> previously approved topic.
>
> It is good that you have now identified a more focused research question and
> have tried to define a manageable scope for the project.
>
> I will review the two-page proposal carefully, particularly the research gap,
> originality, objectives, proposed methodology, and evaluation strategy. We need
> to ensure that the proposed work makes a clear and defensible contribution and
> can realistically be completed within the MSc project timeframe.
>
> However, since your original proposal was already approved during Practicum
> Part 1, please do not consider the topic change approved at this stage. We will
> first need to assess the revised proposal and then follow the appropriate
> process, including consultation with the person who approved your original
> proposal and the Programme Coordinator.
>
> I will share my feedback once I have reviewed the document.
>
> Kind regards,
>
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

### 13 November 2026, 16:30 — Maksym → Raza

> Hello Syed,
> Thanks for the patience.
>
> I could stick with the topic I proposed initially, however I'm quite afraid
> that if somebody would do any sort of literature review - even listening to
> recent model announcements, they would say "but models already do it well?"
>
> If you could back me up, I could return to the original topic, but I'm just
> afraid that it won't work.
>
> Only you have the say here.
>
> Thank you,
> Maksym

### 14 November 2026, 15:39 — Raza → Maksym

> Dear Maksym,
>
> Thank you for being open about your concerns. I understand your hesitation,
> particularly given the rapid developments in AI models and their increasingly
> impressive capabilities.
>
> However, I would not dismiss your original CAD-QA topic simply because recent
> models appear to perform well on certain CAD-related tasks. Strong model
> performance does not necessarily mean that a research gap no longer exists.
>
> The important question is whether existing models have been systematically
> evaluated on complex procedural CAD programs, particularly in terms of geometry
> reasoning, correctness verification, and their ability to handle different
> levels of complexity.
>
> A well-designed benchmark can make a meaningful contribution even if some
> models achieve strong results. It can establish a systematic evaluation
> framework, identify the tasks models handle reliably, expose remaining
> limitations, and provide reproducible comparisons across models.
>
> That said, we should not proceed based on assumptions. We need to examine the
> recent literature and model capabilities carefully to establish whether the
> original research question remains sufficiently novel and whether the proposed
> benchmark offers a clear contribution.
>
> I am happy to support this direction if we can establish a defensible research
> gap, a manageable scope, and a practical evaluation strategy.
>
> Please do not feel that you need to change your topic simply because newer
> models have been announced. Equally, we should avoid committing to a topic
> without sufficient academic justification.
>
> We can agree on the direction and, if necessary, consult the Programme
> Coordinator regarding the formal approval process.
>
> Kind regards,
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

## Follow-up exchange

This exchange is not in either PDF; it was pasted into the OpenCode thread on
15 November 2026. The paste carried no per-message dates, so only the order is
known. Outlook mobile quoting artifacts ("Maksym Riabov", "Syed Abidi" between
messages) have been removed.

### 1. Raza → Maksym

> Dear Maksym,
>
> Thank you for the update. I think you should now focus on the CAD-QA topic
> rather than considering another change of direction.
>
> Regarding your question about how quickly we could change the topic, I need to
> be clear that, with the final submission deadline on 10 December, there is no
> longer sufficient time to change the research topic and develop an entirely new
> project. We need to concentrate on completing the current research within the
> remaining time.
>
> Regarding CAD-QA, I would suggest keeping the research focused and manageable.
> Rather than trying to develop an unnecessarily complex, full-scale project, you
> could consider producing a well-structured research review that critically
> examines geometry reasoning in procedural CAD programs.
>
> The report should provide:
>
> - A clear justification for the research problem and its significance.
> - A review of relevant existing literature and recent AI model capabilities.
> - A critical comparison of existing approaches and their limitations.
> - Identification of a specific research gap.
> - A clear explanation of how CAD-QA addresses that gap.
> - A manageable evaluation or experimental component, where appropriate, to
>   support your findings.
>
> The objective is to demonstrate a clear research contribution through sound
> academic reasoning, appropriate comparisons and critical analysis. You do not
> need to make the project unnecessarily complicated or attempt to build an
> entire large-scale system.
>
> Regarding the dataset, investigate the bugs you have identified and determine
> which issues are genuinely important for your research. Only address what is
> necessary to support your research objectives and evaluation. Avoid spending
> excessive time on dataset development if it does not directly contribute to
> the research question.
>
> Please remember that this is an MSc research report, not a requirement to
> develop a complete research product or a large-scale software system. The
> priority is to produce a focused, academically justified and well-evaluated
> report within the specified deadline.
>
> And regarding how to address me, you can call me Raza. That's absolutely fine.
>
> Kind regards,
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland

### 2. Maksym → Raza

> Hello Raza,
> Okay, confirmed then. I'll get at it starting today/tomorrow.
>
> I have an interview today at 9:00 so I won't be on the weekly meeting, but you
> know the progress so far.
>
> Thank you,
> Maksym

### 3. Raza → Maksym

> Dear Maksym,
>
> Thanks for confirming. That's fine, and best of luck with your interview today!
>
> Please focus on the CAD-QA research and keep the scope manageable, bearing in
> mind the 10 December submission deadline.
>
> We can discuss your progress at our next weekly meeting. In the meantime, please
> keep me updated on your progress.
>
> Kind regards,
> Raza.
>
> SM Raza Abidi (PhD)
> Associate Faculty Lecturer
> National College of Ireland
