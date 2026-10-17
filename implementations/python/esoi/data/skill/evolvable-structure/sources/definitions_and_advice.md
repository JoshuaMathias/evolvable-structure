# Notes: definitions and general advice for "adaptable structure"

Pass date 2026-10-14. Scope: vocabulary (A) and general advice (B). Not repeated: Parnas, Baldwin and Clark, Simon, MacCormack, configuration-cost studies, UDL/learning styles, Ashby, Lucas and Szatrowski, Metz/Fowler/Brooks, size-defect studies, AI-code preprints.

Verification labels used below:
- **FETCHED**: I read the primary page or full text (or text extracted from the PDF).
- **SEARCH-RECORD**: citation details (title, authors, year, DOI) confirmed in search results from several sites, but I did not read the text itself.
- **SECONDARY**: content confirmed only through a secondary page (for example Wikipedia or a review); wording is not the source's own.
- **UNVERIFIED**: could not confirm; not used in the summary.

## A. Vocabulary

| Term | Established meaning (own words) | Source | Difference from or overlap with Joshua's "adaptable structure" | When to use which word |
|---|---|---|---|---|
| Adaptability (ISO) | How effectively and efficiently a product can be adapted for, or moved to, different hardware, software or usage environments. Sits under "Flexibility" in the newer quality model. | ISO/IEC 25010 (iso25000.com summary) | Overlaps: new environment, same product. Differs: ISO's adaptability is about environments the product runs in; Joshua's is about new people, domains, data and experiments served by one core, and about progress across iterations. | Use "adaptable" for a structure that can be fitted to a new case by a person. Say which cases. |
| Modifiability | How effectively and efficiently a product can be changed without adding defects or losing quality. | ISO/IEC 25010 (Maintainability); Bass, Clements, Kazman | Overlaps with the cost-of-change part. Differs: modifiability is about changing the code or artifact; Joshua wants new cases to need no edit of the core. | Use for "how costly is an edit". Use "adaptable" when the aim is that no edit is needed. |
| Modularity, reusability | Modularity: parts composed so that altering one barely affects the rest. Reusability: usable as an asset in more than one system. | ISO/IEC 25010 | Ideal 1 and 2 are these two, plus naming and edge parameters. | Use as the enabling properties, not as the goal. |
| Flexibility | Two senses. (a) Ease of change (Fricke and Schulz). (b) Change driven by an agent outside the system (Ross et al.). In ISO 2023-style models, a group heading that contains adaptability, scalability, installability and replaceability. | Fricke and Schulz 2005; Ross, Rhodes, Hastings 2008; ISO/IEC 25010 | Closest everyday synonym but too loose. Skill already warns "too general fails". | Avoid as a technical term; say what varies. |
| Adaptable vs adaptive (HCI) | Adaptable: a person changes the system (customizes). Adaptive: the system changes itself from a model of the user or context. | McGrenere, Baecker, Booth 2007 (abstract); Oppermann 2005 via secondary pages | Joshua's "adaptable" matches the HCI "adaptable": people change it, and ideal 3 says reversible defaults proceed while irreversible ones wait for a person. | Use "adaptable" when people control the change, "adaptive" only where the system changes itself. |
| Adaptable vs flexible (systems engineering, reversed) | Ross et al. call a change "flexible" when the change agent is outside the system boundary and "adaptable" when it is inside. This is close to the reverse of the HCI use, where adaptable means the person (outside) acts. | Ross et al. 2008 | Warning: the same word has opposite meanings in two fields. | When writing for engineers, state who or what makes the change, and name the system boundary. |
| Changeability | Umbrella term for a system's ability to be changed, described by change agent, change effect and change mechanism. Counted as the number of acceptable change paths available. | Ross, Rhodes, Hastings 2008 | Best match for a measurable "reached when": count the change paths that need no core edit. | Use as the umbrella; "adaptable structure" is one kind of changeable system. |
| Agility (architectural) | Ability to be changed rapidly (Fricke and Schulz). Ross treats it as a modifier of speed, not a separate kind of change. | Fricke and Schulz 2005; Ross et al. 2008 | Joshua's aim is not speed alone but that each change keeps what was learned. | Use for speed of change only. |
| Robustness | Insensitivity to a changing environment, with no change to the system itself. | Fricke and Schulz 2005; Ross et al. 2008 | Opposite strategy: robust systems resist change, adaptable ones accommodate it. | Use when the thing should not change when the context does. |
| Resilience, antifragility | Resilient: resists shocks and stays the same. Antifragile: gains from shocks and disorder. | Taleb 2012 (publisher and record summaries) | Joshua's "progress across iterations" is learning, which is nearer antifragility in spirit, but Taleb's term is not operational and not about design structure. | Avoid; use only to note that iteration should make the structure better, not just survive. |
| Variability | Planned difference between products or cases, realized by mechanisms (inheritance, parameters, plugins, and so on) bound at some point in the life cycle. Realization often delays design decisions. | Svahnberg, van Gurp, Bosch 2005 | The strongest software neighbor: product families are "one core, many cases". Differs: variability work assumes a known set of variants in advance. | Use "variability" for the set of differences; "adaptable structure" for the whole design that holds them and keeps improving. |
| Extensibility | Common usage: new capability added without changing existing parts. No sub-characteristic by this name appeared on the ISO 25010 page I read. | UNVERIFIED as an ISO term (see Gaps) | Overlaps ideal 1 and 13 (a third case needs no core edit). Differs: extensibility concerns adding features; Joshua's concerns adding cases that reuse the same method. | Use for adding behavior through plug points. Not a synonym. |
| Configurability | Behavior set by settings rather than code. | Not defined from a fetched source (configuration cost studies are covered by another pass) | One mechanism for ideals 1, 3 and 4. A structure can be adaptable through definitions and content, not only settings. | Use for the settings layer only. |
| Supports and infill (Open Building) | A shared, durable base (support) decided collectively, and changeable dwelling parts (infill) decided by each household, with decisions distributed by level. | Habraken 1961/1972 (SECONDARY); Kendall and Teicher 2000 (SEARCH-RECORD) | Closest analogue for ideal 5 (shared container, personal content). See entry below. | Use as an analogy when explaining who decides what. |
| Shearing layers, pace layers | A building (or society) is layers that change at different speeds: slow layers support, fast layers experiment. | Duffy; Brand 1994 (SECONDARY); Brand and Saffo talk 2015 (FETCHED) | Close on "parts change at different rates". Differs on purpose and scope. | Use to decide where flexibility belongs. |
| Organic vs mechanistic organization | Mechanistic (fixed hierarchy) fits stable conditions; organic (flexible roles, lateral communication) fits unstable ones. | Burns and Stalker 1961 (SECONDARY) | Organizational sense of a changeable structure. Qualifies "one core": the right amount of fixed structure depends on how fast the environment changes. | Use for people and teams. |
| Semistructure | Limited structure on responsibilities and priorities, plus wide freedom and communication, plus time-paced rhythm. | Brown and Eisenhardt 1997 (SEARCH-RECORD) | Very close to ideal 5 (common rhythm, personal content) in organizations. | Use for organizations and teams. |

