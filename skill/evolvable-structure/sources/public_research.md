# Public and scientific work on "adaptable structure" (for the adaptable-structure skill)

Verification key: V-record = bibliographic record confirmed in Undermind (title, authors, year, DOI); V-abs = abstract or page read; V-sec = confirmed through search results that quote the abstract or page (not the primary page, which blocked fetching). Ideal numbers refer to SKILL.md (1 One core at the edge, 2 Named swappable parts, 3 Changeable defaults, 4 One place per setting, 5 Shared container/personal content, 6 Generic capability/specific from outside, 7 Readable definitions, 8 Experiment = production path, 9 Comparable alternatives, 10 Surface does not grow, 11 Own by adapting, 12 One method/emergent categories, 13 Stable interface/announced changes).

## 1. Designing for change and modularity

### Parnas, 1972, "On the criteria to be used in decomposing systems into modules" (Communications of the ACM 15(12))
Link: https://doi.org/10.1145/361598.361623 (V-record; Undermind had no abstract and the ACM page blocked fetching, so the content below is from my background knowledge of this very well known paper, not from a page I read today.)
What it finds: Compares two ways of splitting the same small system: by processing steps, or by hiding each design decision likely to change inside one module. The second split lets a change touch one module. The lasting rule is to draw module borders around what will change.
Relation: Supports 2 and 13 (callers see a stable interface, the changeable decision is hidden), and sharpens 1: the thing at the edge should be chosen by predicted change, not by "everything could vary". Fits the skill's advice to ask what the next three iterations will change.
Evidence: Classic argued case study (one example), enormously influential but not an experiment.

### Baldwin and Clark, 2002, "The Option Value of Modularity in Design" (HBS Working Paper 02-078; summarises their 2000 book Design Rules, Vol. 1, MIT Press)
Link: https://ssrn.com/abstract=312404 (V-sec via search results quoting the abstract; SSRN blocked fetching). Book: https://mitpress.mit.edu/9780262291859/design-rules-volume-1/ (V-sec)
What it finds: Splits a design into hidden modules (free to change) and visible design rules (fixed). Because hidden modules can be swapped for better versions, each gives an "option", valued by its technical potential, the cost of running independent experiments, and its visibility. The sum of module option values must exceed the cost of building the modular architecture.
Relation: Supports the Purpose (progress across iterations) and 2, 8, 9 directly, and gives Joshua's purpose a formal economic form. Qualifies it: option value only pays when the module's potential is uncertain AND experiments are cheap; a part that never gets replaced earns nothing, which backs the skill's "generality that does not ease the next iteration is overhead".
Evidence: Theoretical model with industry examples (computers). Not a controlled test.

### MacCormack, Rusnak and Baldwin, 2006, "Exploring the structure of complex software designs: an empirical study of open source and proprietary code" (Management Science 52(7))
Link: https://doi.org/10.1287/mnsc.1060.0552 (V-abs, Undermind abstract)
What it finds: Uses design structure matrices to measure dependency between software elements in Linux and Mozilla. Early Mozilla was much less modular than Linux, and a deliberate redesign made it markedly more modular than both. The authors call it exploratory.
Relation: Supports that modular structure is a managed choice, not an accident (1, 2, 13), and that "many small named parts" can be measured (DSM) rather than only asserted. Does not show that more modular code has fewer defects or ships faster; it measures structure only.
Evidence: Empirical, two products, exploratory.

## 2. Variability and configuration

### Berger, She, Lotufo, Wasowski, Czarnecki, 2013, "A study of variability models and languages in the systems software domain" (IEEE TSE 39(12))
Link: https://doi.org/10.1109/TSE.2013.34 (V-record; abstract confirmed via search results)
What it finds: Analyses 128 real variability models from 12 open-source projects (Linux Kconfig, eCos CDL). Real models differ from academic feature models in size, constructs and needs, and the authors say they challenge assumptions made in academic papers.
Relation: Supports 1, 6 and 7 (one core, case differences as readable definitions, here at industrial scale). Sharpens: real definition languages grow large and need their own tooling, which is the "flexibility makes checking harder" difficulty.
Evidence: Empirical corpus study.

