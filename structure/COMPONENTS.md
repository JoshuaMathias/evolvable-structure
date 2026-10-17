# Components

Generated from `structure/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Layer | Role | Serves |
|---|---|---|---|
| `records-core` | core | Loading the configuration and the CSV records, and checking the intent records against the template. | py-records-check |
| `template-reader` | core | Reading the intent template from its source and keeping the parsed copy. | py-template-reader |
| `selection` | core | Resolving an implementation of a solution from a selection table. | py-selector |
| `expectations` | core | The declarative check that case-driven evaluations share. | py-harness |
| `leaderboard` | core | Ranking implementations from the results log and calling a verdict. | py-leaderboard |
| `template-documents` | tools | Generating the non-code templates and excerpts from the template source. | py-template-reader |
| `rules-ownership` | tools | The rule interface and the placement and layering rules. | py-ownership-rules, py-check-runner |
| `rules-registry` | tools | The rules about the registry's own shape and the selection table. | py-check-runner, py-selector |
| `rules-measurement` | tools | The rules about measurement, provenance and discriminating cases. | py-check-runner, py-leaderboard |
| `rules-generated` | tools | The rules about generated files, the tracker and the records. | py-check-runner, py-tracker, py-template-reader |
| `check-runner` | tools | Running every rule over a repository and reporting problems. | py-check-runner |
| `harness` | tools | Running one implementation over a component's cases and recording the result. | py-harness |
| `tracker` | tools | Building the review tracker tabs and syncing them with a sheet. | py-tracker |
| `consumer` | tools | Checking a consuming repository's integration registry. | py-consumer-check |
| `hygiene` | tools | Scanning a public repository for secrets and private data. | py-check-runner |
| `scaffold` | tools | Writing the passing example repository that the init command produces. | py-check-runner |
| `command-line` | cli | The esoi command, a thin call into the module that owns each behaviour. | py-check-runner, py-harness, py-leaderboard, py-tracker, py-consumer-check, py-template-reader |
| `python-tests` | tests | Offline tests that pin each module. | py-check-runner |
| `eval-check-the-structure` | evaluation | Mutation cases for the whole check. | py-check-runner |
| `eval-own-every-file` | evaluation | Mutation cases for placement and layering. | py-ownership-rules |
| `eval-record-intent` | evaluation | Mutation cases for the intent records. | py-records-check |
| `eval-sync-the-template` | evaluation | Cases for reading the template. | py-template-reader |
| `eval-select-an-implementation` | evaluation | Cases for resolving a selection. | py-selector |
| `eval-measure-implementations` | evaluation | Cases for the harness. | py-harness |
| `eval-rank-implementations` | evaluation | Cases for the leaderboard. | py-leaderboard |
| `eval-review-tracker` | evaluation | Cases for the tracker. | py-tracker |
| `eval-check-a-consumer` | evaluation | Mutation cases for the consumer check. | py-consumer-check |
| `eval-know-stale-results` | evaluation | Cases for telling a stale result from a current one. | py-metric-run-policy |
| `eval-shared` | evaluation | Fixtures shared by the evaluations, and the results log. | py-check-runner, py-harness, py-consumer-check, py-metric-run-policy |
| `python-project` | project | Packaging, the implementation's readme and its reference documents. | py-check-runner |
| `documentation` | docs | Explanation, guides and non-code templates (the main feature of the repository). | docs-and-templates |
| `examples` | docs | Adopters as short examples and testimonials. | docs-and-templates |
| `structure-registry` | docs | This repository's own overall network and detailed records. | py-records-check |
| `project-files` | project | Files at the repository root: readme, configuration, contributing, licence. | docs-and-templates |
| `ci` | project | The continuous integration workflow. | py-metric-run-policy |
| `skill-distribution` | tools | Generating, checking and installing the public copy of the author's skill. | py-skill-distribution |
| `public-skill` | docs | The generated public copy of the author's skill, its plugin manifest and the copy bundled in the package. | py-skill-distribution |
| `eval-sync-the-skill` | evaluation | Cases for the sync, the drift check, leak detection and install. | py-skill-distribution |