**Proposed use of words.** "Adaptable structure" is fine and consistent with the HCI meaning (people adapt it). Keep "adaptive" for self-changing behavior, and avoid "flexible" unless defined.

### ISO/IEC 25010 (product quality model)
- Link: https://iso25000.com/index.php/en/iso-25000-standards/iso-25010 and `?start=5` (a site summarizing the standard; the standard itself is ISO/IEC 25010, product quality model, 2011 with a later revision).
- Finding: Maintainability contains modularity, reusability, analysability, modifiability and testability. A group named Flexibility contains adaptability, scalability, installability and replaceability. Adaptability is the degree to which a product can be adapted for or transferred to different hardware, software or usage environments. Modifiability is the degree to which it can be modified without new defects or loss of quality.
- Caveat: the summary page showed no edition year, and the Flexibility grouping looks like the newer revision (older 2011 text put adaptability under Portability). I did not read the standard itself.
- Verification: FETCHED (summary site), standard text not read. Edition marked UNVERIFIED.

### Fricke and Schulz 2005, "Design for Changeability (DfC)"
- Link: https://doi.org/10.1002/sys.20039 (Systems Engineering 8(4): 342-359). Record: https://www.semanticscholar.org/paper/Design-for-changeability-(DfC):-Principles-to-in-Fricke-Schulz/91830614f443f55872f2139d7e9695add5fd8104
- Finding: names four aspects of changeability: robustness (insensitive to change in the environment), flexibility (changed easily), agility (changed rapidly) and adaptability (adapts itself to a changing environment). Gives design principles for each. Motivated by dynamic markets, technology change and varied environments.
- Verification: SEARCH-RECORD for citation; definitions seen in a search snippet and confirmed as quoted by Ross et al. (below), which I read.