### Xu et al., 2015, "Hey, you have given me too many knobs!" (ESEC/FSE 2015)
Link: https://doi.org/10.1145/2786805.2786852 (V-record; figures from V-sec search result summarising the paper)
What it finds: In commercial storage and open-source systems, only about 6 to 17 percent of configuration parameters are set by most users, up to 54 percent are seldom set, and 17 to 49 percent of user configuration issues concern finding or setting parameters.
Relation: Challenges 3 and 10 where they are read as "make everything settable". It strongly supports 10 ("the surface does not grow with the options") and the skill's difficulty that a default acting for people matters. A setting nobody sets is cost with no benefit.
Evidence: Empirical, large user-data study.

### Sayagh, Kerzazi, Adams, Petrillo, 2020, "Software configuration engineering in practice: interviews, survey, and systematic literature review" (IEEE TSE 46(6))
Link: https://doi.org/10.1109/TSE.2018.2867847 (V-abs, Undermind abstract)
What it finds: Interviews with 14 experts and a survey of 229 Java developers, plus a literature review. Options are usually created without planning, add complexity, are hard to understand and debug, and developers avoid touching options in mature systems.
Relation: Challenges 1, 4 and 7 as ideals without a cost: configuration failures are among the most common failures, and "configuration instead of code" moves the complexity rather than removing it. Supports the skill's "flexibility makes checking harder", and suggests adding "configuration needs the same tests and review as code" to 13.
Evidence: Mixed-method empirical study (interview, survey, review).

### Krüger and Berger, 2020, "An empirical analysis of the costs of clone- and platform-oriented software reuse" (ESEC/FSE 2020)
Link: no DOI retrieved (V-abs: Undermind search record and abstract, ESEC/FSE 2020, 28th ACM Joint Meeting, 7 Nov 2020; look up by title before citing in print)
What it finds: Compares clone-and-own with a configurable platform using 26 interviews and a 57-paper review. Platforms cost more up front but lower later reuse cost and give better code quality, yet change propagation can cost more in a platform, and in practice the two strategies blur.
Relation: Directly tests the skill's "copies drift" versus "one core". Supports 1, 4 and the drift difficulty, but qualifies it: the core pays back only with enough reuse, and has a real up-front cost. It supports the "usually two real cases" threshold as a judgment, not a measured number.
Evidence: Empirical, interviews plus literature review.

## 3. Evolvable architecture

### Ford, Parsons, Kua, 2017, "Building Evolutionary Architectures" (O'Reilly)
Link: https://www.oreilly.com/library/view/building-evolutionary-architectures/9781491986356/ch02.html (V-sec)
What it finds: An architecture should support guided incremental change, with "fitness functions" (tests, metrics, monitoring) giving an objective check that important characteristics do not erode.
Relation: Supports 9 and 13 (measure, pin the contract with tests) and the "Keep improving" step: it gives Joshua's "weights and defaults come from measurement" an architectural name. Sharpens 13: tests that pin the contract are fitness functions and should run continuously.
Evidence: Practitioner book. No controlled evidence in it.

### Qiu, Li, Su, 2013, "An empirical analysis of the co-evolution of schema and code in database applications" (ESEC/FSE 2013)
Link: https://doi.org/10.1145/2491411.2491431 (V-sec via search result; not fetched)
What it finds: Across ten open-source database applications and 160K revisions, about 80 percent of schema changes hit 20 to 30 percent of tables, and nearly 40 percent of tables never changed.
Relation: Qualifies Ideal 1/2 on where to place flexibility: change is concentrated, so most of a data model is stable and only some parts earn adaptable treatment. Supports "ask what the next iterations will change" and warns against making everything uniformly flexible.
Evidence: Empirical, observational.

## 4. Adaptable vs adaptive, end-user customization

