# Functional components: iterate inside, reuse across systems

Verification labels: VERIFIED-PRIMARY (I read the text or the official record), VERIFIED-BIB (title, authors, year, venue, DOI confirmed in Crossref plus an abstract or summary seen; full text not read), VERIFIED-SECONDARY (details confirmed only through other papers or pages quoting it). Nothing below is UNVERIFIED; items where the substance rests on my background knowledge are flagged in the text. Krüger and Berger 2020 is already covered in public_research.md and is only referenced here.

## 1. What a component is

### McIlroy, 1968, "Mass produced software components" (NATO Software Engineering Conference, Garmisch; Naur and Randell eds., report 1969, pp. 138-155 of the report)
Link: http://homepages.cs.ncl.ac.uk/brian.randell/NATO/nato1968.PDF (section 8.2; downloaded and read)
What it finds: Argues for a components sub-industry that sells families of routines in catalogues, arranged by precision, robustness, generality and time-space performance, so a buyer picks one tailored to need and treats it as a black box. The families are cheap to make only because they are a few highly parameterized models whose parameters are bound at "sale time" (early binding). He also notes a user can later experiment with an alternative member of the family at low cost.
Relation: Supports and is the earliest statement of the idea. One family, parameters, and swappable members is exactly "iterate inside + reuse across systems with only configuration changed". It sharpens one point: the variation is designed as named dimensions (precision, range, robustness), not as ad hoc flags. It also warns that components must be flexible in more dimensions than a configuration generator for one system, because their niche in a system is less clearly delineated.
Strength: theory / practitioner position paper (invited address).
Verification: VERIFIED-PRIMARY.

### Szyperski, 1998 (2nd ed. 2002), Component Software: Beyond Object-Oriented Programming (Addison-Wesley / ACM Press)
Link: no open copy; definition as quoted and cited in https://www.jot.fm/issues/issue_2003_07/article3.pdf (JOT 2(4), 2003; the cited book date there is 1999, other sources say 1998, so the edition is uncertain)
What it finds: A software component is a unit of composition with contractually specified interfaces and explicit context dependencies only; it can be deployed independently and is subject to composition by third parties. The definition came out of the WCOP'96 workshop at ECOOP'96.
Relation: Supports and supplies the vocabulary. "Explicit context dependencies only" and "composition by third parties" are the properties that let code that does not use Joshua's framework still use the component. It says nothing directly about versioning inside, so it is silent on the iteration half (sharpening need: see section 3).
Strength: theory / practitioner (widely adopted definition).
Verification: VERIFIED-SECONDARY (exact wording read in the JOT paper; book itself not opened; page number not confirmed).

### Heineman and Councill (eds.), 2001, Component-Based Software Engineering: Putting the Pieces Together (Addison-Wesley), ch. 1 "Definition of Software Component and its Elements"
Link: https://www.informit.com/store/component-based-software-engineering-putting-the-pieces-9780201704853
What it finds: Defines a software component as an element that conforms to a component model and can be independently deployed and composed without modification according to a composition standard. The key phrase is "composed without modification".
Relation: Sharpens. "Without modification" is the strict test for reuse across systems: a copy that is edited per system is not the same component. This is the reuse half; iteration happens in the one shared source, never in forks. The definition wording came to me through a search snippet quoting the book, so treat as paraphrase.
Strength: theory / practitioner (edited volume).
Verification: VERIFIED-BIB for the book (publisher page, 2001, ISBN 978-0-201-70485-3); definition wording VERIFIED-SECONDARY.

### Not checked: Parnas component definitions, Brown and Short, UML
Parnas 1972 is already in public_research.md. Brown and Short 1997 and the UML specification definition were not fetched, so they are not used here. See Gaps.

## 2. What makes reuse pay (empirical)