### Ross, Rhodes, Hastings 2008, "Defining Changeability"
- Link: https://doi.org/10.1002/sys.20098 (Systems Engineering 11(3)); preprint: https://web.mit.edu/adamross/www/Ross_JSE07_preprint.pdf
- Finding: ambiguity in the "ilities" blocks specifying and verifying them, so they relate everything to "changeability" through change agent, change effect and change mechanism. Flexibility vs adaptability depends on whether the change agent is outside or inside the system boundary. Scalability, modifiability and robustness describe change effects. Extent of changeability is counted as the number of acceptable change paths (a "filtered outdegree"). Agility is treated as speed. Dove 2005 defines agility broadly.
- Relevance: the strongest published argument that these words are used inconsistently, and a countable test for "reached when".
- Verification: FETCHED (preprint text extracted). Wiley page returned 403, so the journal version was not opened; volume and issue from search record.

### McGrenere, Baecker, Booth 2007, "A Field Evaluation of an Adaptable Two-Interface Design for Feature-Rich Software"
- Link: https://doi.org/10.1145/1229855.1229858 (ACM TOCHI 14(1), Article 3). PDF: https://www.cs.ubc.ca/labs/edapt/papers/mcGrenere2007.pdf
- Finding: contrasts system-controlled adaptive menus with user-controlled adaptable menus. In a field experiment, most users personalized effectively when given an easy mechanism, and the adaptable design gave better navigation and learnability than the one adaptive system tested.
- Relevance: supports "adaptable means the person changes it", and supports ideal 3 and 11. Evidence is one field study with one adaptive system.
- Verification: FETCHED (abstract and citation text). The "adaptable vs adaptive" gloss from Oppermann 2005 came only through secondary pages (SECONDARY).

### Svahnberg, van Gurp, Bosch 2005, "A taxonomy of variability realization techniques"
- Link: https://doi.org/10.1002/spe.652 (Software: Practice and Experience 35(8): 705-754). Record: https://research.rug.nl/en/publications/a-taxonomy-of-variability-realization-techniques/
- Finding: product families use variability to manage differences between products, partly by delaying design decisions to later stages; the paper catalogs the mechanisms for realizing it.
- Verification: SEARCH-RECORD (citation and opening of abstract only; text embargoed).

### Habraken, supports and infill; Kendall and Teicher, Open Building
- Links: https://en.wikipedia.org/wiki/N._John_Habraken (SECONDARY); Kendall and Teicher, *Residential Open Building* (E and FN Spon, 2000), https://doi.org/10.4324/9780203056769 ; search record at https://www.uceb.eu/DATA/CivBook/43.%20Residential%20Open%20Building,%20Stephen%20Kendall%20and%20Jonathan%20Teicher.pdf
- Finding: Habraken's *De Dragers en de Mensen* (1961; English *Supports: An Alternative to Mass Housing*, 1972) proposed separating a shared base building ("supports") from the parts residents decide for themselves ("infill"), to give residents a real role. Open Building (Kendall and Teicher) rests on three ideas from Habraken: levels, supports and infill. Decisions are distributed across levels (urban, building, infill) with different people deciding at each, so each level can change without disrupting the others. The durable part is decided collectively; the changeable part by each household. Habraken led the SAR research group (1965-1975) on methods for adaptable housing.
- Verification: SECONDARY for Habraken (Wikipedia); SEARCH-RECORD for Kendall and Teicher (summary through a search result, text not read). open-building.org failed an HTTPS certificate check, and habraken.com's page was only a bibliography. I did not read Habraken's own text.