### Fischer, 2001, "User modeling in human-computer interaction" (User Modeling and User-Adapted Interaction 11(1))
Link: https://link.springer.com/article/10.1023/A:1011145532042 (V-sec)
What it finds: Contrasts adaptive systems (the system changes itself, little user effort) with adaptable ones (the user changes the system, so fit and control are better). Frames the design problem as writing software for millions of users at design time that must work as if made for one person known only at use time.
Relation: Supports 3, 11 and the difficulty "People set the AI's direction and permissions", and names Joshua's problem precisely (design time versus use time). Sharpens: adaptable and adaptive are a trade-off, and Fischer argues for combining them with system support, which matches "defaults people can change".
Evidence: Review and design argument.

### Mackay, 1991, "Triggers and barriers to customizing software" (CHI '91)
Link: https://doi.org/10.1145/108844.108867 (V-abs)
What it finds: In a four-month study of 51 Unix users, most people did not customize much, because time spent customizing is time not working; customization happened at particular triggers.
Relation: Challenges 3 and 11 as assumptions: "people can change defaults" does not mean they will, so defaults must be good and the ideal's check should be "can" not "do". Supports the calendar-sync lesson: defaults act at scale because few people change them.
Evidence: Empirical field study (51 users), dated.

### Findlater and McGrenere, 2004, "A comparison of static, adaptive, and adaptable menus" (CHI 2004)
Link: https://doi.org/10.1145/985692.985704 (V-record; findings via V-sec)
What it finds: In a 27-person lab study, the adaptive (system-changing) menu was slower than the static one, the adaptable (user-controlled) one was faster than the adaptive under some conditions, and most users preferred the adaptable one.
Relation: Supports 3 and 11 (user-controlled beats system-controlled adaptation on preference and some speed). Qualification: small lab study of menus, and the adaptable condition was not faster than static, so customization costs effort.
Evidence: Controlled experiment, small sample.

## 5. A standard core with personalization in education and care

### Capp, 2017, "The effectiveness of universal design for learning: a meta-analysis of literature between 2013 and 2016" (International Journal of Inclusive Education 21(8))
Link: https://doi.org/10.1080/13603116.2017.1325074 (V-sec; ERIC record EJ1147229: https://eric.ed.gov/?id=EJ1147229)
What it finds: Meta-analysis of 18 pre/post UDL studies: UDL seems to improve the learning process for all students, but the effect on actual outcomes is not demonstrated.
Relation: Supports 5 and 12 in spirit (one framework, many ways in) but only weakly: the evidence is on process, not results. This is a case where the ideal "reached when" line (show which option is better, on real results) is not met by the field itself. Note it is a meta-analysis, not a "meta-review" (the brief said meta-review).
Evidence: Small meta-analysis, outcome evidence thin.

### Pashler, McDaniel, Rohrer, Bjork, 2008, "Learning styles: concepts and evidence" (Psychological Science in the Public Interest 9(3))
Link: https://doi.org/10.1111/j.1539-6053.2009.01038.x (V-sec)
What it finds: Found virtually no evidence that matching instruction to a diagnosed learner "style" improves results, and said resources are better spent on practices with strong evidence. Allows that people do differ in specific aptitudes.
Relation: Challenges 5 and 12 where personalization rests on a plausible but untested personal parameter. Supports "a general claim is a hypothesis until it beats a baseline" and 9: personal variation needs measured benefit, and a parameter can be real in form and empty in effect.
Evidence: Systematic review by expert panel. Later work (a 2024 matching-hypothesis meta-analysis exists, Clinton-Lisell and Litzinger) was not read.

### Kulik and Fletcher, 2016, "Effectiveness of intelligent tutoring systems: a meta-analytic review" (Review of Educational Research 86(1))
Link: https://doi.org/10.3102/0034654315581420 (V-sec)
What it finds: Across 50 controlled evaluations, the median effect was about 0.66 SD over conventional instruction, but depended heavily on whether tests were locally built or standardized (a secondary source gives 0.13 for standardized; not verified).
Relation: Supports 9: adaptive personalization can beat a baseline when measured, and also shows the measurement choice (aligned or standardized test) changes the answer, a caution for "measured value" ideals.
Evidence: Meta-analysis of controlled studies.

## 6. Cybernetics, requisite variety, complex systems