### Frakes and Kang, 2005, "Software reuse research: status and future" (IEEE Transactions on Software Engineering 31(7), 529-536)
Link: https://doi.org/10.1109/TSE.2005.85 (open PDF copy: https://www.cse.chalmers.se/~feldt/courses/sple/papers/frakes_2005_sw_reuse_status_and_future.pdf)
What it finds: A short survey of twenty years of reuse research. It lists systematic reuse, module interconnection languages, commonality and variability analysis, variation points, domain engineering and generators as the main contributions, and points to unsolved problems.
Relation: Supports and sharpens. The field's answer to "how to reuse" is systematic and planned (domain analysis of what varies), not opportunistic copying, which matches parameters-at-the-edge. It is a survey, so it gives direction, not effect sizes.
Strength: review.
Verification: VERIFIED-BIB (abstract and topic list seen through ACM DL summary; full text not read).

### Lim, 1994, "Effects of reuse on quality, productivity, and economics" (IEEE Software 11(5), 23-30)
Link: https://doi.org/10.1109/52.311048 (the abstract page is https://ieeexplore.ieee.org/abstract/document/311048/)
What it finds: Reports metrics from two Hewlett-Packard reuse programs showing better quality (defect fixes accumulate across reuses), higher productivity, and better economics, while stating that reusable assets, a library and tools cost resources to build and maintain. Specific numbers circulate in secondary sources but I did not confirm them in the paper, so none are used.
Relation: Supports "iterate inside" strongly: the quality gain arises because fixes in the shared component reach every consumer. Sharpens by naming the cost side: someone must own and maintain the component.
Strength: empirical, two company case studies (single organization, so weak generality).
Verification: VERIFIED-BIB (abstract content seen; numbers not confirmed).

### Mohagheghi and Conradi, 2007, "Quality, productivity and economic benefits of software reuse: a review of industrial studies" (Empirical Software Engineering 12(5), 471-516)
Link: https://doi.org/10.1007/s10664-007-9040-x
What it finds: A systematic review of industrial observational studies and experiments from 1994 to 2005 that yielded eleven papers. Systematic reuse was related to lower defect density in five studies, less effort fixing problems in three, and productivity gains in three; other results were single-study or inconsistent. The authors call industrial evidence sparse and the synthesis vote-counting.
Relation: Supports in direction, challenges in strength. The benefit most often found is quality, which fits "iterate inside": one tuned component beats many copies. But the evidence base is small and mixed, so the skill should not claim reuse reliably saves effort.
Strength: review (systematic, small n).
Verification: VERIFIED-BIB (abstract content seen via search summary of the Springer abstract).

### Krüger and Berger, 2020 (referenced only)
Already covered in public_research.md section 2. Use it as the cost counterweight to the two papers above: clone-based reuse has lower upfront cost than platform reuse in their data, so componentizing needs a reason.

## 3. The tension: iterating inside a component vs staying reusable

### Raemaekers, van Deursen, Visser, 2017, "Semantic versioning and impact of breaking changes in the Maven repository" (Journal of Systems and Software 129, 140-158; earlier SCAM 2014 version, DOI 10.1109/SCAM.2014.30)
Link: https://doi.org/10.1016/j.jss.2016.04.008 (open copy via TU Delft: http://resolver.tudelft.nl/uuid:7c30551c-a00a-49c6-809a-48cc28a1b386)
What it finds: Studied versioning in over 100,000 jar files from Maven Central (22,000+ libraries, 7 years). Backward-incompatible changes were common, including in releases that semantic versioning says should be compatible, and they affected client systems. Developers do not reliably follow versioning rules.
Relation: Challenges. Iterating inside breaks consumers in practice even when a convention promises otherwise. The skill needs a mechanism that checks compatibility (tests at the interface), not only a version number.
Strength: empirical (large corpus, Java/Maven only).
Verification: VERIFIED-BIB (abstract read via Semantic Scholar record and open-access summary; exact share of breaking releases left out of this note because I only saw it through a summary).

### Dietrich, Pearce, Stringer, Tahir, Blincoe, 2019, "Dependency versioning in the wild" (MSR 2019, 349-359)
Link: https://doi.org/10.1109/MSR.2019.00061 (preprint: https://whileydave.com/publications/DPSTB19_MSR_preprint.pdf)
What it finds: Examined about 70 million dependency declarations across 17 package managers plus a survey of 170 developers. Most ecosystems allow version ranges and use them, but developers struggle to choose between pinned versions (predictable) and ranges (get fixes); experienced developers tend to move toward pinning after compatibility errors. There was no evidence of a large-scale shift to semantic versioning.
Relation: Sharpens. Consumers of a shared component trade stability against improvements, and the practical answer is often to pin. So "iterate inside" and "reuse across" are reconciled by pinning plus deliberate upgrade, not by assuming consumers follow along automatically.
Strength: empirical (very large, plus survey).
Verification: VERIFIED-BIB (abstract and search summary; full text not read).

