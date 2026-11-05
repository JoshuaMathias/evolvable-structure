# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Handle | Layer | Role | Serves |
|---|---|---|---|---|
| Guides and Explanations | `documentation` | docs | Explanation, guides and non-code templates (the main feature of the repository). | the-standard, the-steps |
| Adopter Testimonials | `examples` | docs | Adopters as short examples and testimonials. | the-standard |
| Records of This Repository | `structure-registry` | docs | The records (CSV) and generated pages of every intent: the top intent in esoi/ and each container with the solutions beside their code. | intent-registry |
| Project Files | `project-files` | project | Files at the repository root: readme, configuration, contributing, licence. | the-standard |
| GitHub Wiki Generator | `wiki` | scripts | A thin wrapper that generates this repository's GitHub wiki from docs/ through esoi docs wiki. | the-standard |
| Docs Standard | `docs-standard` | tools | Checking the four-category docs standard and generating a wiki from docs/, so the docs stay the one source. | the-standard |
| Public Skill | `public-skill` | docs | The generated public copy of the author's skill, its plugin manifest and the copy bundled in the package. | skill-distribution, esoi-for-ai, the-steps |
| Records Core | `records-core` | core | Loading the configuration and the CSV records, and checking the intent records against the template. | intent-registry |
| Template Reader | `template-reader` | core | Reading the intent template from its source and keeping the parsed copy. | template-sync |
| Declarative Case Checks | `expectations` | core | The declarative check that case-driven evaluations share. | measurement-harness |
| Balanced Score | `balanced-score` | core | Folding accuracy, cost and time of a metric run into one score with written weights and budgets. | measurement-harness, leaderboard |
| Template Documents | `template-documents` | tools | Generating the non-code templates and excerpts from the template source. | template-sync |
| Rule Interface | `rule-interface` | tools | The rule interface: what a rule group is, what a rule sees, and the cache of module facts the rules share. | structure-check |
| Placement and Layering Rules | `rules-ownership` | tools | The placement and layering rules. | ownership-map, structure-check |
| Registry Rules | `rules-registry` | tools | The rules about the registry's own shape and the selection table. | structure-check, implementation-selection |
| Measurement Rules | `rules-measurement` | tools | The rules about measurement, provenance and discriminating cases. | structure-check, leaderboard |
| Generated File Rules | `rules-generated` | tools | The rules about generated files, the tracker and the records. | structure-check, review-tracker, template-sync, readable-records |
| Check Runner | `check-runner` | tools | Running every rule over a repository and reporting problems. | structure-check, readable-records |
| Run Harness | `harness` | tools | Running one implementation over a component's cases and recording the result. | measurement-harness |
| Solution Diagram Drawer | `diagram` | tools | Drawing each intent's solution diagram (Mermaid) from the solutions' outputs and the implementations' dependencies, and listing the diagrams out of date. | intent-registry, readable-records |
| Run Guards | `run-guards` | tools | Refusing an esoi run that cannot inform a decision: a perfect arm already caps it, a public result already exists, or the cases that failed last have not been rerun to a pass. | measurement-harness |
| Run Log | `run-log` | tools | Saving every run case by case, even a stopped one, and reading it back to rerun only the failing cases and to reuse cases an earlier stage already ran. | measurement-harness, leaderboard |
| Model Call Cassette | `cassette` | tools | Recording model calls in a plain JSONL cassette and replaying a call it already holds without calling the model, with replayed usage kept apart from real spend. | measurement-harness |
| Parent Selection Follower | `follow` | tools | Comparing a parent repository's current selections with this repository's lock and overrides and judging each change on this repository's own metric, as advice. | measurement-harness, assemble-by-name |
| Review Tracker Builder | `tracker` | tools | Building the review tracker tabs and syncing them with a sheet. | review-tracker |
| Integration Registry Check | `consumer` | tools | Checking a consuming repository's integration registry. | consumer-check |
| Public Hygiene Scan | `hygiene` | tools | Scanning a public repository for secrets and private data. | structure-check |
| Example Repository Scaffold | `scaffold` | tools | Writing the passing example repository that the init command produces. | structure-check |
| Command Line | `command-line` | cli | The esoi command, a thin call into the module that owns each behaviour. | structure-check, measurement-harness, leaderboard, review-tracker, consumer-check, template-sync, specify-from-code, promote-the-winner, implementation-selection |
| Python Tests | `python-tests` | tests | Offline tests that pin each module. | structure-check |
| Structure Check Cases | `eval-check-the-structure` | evaluation | Mutation cases for the whole check. | structure-check |
| File Ownership Cases | `eval-own-every-file` | evaluation | Mutation cases for placement and layering. | ownership-map |
| Intent Record Cases | `eval-record-intent` | evaluation | Mutation cases for the intent records. | intent-registry |
| Template Sync Cases | `eval-sync-the-template` | evaluation | Cases for reading the template. | template-sync |
| Harness Cases | `eval-measure-implementations` | evaluation | Cases for the harness. | measurement-harness |
| Leaderboard Cases | `eval-rank-implementations` | evaluation | Cases for the leaderboard. | leaderboard |
| Review Tracker Cases | `eval-review-tracker` | evaluation | Cases for the tracker. | review-tracker |
| Consumer Check Cases | `eval-check-a-consumer` | evaluation | Mutation cases for the consumer check. | consumer-check |
| Stale Result Cases | `eval-know-stale-results` | evaluation | Cases for telling a stale result from a current one. | when-metrics-are-run |
| Shared Evaluation Fixtures | `eval-shared` | evaluation | Fixtures shared by the evaluations, the results log and the per-case log. | structure-check, measurement-harness, consumer-check, when-metrics-are-run, esoi-for-ai, esoi-behaviour-judge, specify-from-code, readable-records, promote-the-winner |
| Python Packaging | `python-project` | project | Packaging, the implementation's readme and its reference documents. | structure-check |
| Continuous Integration Workflow | `ci` | project | The continuous integration workflow. | when-metrics-are-run |
| Skill Distribution | `skill-distribution` | tools | Generating, checking and installing the public copy of the author's skill. | skill-distribution |
| Skill Sync Cases | `eval-sync-the-skill` | evaluation | Cases for the sync, the drift check, leak detection and install. | skill-distribution |
| Intent Tree | `intent-tree` | core | Finding the intent folders of a repository and reading their records as one tree. | intent-registry |
| Parsed Source | `parsed-source` | core | Parsing each Python file once and walking each tree once per run for every reader of source. | intent-registry |
| Intent Migration | `intent-migration` | tools | Moving a legacy two-level repository to the intent layout without inventing a sub-intent. | intent-registry |
| Intent Rules | `rules-intents` | tools | The rules about intents as containers: the sub-intent link, the opportunity and ids across the tree. | structure-check |
| Local Index | `local-index` | tools | The local ESOI index: projects, their relations and where to look. | local-application-index |
| Local Index Cases | `eval-index-projects` | evaluation | Lookup cases over a small world of projects, the live index and the arms it is compared with. | local-application-index |
| Reply Grader | `behaviour` | tools | Grading an AI agent's reply against a behaviour case: the pattern check, the judge prompt and verdict, and a command provider. | esoi-for-ai, esoi-behaviour-judge |
| Behaviour Cases | `eval-behave-by-esoi` | evaluation | Cases, recorded replies and the arms for whether an agent acts by the principles. | esoi-for-ai |
| Judge Agreement Cases | `eval-judge-esoi-behaviour` | evaluation | Labelled replies and the arms for how far a judge agrees with them. | esoi-behaviour-judge |
| Code Declaration Reader | `declarations` | tools | Reading the declarations in the code, the drift rule S30 and the sync of the records. | specify-from-code |
| Technology Admission | `admit` | tools | Taking a newly found technology into the structure as an implementation with no arm yet, and recording a justified change to the specification. | specify-from-code, leaderboard |
| New Solution Command | `new-solution` | tools | Creating a whole solution with one command. | specify-from-code |
| README Renderer | `readme-renderer` | tools | The README of each intent folder, generated from its records. | readable-records |
| Winner Promotion | `promotion` | tools | Switching the selected implementation to the winner of the solution's own metric, or proposing it. | promote-the-winner |
| Specify from the Code Cases | `eval-specify-from-code` | evaluation | Cases for reading declarations, syncing the records and creating a solution. | specify-from-code |
| Readable Records Cases | `eval-readable-records` | evaluation | Cases for the generated README of an intent folder. | readable-records |
| Glanceable README Cases | `eval-readme-at-a-glance` | evaluation | Cases for the layouts of the README of an intent folder: one case per intent folder, scored by model-free glance checks. | readable-records |
| Navigable Records Cases | `eval-navigable-records` | evaluation | Cases for the layouts of a repository's records: one case per solution, scored by model-free navigation checks. | intent-registry |
| Promotion Cases | `eval-promote-the-winner` | evaluation | Cases for promoting the winner of a solution's metric. | promote-the-winner |
| Specification Index | `spec_index` | core | The spec index solution's interface and implementations. | spec-search |
| Specification Index Cases | `eval-spec_index` | evaluation | Cases and scorer for spec-index. | spec-search |
| Cascade Rules | `rules-cascade` | tools | The rules about cascading conditionals: the list can be read (S32) and the selection follows the cascade (S33). | structure-check, leaderboard |
| Hierarchy Rule | `rules-hierarchy` | tools | Rule S35: a child that overrides its parent's default cites a record of its own as the reason. | structure-check, assemble-by-name |
| Version Stamp | `versioning` | tools | The stamp of the skill and template the library follows, the template version, and recording it in a repository. | template-sync |
| Version Rule | `rules-versioning` | tools | The rule S34: the template version a repository records is the one the library carries. | template-sync, structure-check |
| Metric Record Keeper | `metric-record` | tools | Finding the slice of the specification a piece of work serves, reading its metric before and after with bounded meters, and keeping the rows in a ledger. | keep-metric-record |
| Metric Record Cases | `eval-keep-metric-record` | evaluation | Cases for the slice, milestone, meter reading, result, reconcile and iteration of a piece of work's metric record. | keep-metric-record |
| Circumstance Slicing | `circumstances` | core | Reading the circumstances that slice a run's results by a condition on cases or runs, and the variant names (base@key=value) that arms carry. | leaderboard, implementation-selection |
| Spec Search | `spec_search` | core | The spec search solution's interface and implementations. | spec-search |
| Spec Search Cases | `eval-spec_search` | evaluation | Cases and scorer for spec-search. | spec-search |
| Public Evidence Cases | `eval-public_evidence` | evaluation | Cases for grading evidence and for ranking candidates on one shared basis. | public-evidence |
| Choice Statistics | `stats` | core | Wilson interval, exact paired McNemar test and Holm correction for choosing by metric. | leaderboard |
| Evidence Table | `evidence-table` | tools | Markdown table of every evaluated solution's arms with intervals, verdicts and public evidence, written between markers. | leaderboard |
| One-Line Entry | `one-line-entry` | tools | One line for any solution or intent: run(id, input) through the declared interface, and its offline check. | implementation-selection, structure-check, apply-esoi |
| Standards Navigation | `standards-navigation` | tools | Showing an author only the standards whose risk tags and paths match the file in hand, checking a commit against them on the lines it adds, and measuring on past commits whether the standards shown for a task were the ones its work needed. | esoi-for-ai |
| Records Beside the Code | `beside-code-records` | tools | Records kept beside the code: where each record belongs, the moves that put it there or back, and the advisory rule S40. | intent-registry |
| Stale Result Rules | `staleness` | tools | Which changed files make a recorded result stale: the whole repository, the files the arm's component owns, or the files its module imports,  and the attestations that a change to the arm did not move what its result measures. | know-what-a-result-measures |
| Staleness Precision Cases | `eval-staleness-precision` | evaluation | A fixture of commits to a small repository, the hand-written verdict per component and the three rules. | know-what-a-result-measures |
| One-Criterion Rules | `rules-one-criterion` | tools | The advisory rules about a cascade running one criterion: stages that score several components (S41), separate leaderboards for one solution (S42), a selected baseline (S43) and balance weights changed after scoring (S44). | structure-check, leaderboard |
| Metric Foundation | `metric-foundation` | tools | A consumer's metric building on the metric of the library it depends on: reusing the foundation's recorded per-case results when the digests match, running the foundation's own scorer when they do not, composing one number at stated shares, and inheriting its cascade gates. | measurement-harness, leaderboard |
| Source Access | `source-access` | core | Metering, pricing and bounding what a request reads from source systems (records, bytes, calls, scopes, full scans) as cost and as gates a consumer may only tighten. | measurement-harness, leaderboard |
| Foundation Rule | `rules-foundation` | tools | The rule about a metric building on a foundation: a readable declaration, inherited stages that exist, and gates no looser than the foundation's (S47). | structure-check, measurement-harness |
| Wording Rules | `rules-wording` | tools | The advisory rules S51 and S52: a problem says what is true, and an ideal says the state that is wanted, not a solution. | structure-check |
| Selection Table Resolver | `selection` | core | Resolving an implementation of a solution from a selection table. | implementation-selection |
| Selection Cases | `eval-select-an-implementation` | evaluation | Cases for resolving a selection. | implementation-selection |
| Declarations and Cascade | `runtime` | core | Declarations in code and the cascade that picks the implementation a call runs. | implementation-selection |
| Dependency-Ordered Assembler | `assemble` | core | Building the parts of a program by validated name in dependency order, with the cascade that picks each implementation and a frozen result. | assemble-by-name |
| Hierarchical Defaults | `hierarchy` | core | Hierarchical defaults as plain data: the layers of one solution's cascade, conditional entries and the recorded reasons a child differs from its parent. | assemble-by-name |
| Assembly Cases | `eval-assemble-by-name` | evaluation | Cases for assembling by name: hostile names and snapshots, shadowing, cycles, unmet needs, concurrent assembles and the examples in the docs. | assemble-by-name |
| Selection Lock | `lock` | core | Pinning the selected implementations in a lock file, showing what a newer release would change and moving the lock on the consumer's schedule. | assemble-by-name |
| Interface of The Standard | `interface-the-standard` | tools | The Protocol declared with @solution for The Standard and its selected arm. | the-standard |
| Interface of The ESOI Steps | `interface-the-steps` | tools | The Protocol declared with @solution for The ESOI Steps and its selected arm. | the-steps |
| Interface of Skill Distribution | `interface-skill-distribution` | tools | The Protocol declared with @solution for Skill Distribution and its selected arm. | skill-distribution |
| Interface of Readable Records | `interface-readable-records` | tools | The Protocol declared with @solution for Readable Records and its selected arm. | readable-records |
| Interface of Review Tracker | `interface-review-tracker` | tools | The Protocol declared with @solution for Review Tracker and its selected arm. | review-tracker |
| Interface of Local ESOI Index | `interface-local-application-index` | tools | The Protocol declared with @solution for Local ESOI Index and its selected arm. | local-application-index |
| Interface of Intent Registry | `interface-intent-registry` | tools | The Protocol declared with @solution for Intent Registry and its selected arm. | intent-registry |
| Interface of Template Sync | `interface-template-sync` | tools | The Protocol declared with @solution for Template Sync and its selected arm. | template-sync |
| Interface of Specify from the Code | `interface-specify-from-code` | tools | The Protocol declared with @solution for Specify from the Code and its selected arm. | specify-from-code |
| Interface of Ownership Map | `interface-ownership-map` | tools | The Protocol declared with @solution for Ownership Map and its selected arm. | ownership-map |
| Interface of Structure Check | `interface-structure-check` | tools | The Protocol declared with @solution for Structure Check and its selected arm. | structure-check |
| Interface of Structure Budget | `interface-structure-budget` | tools | The Protocol declared with @solution for Structure Budget and its selected arm. | structure-budget |
| Interface of Measurement Harness | `interface-measurement-harness` | tools | The Protocol declared with @solution for Measurement Harness and its selected arm. | measurement-harness |
| Interface of Discriminating Cases | `interface-discriminating-cases` | tools | The Protocol declared with @solution for Discriminating Cases and its selected arm. | discriminating-cases |
| Interface of When Metrics Are Run | `interface-when-metrics-are-run` | tools | The Protocol declared with @solution for When Metrics Are Run and its selected arm. | when-metrics-are-run |
| Interface of Implementation Leaderboard | `interface-leaderboard` | tools | The Protocol declared with @solution for Implementation Leaderboard and its selected arm. | leaderboard |
| Interface of Promote the Winner | `interface-promote-the-winner` | tools | The Protocol declared with @solution for Promote the Winner and its selected arm. | promote-the-winner |
| Interface of Keep a Metric Record | `interface-keep-metric-record` | tools | The Protocol declared with @solution for Keep a Metric Record and its selected arm. | keep-metric-record |
| Interface of Implementation Selection | `interface-implementation-selection` | tools | The Protocol declared with @solution for Implementation Selection and its selected arm. | implementation-selection |
| Interface of Assemble Parts by Name | `interface-assemble-by-name` | tools | The Protocol declared with @solution for Assemble Parts by Name and its selected arm. | assemble-by-name |
| Interface of Consumer Check | `interface-consumer-check` | tools | The Protocol declared with @solution for Consumer Check and its selected arm. | consumer-check |
| Flow of Understanding | `flow-understanding` | tools | The interface of Understanding and its composition arm: the order in which it calls its parts. | esoi-understanding |
| Flow of Structure | `flow-structure` | tools | The interface of Structure and its composition arm: the order in which it calls its parts. | esoi-structure |
| Flow of Optimization | `flow-optimization` | tools | The interface of Optimization and its composition arm: the order in which it calls its parts. | esoi-optimization |
| Flow of Runtime | `flow-runtime` | tools | The interface of Runtime and its composition arm: the order in which it calls its parts. | esoi-runtime |
| Flow of Apply ESOI to a Project | `flow-root` | tools | The root's interface and its two arms: through the four containers, or documents only. | apply-esoi |
| Package Folders | `package-folders` | core | The empty __init__.py that makes each folder of the four containers a package. | apply-esoi |
| Library Adoption Reader | `library-adoption` | tools | Reading the adopts and specializes references of a repository and the library records they point at. | library-adoption |
| Interface of Library Adoption | `interface-library-adoption` | tools | The Protocol declared with @solution for Library Adoption and its selected arm. | library-adoption |
| Adoption Rule | `rules-adoption` | tools | The advisory rule S53: references resolve, an adopted row restates nothing, an own solution does not repeat a library solution, an arm declares the library solution id. | structure-check, library-adoption |
| Adopted Solutions Section | `readme-adopted` | tools | The part of an intent's README that links adopted solutions to the library's page. | readable-records, library-adoption |
| Structure Quality Scorer | `structure-quality` | tools | Reading a project's code and records, scoring seven dimensions of how well it divides the work, mining co-change from git history, and folding them into one balanced number with the worst offenders named. | structure-quality |
| Interface of Structure Quality | `interface-structure-quality` | tools | The Protocol declared with @solution for Structure Quality and its three arms. | structure-quality |
| Structure Quality Rules | `rules-structure-quality` | tools | The advisory rules S54 to S59, one per dimension of Structure Quality: scope, size, coupling, reuse, public surface and behavior preserved. | structure-check, structure-quality |
| Structure Quality Cases | `eval-score-structure-quality` | evaluation | Cases for the structure-quality scorer: small projects of generic incident shapes and clean exemplars, scored by what each arm flags and by comparison with the project cut into tiny files. | structure-quality |