### Ashby, 1956, "An Introduction to Cybernetics" (Chapman and Hall)
Link: https://doi.org/10.5962/bhl.title.5851 (V-sec: found in a bibliography, content from search summaries; book not read)
What it finds: Only variety in the regulator can absorb variety in the thing regulated: a controller needs at least as many distinct responses as the disturbances it must handle.
Relation: Sharpens 1 and 12 as a limit, not a support: one core serving many cases needs enough variation at the edge to match the cases, so "a parameter" must be rich enough. It also warns against 10 taken too far, because a surface that does not grow while cases do will under-fit ("too general fails like too specific"). Gives a principled reason for Joshua's "right level" difficulty.
Evidence: Foundational theory, mathematical, not tested on software design.

### Simon, 1962, "The architecture of complexity" (Proceedings of the American Philosophical Society 106(6))
Link: https://www.jstor.org/stable/985254 (V-sec; full text hosted at https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/ArchitectureOfComplexity.HSimon1962.pdf)
What it finds: Argues complex systems that evolve are hierarchic, built from stable sub-assemblies with weak links between them (near decomposability), and that such systems evolve much faster than flat ones.
Relation: Supports the Purpose and 2: stable named parts are what let a system improve step by step. Gives a general (not only software) reason why "many small named parts" speed progress.
Evidence: Theoretical essay with a parable and examples.

## 7. Research method flexibility

### Lucas and Szatrowski, 2014, "Qualitative comparative analysis in critical perspective" (Sociological Methodology 44(1))
Link: https://doi.org/10.1177/0081175014532763 (V-record; abstract via V-sec)
What it finds: Simulating data with a known causal story, they report QCA recovered the true story in only 3 of 70 solutions, and argue QCA's epistemology has key problems. (A reply by Ragin and others is in the same symposium; I did not read it.)
Relation: Challenges 12 ("one method, categories emerging from each case") and the skill's "flexibility has a cost" with real force: a flexible case-oriented method is only as good as its demonstrated ability to find truth, which here was disputed. Supports the skill's "a general claim is a hypothesis until it beats a baseline" and favors adding simulation with known answers as a check on any flexible method.
Evidence: Simulation study with critics, contested. QCA's own defenders (Ragin 1987, 2008) were not verified, so this is one side only.

## 8. Counter-evidence on over-generalizing, size and structure

### Metz, 2016, "The wrong abstraction" (blog, sandimetz.com, 20 January 2016)
Link: https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction (V-abs)
What it finds: Merging duplicate code too early makes a shared helper that later cases do not fit, so people bend it with parameters and branches until it is worse than duplication, and sunk-cost thinking keeps it alive. The fix is to inline it back and look again.
Relation: Challenges 1, 4 and 6 directly, and supports the skill's "usually two real cases" and "copies drift" in tension: duplication is cheaper than a wrong abstraction. Notes a way for the skill to say "undo a failed generalization" (the skill parks alternatives, which is close).
Evidence: Practitioner essay, no data.

### Fowler, 2015, "Yagni" (martinfowler.com bliki, 26 May 2015)
Link: https://martinfowler.com/bliki/Yagni.html (V-abs)
What it finds: Building for a predicted future need costs in build, delay, carrying complexity, and repair, even if the prediction is right. Yagni depends on code that stays easy to change, and does not excuse neglecting design.
Relation: Challenges the speculative reading of the Purpose ("make the next three iterations parameters") and supports the skill's own difficulty "nothing speculative". Also sharpens: making code easy to change is not speculative, building for a guessed feature is.
Evidence: Practitioner essay, partly citing a product-metrics statistic I did not verify.

### Brooks, 1975 (anniversary ed. 1995), "The Mythical Man-Month", ch. 5 "The second-system effect" (Addison-Wesley)
Link: https://en.wikipedia.org/wiki/The_Mythical_Man-Month (V-sec, secondary summaries only; book not read)
What it finds: A designer's second system tends to over-design, loading in the frills held back on the first. Brooks describes an instruction set where only about half was regularly used.
Relation: Challenges a "generic core" ambition that follows a first success: it is exactly the stage where Joshua's generalizing is most tempting. Supports requiring evidence of real cases.
Evidence: Practitioner experience, a few historical cases.