### Wright (named by Winters), "Hyrum's Law"
Link: https://www.hyrumslaw.com/
What it finds: States that with enough users of an API, all observable behaviors of the system will be depended on by somebody, whatever the contract promises. The page credits Hyrum Wright and says Titus Winters named and spread it.
Relation: Challenges. A component's real interface is larger than its declared one, so internal iteration (even a pure improvement) can break an unknown consumer. Argues for narrow, explicit interfaces and for tests that pin the behaviors callers actually rely on.
Strength: practitioner observation, not a controlled study.
Verification: VERIFIED-PRIMARY (page fetched; statement and attribution read). A 15-word fragment: "all observable behaviors of your system will be depended on by somebody".

### Liskov and Wing, 1994, "A behavioral notion of subtyping" (ACM TOPLAS 16(6), 1811-1841)
Link: https://doi.org/10.1145/197320.197383
What it finds (from my background knowledge, since only the record was checked): A new implementation can safely replace an old one only if it preserves the behavior that clients may rely on, expressed with invariants and history constraints, not just matching signatures.
Relation: Sharpens. This is the formal criterion for "swap implementations without callers changing": same signature is not enough, behavior the contract promises must hold.
Strength: theory.
Verification: VERIFIED-BIB (Crossref record only: title, authors, year, journal, DOI; content statement is from my own knowledge and not re-read).

### Parnas, 1979, "Designing software for ease of extension and contraction" (IEEE Transactions on Software Engineering SE-5(2), 128-138)
Link: https://doi.org/10.1109/TSE.1979.234169
What it finds (background knowledge, not re-read): Proposes designing a program as a family so that subsets and extensions can be built, using a "uses" relation that lets parts be removed or added, and information hiding so a module's decisions can change without touching others.
Relation: Supports and sharpens: it is the design-for-versions companion to Parnas 1972 and McIlroy's families. The idea that a component's hidden decisions are what you iterate on, while the interface is held steady, comes from here.
Strength: theory.
Verification: VERIFIED-BIB (Crossref record only).

## 4. Reusable components outside software

### Polsani, 2003, "Use and abuse of reusable learning objects" (Journal of Digital Information 3(4))
Link: http://jodi.ecs.soton.ac.uk/Articles/v03/i04/Polsani (as cited by other sources; I did not open this page)
What it finds: Defines a learning object as an independent, self-standing unit of learning content predisposed to reuse in multiple instructional contexts, and argues its size should follow the concept it teaches, not a fixed length.
Relation: Supports for courses and curricula: the same module placed in many courses, with context supplied outside it. The same literature also contains the main caution (see section 5): learning objects reused out of context lose meaning.
Strength: theory / conceptual paper.
Verification: VERIFIED-SECONDARY (title, author, venue, year and definition confirmed only through citing sources; full text not read).

### Haynes et al., 2009, "A surgical safety checklist to reduce morbidity and mortality in a global population" (New England Journal of Medicine 360(5), 491-499)
Link: https://doi.org/10.1056/NEJMsa0810119
What it finds: A 19-item checklist introduced in eight hospitals in eight cities worldwide. In a before-and-after design with about 3,700 and 3,950 patients, the death rate fell from 1.5 to 0.8 percent and inpatient complications from 11.0 to 7.0 percent.
Relation: Supports reuse across systems: one standard procedure module works across very different hospitals with local adaptation of how it is run, and it can be revised over time. Limit: before-and-after without a control group, so effect size should be reported with that caveat. It is an example of a protocol module, and a standard-operating-procedure analogue.
Strength: empirical (multi-site, uncontrolled before-and-after).
Verification: VERIFIED-BIB (Crossref record plus figures from search summary of abstract).

## 5. Failures of reuse and lock-in

