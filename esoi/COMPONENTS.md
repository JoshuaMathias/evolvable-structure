# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Handle | Layer | Role | Serves |
|---|---|---|---|---|
| Documentation | `documentation` | docs | Explanation, guides and non-code templates (the main feature of the repository). | docs-and-templates, follow-the-steps |
| Examples | `examples` | docs | Adopters as short examples and testimonials. | docs-and-templates |
| Structure registry | `structure-registry` | docs | This repository's own overall network and detailed records. | intent-registry |
| Project files | `project-files` | project | Files at the repository root: readme, configuration, contributing, licence. | docs-and-templates |
| Wiki | `wiki` | scripts | A thin wrapper that generates this repository's GitHub wiki from docs/ through esoi docs wiki. | docs-and-templates |
| Docs standard | `docs-standard` | tools | Checking the four-category docs standard and generating a wiki from docs/, so the docs stay the one source. | docs-and-templates |
| Public skill | `public-skill` | docs | The generated public copy of the author's skill, its plugin manifest and the copy bundled in the package. | skill-distribution, behave-by-esoi, follow-the-steps |
| Records core | `records-core` | core | Loading the configuration and the CSV records, and checking the intent records against the template. | intent-registry |
| Template reader | `template-reader` | core | Reading the intent template from its source and keeping the parsed copy. | template-sync |
| Expectations | `expectations` | core | The declarative check that case-driven evaluations share. | measurement-harness |
| Leaderboard | `leaderboard` | core | Ranking implementations from the results log and calling a verdict. | leaderboard |
| Balanced score | `balanced-score` | core | Folding accuracy, cost and time of a metric run into one score with written weights and budgets. | measurement-harness, leaderboard |
| Template documents | `template-documents` | tools | Generating the non-code templates and excerpts from the template source. | template-sync |
| Rule interface | `rule-interface` | tools | The rule interface: what a rule group is, what a rule sees, and the cache of module facts the rules share. | structure-check |
| Rules ownership | `rules-ownership` | tools | The placement and layering rules. | ownership-map, structure-rules |
| Rules registry | `rules-registry` | tools | The rules about the registry's own shape and the selection table. | structure-rules, runtime-selection |
| Rules measurement | `rules-measurement` | tools | The rules about measurement, provenance and discriminating cases. | structure-rules, leaderboard |
| Rules generated | `rules-generated` | tools | The rules about generated files, the tracker and the records. | structure-rules, review-tracker, template-sync, readable-records |
| Check runner | `check-runner` | tools | Running every rule over a repository and reporting problems. | structure-check, readable-records |
| Harness | `harness` | tools | Running one implementation over a component's cases and recording the result. | measurement-harness |
| Diagram | `diagram` | tools | Drawing each intent's solution diagram (Mermaid) from the solutions' outputs and the implementations' dependencies, and listing the diagrams out of date. | intent-registry, readable-records |
| Run guards | `run-guards` | tools | Refusing an esoi run that cannot inform a decision: a perfect arm already caps it, a public result already exists, or the cases that failed last have not been rerun to a pass. | measurement-harness |
| Run log | `run-log` | tools | Saving every run case by case, even a stopped one, and reading it back to rerun only the failing cases and to reuse cases an earlier stage already ran. | measurement-harness, leaderboard |
| Cassette | `cassette` | tools | Recording model calls in a plain JSONL cassette and replaying a call it already holds without calling the model, with replayed usage kept apart from real spend. | measurement-harness |
| Follow | `follow` | tools | Comparing a parent repository's current selections with this repository's lock and overrides and judging each change on this repository's own metric, as advice. | measurement-harness, assemble-by-name |
| Tracker | `tracker` | tools | Building the review tracker tabs and syncing them with a sheet. | review-tracker |
| Consumer | `consumer` | tools | Checking a consuming repository's integration registry. | consumer-check |
| Hygiene | `hygiene` | tools | Scanning a public repository for secrets and private data. | structure-check |
| Scaffold | `scaffold` | tools | Writing the passing example repository that the init command produces. | structure-check |
| Command line | `command-line` | cli | The esoi command, a thin call into the module that owns each behaviour. | structure-check, measurement-harness, leaderboard, review-tracker, consumer-check, template-sync, specify-from-code, promote-the-winner, runtime-selection |
| Python tests | `python-tests` | tests | Offline tests that pin each module. | structure-check, structure-rules |
| Eval check the structure | `eval-check-the-structure` | evaluation | Mutation cases for the whole check. | structure-check, structure-rules |
| Eval own every file | `eval-own-every-file` | evaluation | Mutation cases for placement and layering. | ownership-map |
| Eval record intent | `eval-record-intent` | evaluation | Mutation cases for the intent records. | intent-registry |
| Eval sync the template | `eval-sync-the-template` | evaluation | Cases for reading the template. | template-sync |
| Eval measure implementations | `eval-measure-implementations` | evaluation | Cases for the harness. | measurement-harness |
| Eval rank implementations | `eval-rank-implementations` | evaluation | Cases for the leaderboard. | leaderboard |
| Eval review tracker | `eval-review-tracker` | evaluation | Cases for the tracker. | review-tracker |
| Eval check a consumer | `eval-check-a-consumer` | evaluation | Mutation cases for the consumer check. | consumer-check |
| Eval know stale results | `eval-know-stale-results` | evaluation | Cases for telling a stale result from a current one. | when-metrics-are-run |
| Eval shared | `eval-shared` | evaluation | Fixtures shared by the evaluations, the results log and the per-case log. | structure-check, measurement-harness, consumer-check, when-metrics-are-run, behave-by-esoi, judge-esoi-behaviour, specify-from-code, readable-records, promote-the-winner |
| Python project | `python-project` | project | Packaging, the implementation's readme and its reference documents. | structure-check |
| Ci | `ci` | project | The continuous integration workflow. | when-metrics-are-run |
| Skill distribution | `skill-distribution` | tools | Generating, checking and installing the public copy of the author's skill. | skill-distribution |
| Eval sync the skill | `eval-sync-the-skill` | evaluation | Cases for the sync, the drift check, leak detection and install. | skill-distribution |
| Intent tree | `intent-tree` | core | Finding the intent folders of a repository and reading their records as one tree. | intent-registry |
| Intent migration | `intent-migration` | tools | Moving a legacy two-level repository to the intent layout without inventing a sub-intent. | intent-registry |
| Rules intents | `rules-intents` | tools | The rules about intents as containers: the sub-intent link, the opportunity and ids across the tree. | structure-rules |
| Local index | `local-index` | tools | The local ESOI index: projects, their relations and where to look. | local-application-index |
| Eval index projects | `eval-index-projects` | evaluation | Lookup cases over a small world of projects, the live index and the arms it is compared with. | local-application-index |
| Behaviour | `behaviour` | tools | Grading an AI agent's reply against a behaviour case: the pattern check, the judge prompt and verdict, and a command provider. | behave-by-esoi, judge-esoi-behaviour |
| Eval behave by esoi | `eval-behave-by-esoi` | evaluation | Cases, recorded replies and the arms for whether an agent acts by the principles. | behave-by-esoi |
| Eval judge esoi behaviour | `eval-judge-esoi-behaviour` | evaluation | Labelled replies and the arms for how far a judge agrees with them. | judge-esoi-behaviour |
| Declarations | `declarations` | tools | Reading the declarations in the code, the drift rule S30 and the sync of the records. | specify-from-code |
| Admit | `admit` | tools | Taking a newly found technology into the structure as an implementation with no arm yet, and recording a justified change to the specification. | specify-from-code, leaderboard |
| New solution | `new-solution` | tools | Creating a whole solution with one command. | specify-from-code |
| Readme renderer | `readme-renderer` | tools | The README of each intent folder, generated from its records. | readable-records |
| Promotion | `promotion` | tools | Switching the selected implementation to the winner of the solution's own metric, or proposing it. | promote-the-winner |
| Eval specify from code | `eval-specify-from-code` | evaluation | Cases for reading declarations, syncing the records and creating a solution. | specify-from-code |
| Eval readable records | `eval-readable-records` | evaluation | Cases for the generated README of an intent folder. | readable-records |
| Eval readme at a glance | `eval-readme-at-a-glance` | evaluation | Cases for the layouts of the README of an intent folder: one case per intent folder, scored by model-free glance checks. | readable-records |
| Eval navigable records | `eval-navigable-records` | evaluation | Cases for the layouts of a repository's records: one case per solution, scored by model-free navigation checks. | intent-registry |
| Eval promote the winner | `eval-promote-the-winner` | evaluation | Cases for promoting the winner of a solution's metric. | promote-the-winner |
| Spec index | `spec_index` | core | The spec index solution's interface and implementations. | spec-index |
| Eval spec index | `eval-spec_index` | evaluation | Cases and scorer for spec-index. | spec-index |
| Cascade | `cascade` | tools | Reading a metric's cascading conditionals, checking their order against the skill's expectations, settling when results expire (stage, metric, project default), choosing the implementation by the latest stage run, expiry of results and the next stage to run. | leaderboard, promote-the-winner |
| Rules cascade | `rules-cascade` | tools | The rules about cascading conditionals: the list can be read (S32) and the selection follows the cascade (S33). | structure-rules, leaderboard |
| Rules hierarchy | `rules-hierarchy` | tools | Rule S35: a child that overrides its parent's default cites a record of its own as the reason. | structure-rules, assemble-by-name |
| Versioning | `versioning` | tools | The stamp of the skill and template the library follows, the template version, and recording it in a repository. | template-sync |
| Rules versioning | `rules-versioning` | tools | The rule S34: the template version a repository records is the one the library carries. | template-sync, structure-rules |
| Metric record | `metric-record` | tools | Finding the slice of the specification a piece of work serves, reading its metric before and after with bounded meters, and keeping the rows in a ledger. | keep-metric-record |
| Eval keep metric record | `eval-keep-metric-record` | evaluation | Cases for the slice, milestone, meter reading, result, reconcile and iteration of a piece of work's metric record. | keep-metric-record |
| Circumstances | `circumstances` | core | Reading the circumstances that slice a run's results by a condition on cases or runs, and the variant names (base@key=value) that arms carry. | leaderboard, runtime-selection |
| Spec search | `spec_search` | core | The spec search solution's interface and implementations. | spec-search |
| Eval spec search | `eval-spec_search` | evaluation | Cases and scorer for spec-search. | spec-search |
| Evidence | `evidence` | tools | Grading public evidence from a CSV of reported numbers: a letter per candidate and dimension, flags, a ranking and whether an own run is needed, with no model call. | public-evidence |
| Eval public evidence | `eval-public_evidence` | evaluation | Cases for grading evidence and for ranking candidates on one shared basis. | public-evidence |
| Stats | `stats` | core | Wilson interval, exact paired McNemar test and Holm correction for choosing by metric. | leaderboard |
| Evidence table | `evidence-table` | tools | Markdown table of every evaluated solution's arms with intervals, verdicts and public evidence, written between markers. | leaderboard |
| One line entry | `one-line-entry` | tools | One line for any solution or intent: run(id, input) through the declared interface, and its offline check. | implementation-selection, structure-check, apply-esoi |
| Standards navigation | `standards-navigation` | tools | Showing an author only the standards whose risk tags and paths match the file in hand, and checking a commit against them on the lines it adds. | esoi-for-ai |
| Beside code records | `beside-code-records` | tools | Records kept beside the code: where each record belongs, the moves that put it there or back, and the advisory rule S40. | intent-registry |
| Staleness | `staleness` | tools | Which changed files make a recorded result stale: the whole repository, the files the arm's component owns, or the files its module imports,  and the attestations that a change to the arm did not move what its result measures. | know-what-a-result-measures |
| Eval staleness precision | `eval-staleness-precision` | evaluation | A fixture of commits to a small repository, the hand-written verdict per component and the three rules. | know-what-a-result-measures |
| Rules one criterion | `rules-one-criterion` | tools | The advisory rules about a cascade running one criterion: stages that score several components (S41), separate leaderboards for one solution (S42), a selected baseline (S43) and balance weights changed after scoring (S44). | structure-rules, leaderboard |
| Metric foundation | `metric-foundation` | core | A consumer's metric building on the metric of the library it depends on: reusing the foundation's recorded per-case results when the digests match, running the foundation's own scorer when they do not, composing one number at stated shares, and inheriting its cascade gates. | measurement-harness, leaderboard |
| Source access | `source-access` | core | Metering, pricing and bounding what a request reads from source systems (records, bytes, calls, scopes, full scans) as cost and as gates a consumer may only tighten. | measurement-harness, leaderboard |
| Rules foundation | `rules-foundation` | tools | The rule about a metric building on a foundation: a readable declaration, inherited stages that exist, and gates no looser than the foundation's (S47). | structure-rules, measurement-harness |
| selection | `selection` | core | Resolving an implementation of a solution from a selection table. | runtime-selection |
| eval-select-an-implementation | `eval-select-an-implementation` | evaluation | Cases for resolving a selection. | runtime-selection |
| runtime | `runtime` | core | Declarations in code and the cascade that picks the implementation a call runs. | runtime-selection |
| assemble | `assemble` | core | Building the parts of a program by validated name in dependency order, with the cascade that picks each implementation and a frozen result. | assemble-by-name |
| requirements | `requirements` | core | Declaring what an implementation needs from its environment and checking it. | assemble-by-name |
| hierarchy | `hierarchy` | core | Hierarchical defaults as plain data: the layers of one solution's cascade, conditional entries and the recorded reasons a child differs from its parent. | assemble-by-name |
| eval-assemble-by-name | `eval-assemble-by-name` | evaluation | Cases for assembling by name: hostile names and snapshots, shadowing, cycles, unmet needs, concurrent assembles and the examples in the docs. | assemble-by-name |
| lock | `lock` | core | Pinning the selected implementations in a lock file, showing what a newer release would change and moving the lock on the consumer's schedule. | assemble-by-name |