### Wagner and Deissenboeck, 2008, "Abstractness, specificity, and complexity in software design" (arXiv)
Link: Undermind record for the paper, ArXiv 2008-05-11 (V-abs; I did not fetch the arXiv page)
What it finds: Separates two kinds of abstraction that affect specificity and complexity differently, arguing the trade-offs are not well understood.
Relation: Sharpens "too general fails like too specific": abstraction is not one dial. Weak support only.
Evidence: Conceptual paper.

### Koru, Zhang, El Emam, Liu, 2009, "An investigation into the functional form of the size-defect relationship for software modules" (IEEE TSE 35(2))
Link: https://doi.org/10.1109/TSE.2008.90 (V-record; findings via V-sec)
What it finds: In Mozilla, Cn3d, JBoss and Eclipse, size mattered for defect proneness but in a logarithmic form: smaller classes were proportionally more defect-prone per line than larger ones.
Relation: Challenges the intuition that "many tiny parts" are automatically safer. Defects per line may be higher in small units, though fewer lines per unit may still cost less per unit of change. It does not show big files are better, and says nothing on comprehension by an AI.
Evidence: Empirical, four large OO products. One reading dispute exists (one source reads it as lower density in larger modules), so cite the "logarithmic, smaller proportionally worse" form.

### Hatton, 1997, "Reexamining the fault density-component size connection" (IEEE Software 14(2))
Link: https://doi.org/10.1109/52.582978 (V-abs)
What it finds: Found medium-sized components were proportionately more reliable than small or large ones, against the conventional belief that smaller components have fewer faults.
Relation: Challenges "smaller is better" in a different direction from Koru: there may be a middle size. Together with Koru, no clean support for either "few huge files" or "tiny parts".
Evidence: Empirical, older data.

### Fenton and Ohlsson, 2000, "Quantitative analysis of faults and failures in a complex software system" (IEEE TSE 26(8))
Link: https://doi.org/10.1109/32.879815 (V-abs)
What it finds: In two releases of a commercial system, few modules held most faults, but the authors found no evidence for earlier claims linking module size to fault density, and complexity metrics predicted poorly.
Relation: Qualifies anything claiming a size threshold: defects concentrate in a few modules, so what matters is which parts change and break. Supports measuring Joshua's own repos instead of assuming.
Evidence: Empirical, one company, two releases.

### El Emam, Benlarbi, Goel, Rai, 2001, "The confounding effect of class size on the validity of object-oriented metrics" (IEEE TSE 27(7))
Link: https://doi.org/10.1109/32.935855 (V-abs)
What it finds: Many OO structure metrics appear to predict faults only because they track class size; once size is controlled the association disappears (the abstract states a strong confounding effect).
Relation: Challenges using structure metrics (cohesion, coupling) as proof of quality, and so challenges any "reached when" test that relies on a structural score alone. Support for 9: compare on real outcomes.
Evidence: Empirical, one C++ framework.

### Hu, Wang, Peng, Gao, Lo, 2026, "Evaluating LLM-based 0-to-1 software generation in end-to-end CLI tool scenarios" (arXiv 2604.06742)
Link: https://arxiv.org/abs/2604.06742 (V-abs)
What it finds: A 94-repository benchmark; the best of seven LLMs passed only 43.8 percent, and agents tended to produce monolithic code.
Relation: Supports Joshua's observation that AI code tends toward few huge files (his "small parts found by name" guidance in coding.md). It does not prove monolithic code is worse, only that it differs from the human reference.
Evidence: Benchmark study, preprint (2026, v2 July 2026), not peer reviewed as far as I could see.

### Zhu, Tsantalis, Rigby, 2026, "AI-generated smells: an analysis of code and architecture in LLM and agent-driven development" (arXiv 2605.02741)
Link: https://arxiv.org/abs/2605.02741 (V-abs)
What it finds: Reports a characteristic "machine signature" of defects, bulkier and more tightly coupled code from more capable models, and a "volume-quality inverse law"; concludes agents need explicit architectural foresight.
Relation: Supports 2, 13 and the skill's "interface and one example call first, small parts found by name" for AI-written code. Qualifies it: other search-result text describes a "modular mirage" (many files without real cohesion), which I did not read in the paper, so many files is not the same as good structure.
Evidence: Preprint, empirical, 2026.