### Garlan, Allen, Ockerbloom, 1995, "Architectural mismatch: why reuse is so hard" (IEEE Software 12(6), 17-26; ICSE 1995 version; a 2009 follow-up in IEEE Software)
Link: https://doi.org/10.1109/52.469757 (PDF copy: https://users.ece.utexas.edu/~perry/education/SE-Intro/mismatch-sw94.pdf)
What it finds: A reusable part carries assumptions about the system structure it will sit in (control, data, environment); when they clash with other parts, integration costs far more than expected. Their examples came from building Aesop from existing packages that ran "out of the box" in early tests but needed major modification later.
Relation: Challenges and sharpens Szyperski's "explicit context dependencies only". The component must not hide structural assumptions (it owns its main loop, it assumes one process, it assumes a data format); parameters can fix values but not structure. Directly relevant to framework lock-in: a component that assumes the framework's control flow is not reusable outside it.
Strength: practitioner experience report (single project, widely cited).
Verification: VERIFIED-BIB (record; abstract and thesis confirmed from search summary; full text not read).

### Katz and Allen, 1982, "Investigating the Not Invented Here (NIH) syndrome" (R&D Management 12(1), 7-20)
Link: https://doi.org/10.1111/j.1467-9310.1982.tb00478.x
What it finds: In 50 R&D project groups, performance rose until about 1.5 years of mean group tenure and declined by five years, explained by falling communication with the group's outside information sources, which the authors present as NIH. One critique argues the analysis is weak.
Relation: Mostly peripheral. It supports a cautious claim: long-standing teams become insular and stop looking at external components. It is not a study of software reuse, and the NIH label is used for tenure decline, so use only as a mechanism hint, not as evidence that reuse is missed.
Strength: empirical but old, indirect and contested.
Verification: VERIFIED-BIB (Crossref plus summary of abstract; the critique was seen only in a search summary).

### Krüger and Berger, 2020 (referenced only)
Their finding that reuse can cost more than it saves is the main evidence for the "reuse costs more than it saves" thread. The skill should keep citing it there.

## Proposed wording
A functional component is one piece of a larger system with a narrow, explicit interface and explicit dependencies, so other systems (including code that does not use the author's framework) can use it by changing only parameters or configuration, composed without modification. Its inside stays free to improve: versioned, tuned, or replaced by a better implementation behind the same interface, with tests of the promised behavior and a stated version so callers can adopt a change on purpose. It earns the name only when it holds across more than one system without forking.

## What this changes in the skill
- Adopt Szyperski plus Heineman and Councill as the definition test: explicit interface, explicit context dependencies only, deployable alone, composed without modification. A copy-and-edit per system fails the test.
- Add the McIlroy rule: variation is a named family (dimensions such as precision or robustness) with early-bound parameters. This is the old form of atoms and molecules, and it is a good citation for them.
- Add a "compatibility" half to the iterate-inside rule: semantic versioning is not enough (Raemaekers) and hidden behavior becomes the real interface (Hyrum's Law), so keep a behavior-level test for swapped implementations (Liskov and Wing) and let consumers pin versions (Dietrich).
- Add a no-framework check from Garlan et al.: list the structural assumptions a component makes (control flow, process model, data format), not only its parameters, and remove any that need the framework.
- State the evidence honestly: reuse evidence leans toward quality gains and is thin and mixed (Mohagheghi and Conradi), with costs of building and owning the component (Lim, Krüger and Berger); do not promote componentizing a one-off.

## Gaps
- Brown and Short, UML component definition, Parnas on components, and the original Heineman and Councill text were not opened; their definitions are not used here.
- No empirical study found or checked on "same component used in many systems with only config changed" as such; evidence is indirect (reuse reviews, versioning studies).
- Semantic versioning evidence is Java/Maven and package manager data; nothing on Python or ML pipeline stages, nothing on LLM-prompt components.
- Non-software evidence is thin: one conceptual learning-object source (not fully read) and one checklist trial; microlearning and SOP-specific studies were not verified. Also not checked: the criticism that learning objects lose meaning out of context (known from the literature but not verified here).
- Framework lock-in as a studied topic: only Garlan et al. verified; no direct empirical study on lock-in found.
- Liskov and Wing and Parnas 1979 summaries rest on my knowledge; only bibliographic records were checked.