### Brand 1994 (How Buildings Learn) and Duffy: shearing layers; Brand and Saffo talk
- Links: https://en.wikipedia.org/wiki/Shearing_layers (SECONDARY); https://longnow.org/talks/02015-brand-saffo/ (FETCHED); Brand's essay https://jods.mitpress.mit.edu/pub/issue3-brand (403, not read).
- Finding: Frank Duffy described a building as layers of different longevity (shell, services, scenery, set). Brand's book (Viking, 1994) expands this to six layers: site, structure, skin, services, space plan, stuff, with typical lifespans from centuries (site, structure) to days or months (stuff). The claim is that buildings adapt well when fast layers are not blocked by slow ones. The 2015 Long Now talk page states the later "pace layers" version: fast layers generate novelty, slow layers keep what is established, and friction between them is useful. Evidence is observation and case studies, not controlled study.
- Verification: book title, author, publisher and year confirmed in search results; layer lifespans from Wikipedia (SECONDARY); talk page FETCHED.

### Schmidt and Austin 2016, Adaptable Architecture: Theory and Practice
- Link: https://www.routledge.com/Adaptable-Architecture-Theory-and-practice/SchmidtIII-Austin/p/book/9780415522588
- Finding: Routledge, 2016, 318 pages, Loughborough University authors. Aim: extend a building's useful life by designing it for change. Treats adaptability as a complex design phenomenon that includes purpose, design and business case, not only the physical object. The chapter list includes "Buildings as Layers", "A Typology of Adaptability" and "Design Strategies, Characteristics and Tactics". The publisher page gives no definition of adaptable vs flexible; I could not read the glossary or typology.
- Verification: FETCHED (publisher page). Definitions UNVERIFIED.

### Burns and Stalker 1961, The Management of Innovation
- Link: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1496187 (record); published by Tavistock, London, 1961.
- Finding: from a study of 20 electronics firms: a mechanistic management system suits stable conditions; an organic one suits unstable conditions. The authors presented the two as ends of a range matched to the rate of environmental change.
- Verification: SECONDARY (search summaries and an SSRN record); not read.

### Taleb 2012, Antifragile
- Link: https://books.google.com/books/about/Antifragile.html?id=5fqbz_qGi0AC
- Finding: the resilient resists shocks and stays the same; the antifragile gets better from them. Published by Random House (US) and Penguin (UK), 27 November 2012.
- Verification: SEARCH-RECORD (publisher and book-record summaries).

### Salehie and Tahvildari 2009, "Self-adaptive software: Landscape and research challenges"
- Link: https://doi.org/10.1145/1516533.1516538 (ACM TAAS 4(2), 14:1-14:42).
- Finding: taxonomy of self-adaptation by how, what, when and where; self-adaptive is typically top-down, self-organizing bottom-up. Could not confirm its wording on "adaptive vs adaptable".
- Verification: SEARCH-RECORD only. Not used in the table.

## B. General advice

### Brand 1994 and the Long Now talk: separate by rate of change
- Advice: arrange parts by how fast they change, keep the slow ones stable underneath, and do not let a fast part wait on a slow one. Friction between layers is normal and useful.
- Source: https://longnow.org/talks/02015-brand-saffo/ (FETCHED); *How Buildings Learn* (1994).
- Evidence: practitioner/case observation (not controlled).
- Recommendation: **add as an ideal** ("Parts are separated by how fast they change, so a fast change never waits on a slow part"). The skill has "most parts rarely change" as a difficulty but not this positive design rule. Reached when: a typical change touches only the layer that normally changes.

