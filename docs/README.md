# ESOI: Evolvable Structure that Optimizes Intent

ESOI is a way to make sure what you intend actually happens, and keeps getting better. You put your intent into words
as a few short kinds of record (the problem, the ideal you want, the solution, the ways of doing it, and how to measure
them), try more than one way, and let a measurement pick the best. The structure stays steady while the ways of doing
things improve, and it changes with you when your intent does.

It works for anything with an intent and more than one way to serve it: a product, code, a course, a coaching program,
a team process, a personal schedule.

## Tutorials

Learn by doing; each one ends with something working.

- [Assemble a solution and get its environment ready](tutorials/get-an-assembly-ready.md): declare what an arm needs, see what
  is missing, generate the `.env` template and the install script.

## How-to guides

Steps for a task you already know you want to do.

- [Apply ESOI by hand](how-to/apply-by-hand.md): a first pass in about an hour, with no tools.
- [Apply ESOI with the Python tools](how-to/apply-with-tools.md)
- [Measure structure quality](how-to/measure-structure-quality.md): `esoi structure-quality` at stage one and two, comparing two structures, how to read the report, the rules S54 to S59, and tightening budgets.
- [Migrate to intents](how-to/migrate-to-intents.md): from the two-level overall layout.
- [Migrate from esoi 0.3 to 0.4](how-to/migrate-from-0.x.md): the public API, the commands and where every module went.
- [Install the skill](how-to/install-the-skill.md): give an AI agent the principles.
- [Search records and items together](how-to/search-specs-and-items.md)
- [Use public evidence](how-to/use-public-evidence.md)
- [Declare a solution's interface and call it with one function](how-to/declare-a-solutions-interface.md): kind, entry, example, `run(id, input)`, the outcomes, the opt-in checks.
- [Assemble the parts of a program by name](how-to/assemble-by-name.md): resolve, build in dependency order, fail early.
- [Adopt a solution from a library](how-to/adopt-a-solution-from-a-library.md): refer to a library's solution instead of copying its records (rule S53).
- [Declare what an implementation needs from its environment](how-to/declare-environment-needs.md): variables, API keys, packages, binaries, services; generate the `.env` template and install script.
- [Install only what your solutions need](how-to/install-only-what-you-need.md): the closure, the plan, the resolution ladder, coherence in CI.
- [Build on another package's defaults and say why you differ](how-to/hierarchical-defaults.md): a parent's defaults, one `explain`, reasons for each override, rule S35.
- [Pin selections for production and update on your schedule](how-to/pin-selections-for-production.md): when pip pinning is enough, when a lock helps, `esoi lock` and its diff.
- [Follow a parent repository's selections](how-to/follow-a-parent-repositorys-selections.md): `esoi follow` judges the parent's current arm on your own metric and says whether to adopt, keep or drop an override.
- [Iterate on an LLM arm without repeating model calls](how-to/iterate-on-an-llm-arm-without-repeating-model-calls.md): record model calls in a cassette, replay unchanged prompts for free, prove a variant costs nothing with `--cassette-only`.
- [Keep a consumer current with an AI agent](how-to/keep-a-consumer-current-with-an-ai-agent.md): run `esoi lock --status` on a schedule, resolve blockers, apply, verify.
- [Keep a metric's value before and after a piece of work](how-to/measure-before-and-after.md): find the slice of the specification, read the metric twice, keep the rows.
- [Fit public benchmarks into one generic metric](how-to/fit-public-benchmarks-into-one-generic-metric.md): define the metric by what matters, add one adapter per benchmark, fix each share before scoring, reuse public results for public arms.
- [Write a cascade that stays one number](how-to/write-a-cascade-that-stays-one-number.md): one balanced score at every stage, kinds of cases as case sources, floors marked, then `esoi check --findings`.
- [Measure an implementation per circumstance](how-to/measure-per-circumstance.md): circumstances, variants, slice rows, and how to read a slice verdict as a proposal.
- [Keep records beside the code](how-to/keep-records-beside-the-code.md): put each solution's records in the folder that holds its code, with a generated README in each.
- [Generate the README of every intent folder](how-to/generate-intent-readmes.md): write a page per intent folder that shows what it is, how its parts fit and where to go next.
- [Write problems and ideals that hold up](how-to/write-problems-and-ideals-that-hold-up.md): a problem true today in plain words, an ideal as the state you want and not a solution; rules S51 and S52.
- [Admit a technology that does not fit the structure](how-to/admit-a-technology-that-does-not-fit.md): the decision steps, what a specification change may touch, three worked examples, `esoi admit`.
- [Generate the wiki from the docs](how-to/generate-the-wiki.md): check the four categories and publish a wiki that cannot drift.

## Explanation

Why it is built this way. Start with the idea, then the pieces.

- [What ESOI is](explanation/what-is-esoi.md): the idea in five minutes.
- [The ESOI steps](../skill/evolvable-structure/steps.md): what to do, in order, from your purpose to choosing by a
  measurement.
- [The order of building with structure](explanation/the-order-of-building.md): hierarchy and visions, then interfaces with the paragraph, diagram, metrics, which implementations to build, implementing, running metrics, and the loop of improvement.
- [Extend before adding a solution](explanation/extend-before-adding-a-solution.md): cases, metric stages, arms and flow steps first; the three-part test for a genuinely missing solution.
- [Intents and the five specification types](explanation/intent-types.md): an intent as the container; problems, ideals,
  solutions, implementations and metrics.
- [How the records connect](explanation/how-they-connect.md)
- [A problem says what is true; an ideal says the state you want](explanation/a-problem-says-what-is-true.md): no overstated absolutes or strawmen in problems; absolutes belong in ideals, which describe a state, never a means.
- [Intents and sub-intents](explanation/intents-and-sub-intents.md): the hierarchy, and the legacy two-level layout.
- [When to create a sub-intent](explanation/when-to-create-a-sub-intent.md)
- [Why a new technology needs a decision, not a slot](explanation/admitting-a-technology.md): what differs, in which of how, judged by, where it sits and what is wanted, and why a change is recorded.
- [The local ESOI index](explanation/local-index.md): where ESOI is applied on a machine.
- [Finding the specifications a new use case needs](explanation/finding-specifications.md): the specification index, tiers, and what a system on top adds.
- [One search for records and items, written once](explanation/one-search-for-records-and-items.md): the stages around the index, with the vector search and judge supplied by the caller.
- [Judge public evidence like a scientist](explanation/judge-public-evidence-like-a-scientist.md): other people's evals are complementary; one is never enough, a vendor number is a claim.
- [Choosing by metric](explanation/choosing-by-metric.md)
- [What a metric includes](explanation/what-a-metric-includes.md): the checklist (outcome, cost, time, risk gates, robustness, abstention, freshness, evidence quality, checkable cascade, fixed weights) with nine examples, and three ways to lean on other metrics.
- [A metric must be meaningfully real](explanation/metrics-must-be-real.md): no scripted stand-ins; creative and limited measures are fine, fake ones are not (rule S31).
- [Code quality is structure quality](explanation/code-quality-is-structure-quality.md): scope, size, coupling, reuse, flow, surface and behavior as one balanced number, why a shared kernel is not coupling, the gaming moves tested, the history it was checked against, and what the number cannot tell a reviewer (rules S54 to S59).
- [A cascade runs one criterion](explanation/a-cascade-runs-one-criterion.md): every stage's metric is one number, kinds of cases are case sources, floors are marked (rules S41 to S44).
- [The first stage needs no model](explanation/first-stage-needs-no-model.md): start a metric's cascade with a free stage that proves the scorer.
- [Declare, call, measure, promote](explanation/graceful-selection.md): the graceful way to declare alternatives in code and let the metric pick.
- [When metrics are run](explanation/when-metrics-are-run.md): when to run each metric and who approves the spend.
- [Depend on other solutions by name](explanation/cross-dependency-by-name.md): why one solution needs another by name, not by import.
- [Declare environment needs beside the arm](explanation/environment-needs.md): why an arm states its variables, API keys and packages, and how assembly reports them.
- [Override only what differs, and say why](explanation/override-only-what-differs.md): why defaults are hierarchical and an override cites its own records.
- [Adopting solutions from a library](explanation/adopting-solutions-from-a-library.md): adopted, specialized and own solutions, and why an application refers to a library's jobs instead of copying them.
- [What belongs in the library and what stays in an application](explanation/what-belongs-where.md): the test, with a table.
- [Versioning](explanation/versioning.md): the package version, the skill and template stamp, and the template version a repository records (rule S34).
- [Where each part of esoi lives](explanation/layout-of-esoi.md): the four containers, the rule for a solution folder, and where each old module went.
- [Applying ESOI beyond code](explanation/beyond-code.md)
- [ESOI applied to AI behaviour](explanation/esoi-for-ai.md)
- [The definitions and principles, in Joshua Mathias's words](explanation/from-the-skill.md)
- [Where the template came from](explanation/project-documentation-board.md)
- [Related frameworks and designs](explanation/related-work.md)

## Reference

Facts to look up.

- [Requirements: every kind, its fields, and the commands](reference/requirements.md): includes `esoi install`.
- [The lock: file, API, command line and exit codes](reference/lock.md): `esoi lock`, `esoi.runtime.implementation_selection.lock`, the status plan.
- [Scope the role of a solution](how-to/scope-the-role-of-a-solution.md): purpose, exclusions and who owns them, delegation, the change driver of a container; rules S48 and S49.
- [A solution holds alternatives of one job](explanation/a-solution-holds-alternatives-of-one-job.md): read the implementation list for purpose and specificity; split by purpose.
- [Start from the flow](how-to/start-from-the-flow.md): write the flow the coherence paragraph describes, in the medium of the implementation, then what it reaches; rule S50.
- [Names and ids](reference/names-and-ids.md): the name leads every generated output, the id is the handle; rule S46.
- [`esoi attest`](reference/attest.md): a recorded, reasoned attestation that an arm's changed code did not move its result.
- [Component documents](reference/component-documents.md): the `documents` column of components.csv, whose document a file is, rule S1 for it.
- [Records beside the code](reference/records-beside-code.md): the layout, the folder kinds, where each record lives, what is generated and what is measured.
- [The README of an intent folder](reference/intent-readme.md): the layout every generated page follows, and how it is measured.
- [Docs commands](reference/docs-commands.md): `esoi docs check` and `esoi docs wiki`.
- [All templates](reference/templates/README.md): what each one is for.
- [Problem](reference/templates/problem.md), [Ideal](reference/templates/ideal.md), [Solution](reference/templates/solution.md),
  [Implementation](reference/templates/implementation.md) and [Metric](reference/templates/metric.md)
- [Intent](reference/templates/intent.md)
- [Repository standard](reference/templates/repository-standard.md)
- [Review sheet layout](reference/templates/review-sheet.md)
- [Metric run policy](reference/templates/metric-run-policy.md)

## About these pages

The author's own words (the definitions, the principles and the intent template) are quoted from the
evolvable-structure skill's `SKILL.md` and regenerated whenever it changes, in
[the definitions and principles](explanation/from-the-skill.md) and [the templates](reference/templates/README.md). To change a
question, change `SKILL.md`, then run `esoi template sync`. The repository's wiki is generated from this folder, so
edit pages here, not on the wiki. Every page sits in exactly one of the four folders (tutorials, how-to, explanation, reference),
following the Diataxis framework; `esoi docs check` enforces it.