### Mao, Zhao, Tang, Wang, Zhang, 2026, "A large-scale comprehensive measurement of AI-generated code in real-world repositories" (arXiv 2603.27130)
Link: https://arxiv.org/abs/2603.27130 (V-abs)
What it finds: Compares AI-assisted and human code in real repositories and reports that code-level differences are rather small, smaller than lab studies suggested.
Relation: Challenges treating "AI code is huge-file code" as a settled fact; the effect may be strong in from-scratch generation and weak in real mixed repositories. (A search summary gave function and per-file counts, which I did not verify.)
Evidence: Large-scale repository measurement, preprint.

## What this changes in the skill

- Purpose and Ideals 2, 8, 9, 13: best supported (Parnas, Baldwin and Clark, Simon, MacCormack, Ford et al.), but support is mostly theory, case studies and practitioner argument; only MacCormack is empirical, and it measures structure, not outcomes. Say "supported by theory and case evidence" rather than "proven".
- Ideals 1, 4, 6, 7 need a cost clause: configuration is expensive (Sayagh, Xu); a core pays back only with enough reuse (Krüger and Berger); a wrong abstraction is worse than duplication (Metz). Suggested addition to the "reached when" of 1: "and the core did not get harder to understand".
- Ideals 3, 10, 11: add that settings people never touch are cost (Xu: up to 54 percent seldom set) and that people rarely customize (Mackay), so a default must be good and bounded, which fits the 2026-10-12 calendar lesson. User-controlled adaptation is preferred in the one lab test (Findlater), small evidence.
- Ideals 5 and 12 (personal content, emergent categories): qualify with Pashler (a personal parameter needs measured benefit) and Lucas and Szatrowski (flexible case methods can fail simulations with known answers). Evidence for personalization working is strongest for intelligent tutoring (Kulik and Fletcher), weakest for UDL outcomes (Capp).
- Add a difficulty: "Change is concentrated" (Qiu, Fenton): most parts never change; spend flexibility on the few that do, and measure before assuming.
- Add a difficulty or note on size: the claim "many tiny parts beat huge files" has no clear empirical support for defects (Koru: smaller units can be proportionally worse; Hatton: middle size best; Fenton: no size link). The support is for named stable interfaces and hiding change (Parnas, Simon), not size. AI-code studies (Hu, Zhu) back his observation of monolithic output but are 2026 preprints.
- Add missing ideal candidate: "Variety at the edge matches variety of cases" (Ashby), as a check against both over-generalizing and under-fitting.
- Add to Keep-improving: undo a failed generalization by inlining it back (Metz), and treat fitness-function style checks as the guard (Ford et al.).

## Gaps

- Not verified or not found: Ragin's own QCA works (1987 and 2008) and any rebuttal to Lucas and Szatrowski; Lucas 1974 (already in Joshua's notes); design structure matrix primary source (Steward 1981); open-closed principle primary source (Meyer 1988, Martin 1996); the inner-platform effect (only practitioner folklore found); the rule of three (Fowler's Refactoring, not fetched).
- Parnas and Brooks content comes from background knowledge or secondary summaries; the Parnas ACM page and Baldwin and Clark SSRN page blocked fetching.
- No empirical study found that directly measures "over-engineering" cost beyond configuration studies; Wagner and Deissenboeck is conceptual.
- Personalized medicine versus protocol (thread 5) not covered; differentiated instruction not covered beyond UDL and learning styles.
- No peer-reviewed study of file or module size for LLM-written code versus maintainability; only 2026 preprints. The Krüger and Berger DOI was not fetched separately.
- Oppermann 1994 (Adaptive User Support) was seen only as a citation inside Fischer 2001.
- No source found that tests the "one core with parameters at the edge" idea as a whole against alternatives in a controlled way. That would be Joshua's own comparison to run, which suits the skill's ideal 9.