### Bezos 2015 letter: one-way and two-way doors
- Advice: sort decisions into those that cannot be undone and those that can; take the slow, careful path only for the first, and decide the second quickly. Treating every choice as irreversible produces slowness and less experimentation.
- Source: Amazon 2015 shareholder letter, https://www.sec.gov/Archives/edgar/data/1018724/000119312516530910/d168744dex991.htm (FETCHED).
- Evidence: practitioner.
- Recommendation: **qualify ideal 3** (add: match the weight of process to reversibility; heavy process on a reversible default is itself a cost). Do not add a new ideal.

### Poppendieck and Poppendieck 2003: last responsible moment
- Advice: delay a commitment until the moment at which not deciding would eliminate an important alternative, and no later; waiting past that point means deciding by default.
- Source: *Lean Software Development: An Agile Toolkit* (Addison-Wesley, 2003, ISBN 0321150783), chapter 3; quoted at https://blog.codinghorror.com/the-last-responsible-moment/ (search record).
- Evidence: practitioner.
- Recommendation: **add as a difficulty**: a general design for a case not yet seen is a deferred decision made too early. It supports the existing "usually two real cases" rule and gives it a name and a limit (do not wait forever).
- Verification: book SEARCH-RECORD (title, year, ISBN, chapter list); quotation via blog, not the book.

### Fowler 2003: architecture is what is hard to change
- Advice: treat "architecture" as the decisions people think are hard to change, and try to reduce them. Irreversibility drives complexity; but making everything easy to change makes the whole system very complex, so choose which things to make easy.
- Source: Fowler, "Who Needs an Architect?", IEEE Software, 2003, https://martinfowler.com/ieeeSoftware/whoNeedsArchitect.pdf (FETCHED, text extracted).
- Evidence: practitioner.
- Recommendation: **add as a difficulty** (qualifies ideals 1 and 3): flexibility has a complexity price at the system level, so spend it on the few decisions that really are costly to reverse. The skill's difficulties already say "spend flexibility on the few"; this adds the reason and the strategy of making a hard thing easy (his database-migration example). Not new enough for an ideal.

### Conway 1968 and Colfer and Baldwin 2016: structure copies communication
- Advice: the structure of a system tends to copy the communication structure of the group that builds it, and splitting teams early locks in design choices. Keep organization flexible while the design concept is still moving.
- Sources: Conway, "How Do Committees Invent?", Datamation, April 1968, https://www.melconway.com/Home/Committees_Paper.html (FETCHED); Colfer and Baldwin, Industrial and Corporate Change 25(5), 2016, https://doi.org/10.1093/icc/dtw027 (SEARCH-RECORD).
- Evidence: Conway is theory with examples. Colfer and Baldwin review 142 studies: mirroring is common but not universal, about a quarter of within-firm and buyer-supplier studies showed partial or no mirroring, open collaborative software projects did not support it, and among normative firm studies unmirrored organizations performed poorly in 10 cases, with premature modularization the common thread (as reported in the search record).
- Recommendation: **add as a difficulty**: who owns the core and who owns the edge shapes the structure, and splitting into modules or teams too early can freeze a bad split. This qualifies ideal 2. It is the best empirical item in this pass, though read through a summary.

### Brown and Eisenhardt 1997: semistructures and time-paced change
- Advice: in continuously changing organizations, fix a little structure (responsibilities, priorities, a rhythm) and leave wide freedom inside it; link present and future through a fixed cadence; run cheap probes of what comes next.
- Source: Administrative Science Quarterly 42(1): 1-34, https://doi.org/10.2307/2393807 (SEARCH-RECORD; full-text links listed in the search result).
- Evidence: empirical but qualitative (six computer firms, interviews).
- Recommendation: **add to ideal 5 as support**, and consider "low-cost probes" under ideal 9. The "fixed cadence" idea fits "rhythm is common" in ideal 5 and the iterate-and-compare purpose. Not a new ideal.

### Burns and Stalker 1961: structure should fit the rate of change
- Advice: stable conditions suit a fixed, formal structure; unstable ones suit looser, lateral structures. The task is to read how fast the environment changes and fit the structure to it.
- Source: Burns and Stalker, *The Management of Innovation*, Tavistock, 1961 (SECONDARY).
- Evidence: empirical (20 firms) with later critique that it may not hold for new ventures in turbulent young sectors.
- Recommendation: **add as a difficulty** (qualifies "one core"): the amount of fixed structure should follow how fast the environment actually changes; a core designed for variety that never arrives is overhead. Overlaps "most parts rarely change". May fold into the Brand ideal rather than stand alone.

### Gall 1975: start from a working simple system
- Advice: a complex system that works grew out of a simpler working one; one designed complex from scratch does not work and cannot be patched into working.
- Source: Gall, *Systemantics* (first as *General Systemantics*, 1975; Quadrangle 1977). Checked at https://en.wikipedia.org/wiki/John_Gall_(author).
- Evidence: practitioner aphorism, no empirical test found.
- Recommendation: **add as a difficulty, or leave out**. It echoes "generalize from two real cases" and "inline back". If added, say that the general core should be grown from a working specific case.
- Verification: SECONDARY.

### Bass, Clements, Kazman: modifiability tactics and binding time
- Advice: make changes local (cohesive modules, few dependencies) and treat binding time as a dial: parameters, configuration and plug-ins bind later than code, which widens flexibility.
- Source: *Software Architecture in Practice* (Addison-Wesley; editions 2003, 2012, 2021), summaries at https://software-architecture-guild.com/guide/architecture/characteristics/modifiability/ and sample pages at https://ptgmedia.pearsoncmg.com/images/9780321815736/samplepages/0321815734.pdf (search results only).
- Evidence: practitioner/theory.
- Recommendation: **leave out as a new item**; use "binding time" as vocabulary in `principles.md` because it names what moving a difference "to the edge" does. The later-binding cost (harder to check) is already in the skill ("flexibility makes checking harder").
- Verification: SEARCH-RECORD; I did not read the book.

### Ousterhout 2018: deep modules
- Advice: a module's interface should be much simpler than what it hides; many small shallow parts add complexity rather than remove it.
- Source: *A Philosophy of Software Design* (Yaknyan Press, 2018) per search summaries; reviews at https://www.pathsensitive.com/2018/10/book-review-philosophy-of-software.html (critical of how "simple" is judged).
- Evidence: practitioner; the reviewer notes it rests on intuition.
- Recommendation: **leave out** as a new item, since the skill already says small size is not evidence and ideal 13 puts the support on stable interfaces. Possible one-line support for ideal 13.
- Verification: SEARCH-RECORD (publisher details not confirmed).

### Wiggins and McTighe 2005: backward design for courses
- Advice: plan a course from the intended results, then the evidence that they were reached, then the learning activities, and aim at transfer, not coverage.
- Source: *Understanding by Design*, expanded 2nd ed., ASCD, 2005; framework paper https://files.ascd.org/staticfiles/ascd/pdf/siteASCD/publications/UbD_WhitePaper0312.pdf (SEARCH-RECORD).
- Evidence: practitioner/education theory.
- Recommendation: **leave out; cross-reference**. It matches "definition (what, with a measure) separate from implementation (how)" in the How to think section, and "transfer" is a useful statement of why a course core serves many learners. Could be cited as non-software support for that step.

### Taleb 2012: antifragile
- Advice: prefer designs that gain from shocks over designs that merely survive them.
- Source: https://books.google.com/books/about/Antifragile.html?id=5fqbz_qGi0AC
- Evidence: theory, argued largely by example.
- Recommendation: **leave out** (not operational for structure design). Mention only in vocabulary.

## How close is the building analogue? An honest assessment

Close on three points.
1. Fixed support, changeable infill. Habraken's split matches ideal 5 and ideal 1: a shared base serviced for everyone, and the part that differs per household chosen by that household.
2. Decisions by level. Open Building says who decides what at each level; Joshua's ideals 3, 5 and 11 say the same about people and defaults.
3. Layers by rate of change. Duffy and Brand's layers are the clearest statement of "most parts rarely change, spend flexibility on a few".

Not close on four points.
1. Purpose. Habraken and Brand are about one building (or one household) serving changing use over a long life, and about residents' control. Joshua's purpose is progress across iterations, which means alternatives compared on a measure and what was learned carried forward. Buildings have no baseline and no comparison step (ideal 9).
2. Many cases at once. Joshua's core serves many people and domains simultaneously, which is nearer a product family (variability literature) than one building changing over time.
3. Content as behavior. Ideals 6 and 7 (definitions a person can read that drive behavior, specifics connected from outside) have no building counterpart.
4. Evidence. Brand's claims rest on observation of buildings; I found no controlled test, and Schmidt and Austin's definitions could not be read.

Verdict: a good analogy for the shape (stable support, decided-by-level infill, layers by rate), and a good teaching image; not a source for the purpose or for ideals 6 to 9 and 12. Use it as an illustration, with this limit stated.

## Proposed definition

An adaptable structure is a stable core that a person can fit to a new case, such as another person, domain, dataset or experiment, by changing a parameter, a name or content at the edge, without editing the core. It is built so that each such change can be tried, compared with the alternatives and kept or reversed, so the work improves over iterations.

How it differs: "adaptive" changes itself without a person (the HCI and self-adaptive software meaning), "flexible" only says change is easy, "configurable" is one mechanism (settings) for part of it, and "extensible" is adding new capability, not fitting the same core to new cases.

## What this changes in the skill

- Add a vocabulary note to `principles.md` (not `SKILL.md`): "adaptable" means a person changes it, "adaptive" means it changes itself, and Ross et al. use the opposite split, so state who makes the change. Source: McGrenere et al. 2007; Ross et al. 2008.
- Add an ideal on layers: parts are separated by rate of change, slow parts stable underneath, fast parts never waiting on slow ones (Brand and Duffy, practitioner evidence). Name the building analogue and its limits.
- Add a difficulty: deferring a decision to the last responsible moment is a reason not to build the general version before the second case, and a limit (do not wait past the point where an alternative is lost). Sources: Poppendieck; Fowler (irreversibility, and the complexity price of making everything easy to change); Gall.
- Qualify ideal 3: weight the process by reversibility, since heavy approval on reversible defaults costs experimentation (Bezos 2015).
- Add a difficulty on organization: the structure copies the team structure, premature modularization hurts, and the right amount of fixed structure follows the rate of change (Conway 1968; Colfer and Baldwin 2016; Burns and Stalker 1961).
- Use "changeability as a count of change paths that need no core edit" (Ross et al. 2008) as a possible "reached when" test for ideal 1, and note Brown and Eisenhardt's fixed rhythm plus cheap probes as support for ideals 5 and 9.

## Gaps

- ISO/IEC 25010: I read a summary site, not the standard, and could not confirm the edition. Extensibility is not an ISO 25010 sub-characteristic on the page I read; no authoritative extensibility definition was fetched.
- IEEE/SEI/Bass-Clements-Kazman: only search summaries; the IEEE Std 610.12 and ISO/IEC/IEEE 24765 vocabulary entries for "modifiability", "flexibility" and "evolvability" were not retrieved.
- Open Building: Habraken's own text, Kendall and Teicher's text, Brand's book and Schmidt and Austin's glossary were not read. open-building.org failed a certificate check and Brand's MIT Press essay returned 403.
- Burns and Stalker, Brown and Eisenhardt, Colfer and Baldwin, Svahnberg et al., Taleb and Salehie and Tahvildari are verified by citation records and summaries only; confirm the specific claims before quoting.
- Configurability and "adaptable organization" (for example dynamic capabilities or agile-at-scale frameworks) have no strong source here; the organizational evidence found is two classic studies, not recent evidence.
- No source found tests the whole "one core, parameters at the edge, across iterations" claim, which matches the earlier note in `principles.md`.
- Courses and processes: only Wiggins and McTighe was checked; other course-design and process-improvement sources (for example Deming or Shewhart cycles) were not examined.
