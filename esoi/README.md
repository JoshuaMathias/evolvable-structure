These are ESOI records (evolvable structure that optimizes intent): why this project exists, and its problems, solutions, implementations, ideals and metrics. This page is generated from the CSV files beside it by `esoi check --write-docs`; edit the CSV files, not this page.

# Evolvable structure that optimizes intent (ESOI)

Every intention is turned into a structure that optimizes the fulfilling of that intent while supporting changes to it, and the intent and the structure evolve together in a continual feedback loop.

## Problems

- `prob-intent-lost-between-person-and-code`: What someone meant when they asked for a capability lives in their head, a chat or a task, and the code that answers it carries none of that meaning. Months later nobody, human or AI, can tell what a module was for, which use cases it must serve, or what "better" would mean for it.
- `prob-best-alternative-unknown`: Most parts of a system can be done several ways (a model tier, a router, a retrieval method), and the one in use was chosen by whoever wrote it, not by evidence. When a better alternative appears, nothing shows that it is better or makes it the default.
- `prob-measurements-untrusted`: A number recorded on uncommitted code, on a different case set, typed by hand, or copied into prose that is never updated looks like evidence but proves nothing. Two numbers from different conditions get compared as if they were alike.
- `prob-switching-means-editing-code`: Switching a provider, runner or backend means finding and editing the call sites, often an `if` chain, and an embedding system cannot switch without forking.
- `prob-purposeless-oversized-code`: Files no one can attribute to a purpose stay because deleting feels risky, and modules grow until no one reads them whole (one adapter file reached thousands of lines).
- `prob-structure-rules-decay`: Rules written in prose (where files go, which way imports point, what must be documented) are followed by whoever read them and broken by the next agent, and generated documents drift from what they describe.
- `prob-review-needs-implementations`: A person who wants to steer quality has to read implementations, because ideals, metrics and current results are not gathered anywhere they can read and correct.
- `prob-evaluation-detached-from-shipped-code`: Evaluations built beside production code test copies, stubs or scripts of their own, so their results describe something that does not run.
- `prob-embedding-soundness-unknown`: A system builds on a library's solutions with its own stores and prompts, but cannot see which library solution each of its parts serves, whether its parts meet the library's own cases, or how far its pinned version lags.
- `prob-template-copies-drift`: The intent template is being refined in the skill, and every registry and checker that copied its fields falls out of date.
- `prob-others-cannot-adopt`: There is no worked, checked example of evolvable structure in code, so each team that wants it designs its own from prose.
- `prob-structure-costs-more-than-it-returns`: Every rule, record and check adds work to each change, and past a point contributors spend more time satisfying the structure than improving the code.
- `prob-metrics-run-at-the-wrong-time`: Results are stale when a choice depends on them, or paid runs happen with no decision behind them, so people either decide on numbers that no longer describe the code or stop running the metrics at all.
- `prob-skill-cannot-be-reached-safely`: A person who wants to use the author's skill cannot get it in a form that is both complete and safe to publish. The skill lives in a private folder next to material that is not public, so it cannot simply be shared; a copy made by hand starts to drift on the first edit; and a leaked name, path or internal process cannot be taken back once published.
- `prob-ai-behaviour-drifts-from-principles`: An AI agent asked to do work applies the principles inconsistently, and nothing shows how often. It builds a framework for a one-off fix, treats a task as a problem, merges use cases whose best differs into one function, drops the qualifier from a rule it restates, or pastes a fifth copy, and the instructions meant to prevent this (a skill, a system prompt) are edited with no measure showing whether the behaviour got better or worse.
- `prob-no-order-to-follow`: People who want to apply ESOI have the five record types and the principles but no order to follow. They do not know what to do first, write implementations before deciding what best means, trust a metric nobody checked, skip the perspectives that would find gaps, and stop after the first build instead of looping back.
- `prob-applied-structure-is-rediscovered`: Where ESOI is already applied, how those projects relate and where to look in each is rediscovered in every session.
- `prob-behaviour-verdicts-uncalibrated`: A model that grades whether a reply acts by the principles can disagree with the people whose intent the principles express, can favour its own phrasing when it wrote the reply, and can pass a reply that uses the right words while doing the opposite. Nothing shows by how much, so a score built on its verdicts looks like evidence but may measure the judge.
- `prob-records-copy-the-code`: The records repeat what the code already says: which alternatives of a solution exist, the file each lives in, and an interface's signature. Each repeated fact is kept in step by hand, or by a check that only reports the drift, so adding an alternative means editing the code and several records, and the two drift apart.
- `prob-winner-not-adopted`: A rival that clearly beats the selected implementation on the solution's own metric stays unadopted until someone notices and edits the selection, the metric's command and the record of why, by hand.
- `prob-records-unreadable-at-a-glance`: An intent's folder of CSV files states it completely, but what the intent is for cannot be seen without opening several files and following ids between them.
- `prob-simulated-arm-false-loss`: An arm that meters a deterministic stand-in for a model counts the calls a real model would make but spends nothing. It is recorded with an unknown model and cost, so the harness skips it as paid and the ranking rates a free baseline cheaper than a cost that is merely unknown, reporting a loss that is not real.
- `prob-selection-default-kept-twice`: The default implementation of a solution is written in the selection table and again in the records, and only a check holds the two equal. Choosing a winner means editing both, and a mismatch fails the build.
- `prob-swappable-needs-ceremony`: Making a part swappable takes a port class, a table entry with an import path for every alternative, a wrapper file to measure each one, and edits wherever the choice is made, so most parts are never made swappable.
- `prob-rules-unjustified`: A rule is kept in code with no record of the mistake that justified it or of what it has caught since, so nobody can tell whether it still earns its place or why its limit has its value.
- `prob-intent-specs-not-found-for-new-input`: A new use case or input arrives, and nobody (human or AI) can tell which of a project's problems, ideals, solutions, implementations and metrics apply without reading all of them. The specifications exist, but finding the relevant few is left to whoever happens to remember them.
- `prob-metric-measures-a-stand-in`: A metric scores a scripted judge, a mocked model or a canned answer instead of the real thing, so its number measures the plumbing around the thing and not the thing. A perfect scripted judge passes everything, and a decision built on the number is backed by nothing.

## Ideals

- `ideal-explicit-intent`, Explicit intent: Every built part traces to the problems it addresses and the ideals it pursues.
- `ideal-metric-chosen-defaults`, Metric-chosen defaults: The implementation that runs is the one the solution's authoritative metric ranks best.
- `ideal-trustworthy-evidence`, Trustworthy evidence: Every number can be reproduced from a commit and a case set, and only like is compared with like.
- `ideal-effortless-substitution`, Effortless substitution: Switching the implementation of a solution is a change of data, not of code.
- `ideal-purposeful-code`, Purposeful code: Nothing exists that serves no solution, and every part is small enough to understand in one reading.
- `ideal-self-enforcing-structure`, Self-enforcing structure: A structural rule is enforced by the structure, at the moment it is broken.
- `ideal-review-by-metric`, Review by metric: People can steer by reviewing problems, ideals, metrics and results alone, without needing to read implementations; anyone may still review or improve an implementation, and that still adds value.
- `ideal-faithful-measurement`, Faithful measurement: What is measured is what ships.
- `ideal-sound-integration`, Sound integration: A system built on a library meets the same standard as the library, through the library's own checks and cases.
- `ideal-living-template`, Living template: The template's author changes it in one place and every record follows.
- `ideal-adoptable-structure`, Adoptable structure: Another team can apply the same structure to its own code by following one standard and reusing this library's tools.
- `ideal-proportionate-structure`, Proportionate structure: The structure costs less than it returns, and a small change carries a small cost.
- `ideal-timely-affordable-evidence`, Timely affordable evidence: Every choice between alternatives is backed by a current result, and what it cost to get was proportionate to the choice and approved.
- `ideal-installable-skill`, Installable skill: A stranger gets the author's current skill, complete and public-safe, in one step, while the author keeps one source of truth.
- `ideal-principled-behaviour`, Principled behaviour: An AI agent acts by the principles in its own work, including holding back where structure costs more than it returns, and keeps every qualifier when it restates one.
- `ideal-followable-process`, Followable process: Anyone applying ESOI can follow one stated order from purpose to selection by metric, sized to the work, and knows where to return when something changes.
- `ideal-found-structure`, Found structure: Structure that already exists is found and reused instead of rediscovered.
- `ideal-calibrated-judging`, Calibrated judging: A judge's verdicts agree with the human verdicts they stand in for, and where they disagree is known.
- `ideal-declared-once`, Declared once: Each fact is stated once, where it belongs, and everything else is derived from it or measured; a second copy held in step by a check is upkeep, not structure.
- `ideal-readable-intent`, Readable intent: Anyone opening an intent's folder learns what it is for, and what it contains, from a page the records themselves produce.
- `ideal-rules-earn-their-place`, Rules earn their place: Every rule can say which mistake it prevents, and is removed when it stops catching any.
- `ideal-right-spec-at-the-right-time`, Right specification at the right time: For any new use case or input, the relevant specifications are found by looking at a small, cheap description first and reading in full only what was chosen.

## Solutions

| Solution | Name | Selected | Metric |
|---|---|---|---|
| `apply-esoi` | Apply ESOI to a project | documents-templates-and-tools | Adoption effort |
| `intent-registry` | Intent registry | csv-records-in-the-repository | Record completeness |
| `template-sync` | Template sync | template-parser | Template agreement |
| `ownership-map` | Ownership map | component-rows | Trace completeness |
| `implementation-selection` | Implementation selection | declarations | Resolution correctness |
| `measurement-harness` | Measurement harness | component-harness | Provenance completeness |
| `leaderboard` | Leaderboard | margin-leaderboard | Ranking correctness |
| `discriminating-cases` | Discriminating cases | broken-baselines | Case discrimination |
| `structure-check` | Rule engine | rule-script | Check dependability |
| `structure-rules` | Structure rules | rule-modules | Violation detection |
| `review-tracker` | Review tracker | tracker-and-sheet | Review coverage |
| `consumer-check` | Consumer check | consumer-command | Consumer soundness |
| `the-standard` | The standard | standard-document | Adoption effort |
| `structure-budget` | Structure budget | written-weighing-rule | Structure cost against catches |
| `when-metrics-are-run` | When metrics are run | on-every-change | Decisions backed by current results |
| `skill-distribution` | Skill distribution | generated-public-copy | Skill copy agreement and leaks |
| `esoi-for-ai` | ESOI applied to AI behaviour | skill-as-standing-instructions | Behaviour adherence |
| `the-steps` | The ESOI steps | esoi-steps | Steps followed |
| `docs-and-templates` | Documentation and templates | docs/README.md | Newcomer effort |
| `follow-the-steps` | Follow the steps | skill/evolvable-structure/steps.md | Steps trial |
| `local-application-index` | Local ESOI index | implementations/python/evaluation/components/index_projects/impls/live_index.py | Local index lookup cases |
| `esoi-behaviour-judge` | ESOI behaviour judge | model-judge-on-the-rubric | Judge agreement |
| `behave-by-esoi` | Behave by ESOI | implementations/python/evaluation/components/behave_by_esoi/impls/standing_instructions.py | ESOI behaviour cases |
| `judge-esoi-behaviour` | Judge ESOI behaviour | implementations/python/evaluation/components/judge_esoi_behaviour/impls/model_judge.py | ESOI judge agreement cases |
| `specify-from-code` | Specify from the code | declarations-and-sync | Declaration sync |
| `readable-records` | Readable records | generated-readme | README fidelity |
| `promote-the-winner` | Promote the winner | margin-promotion | Promotion correctness |
| `spec-index` | Specification index | weighted-tfidf | Specification recall at k |

## Implementations

| Implementation | Name | Where | Sub-intent |
|---|---|---|---|
| `apply-esoi:documents-templates-and-tools` | Documents, templates and tools together |  |  |
| `apply-esoi:documents-only` | Documents only, applied by hand |  |  |
| `intent-registry:csv-records-in-the-repository` | CSV records in the repository | implementations/python/esoi/records.py |  |
| `intent-registry:records-beside-the-code` | Records beside the code |  |  |
| `intent-registry:sheet-as-source` | Sheet as source |  |  |
| `template-sync:template-parser` | Template parser | implementations/python/esoi/template.py |  |
| `template-sync:hand-kept-field-list` | Hand-kept field list |  |  |
| `ownership-map:component-rows` | Component rows | implementations/python/esoi/rules/layout.py |  |
| `implementation-selection:declarations` | Declarations in code |  | [esoi-runtime](esoi-runtime/README.md) |
| `implementation-selection:entry-point-plugins` | Entry-point plugins |  |  |
| `measurement-harness:component-harness` | Component harness | implementations/python/esoi/harness.py |  |
| `measurement-harness:external-eval-platform` | External eval platform |  |  |
| `leaderboard:margin-leaderboard` | Margin leaderboard | implementations/python/esoi/leaderboard.py |  |
| `discriminating-cases:broken-baselines` | Broken baselines |  |  |
| `structure-check:rule-script` | Rule script | implementations/python/esoi/check.py |  |
| `structure-rules:rule-modules` | Numbered rule modules | implementations/python/esoi/rules/__init__.py |  |
| `structure-rules:prose-rules` | Rules in prose |  |  |
| `review-tracker:tracker-and-sheet` | Tracker and sheet | implementations/python/esoi/tracker.py |  |
| `consumer-check:consumer-command` | Consumer command | implementations/python/esoi/consumer.py |  |
| `the-standard:standard-document` | Standard document |  |  |
| `when-metrics-are-run:on-every-change` | On every change | .github/workflows/check.yml |  |
| `when-metrics-are-run:on-a-schedule` | On a schedule |  |  |
| `when-metrics-are-run:on-a-decision` | On a decision |  |  |
| `when-metrics-are-run:on-drift` | On drift |  |  |
| `skill-distribution:generated-public-copy` | Generated public copy | implementations/python/esoi/skill.py |  |
| `skill-distribution:hand-copied-folder` | Hand-copied folder |  |  |
| `skill-distribution:publish-the-private-folder` | Publish the private folder |  |  |
| `structure-budget:written-weighing-rule` | Written weighing rule |  |  |
| `structure-budget:measured-cost-and-catches` | Measured cost and catches |  |  |
| `esoi-for-ai:skill-as-standing-instructions` | Skill as standing instructions |  |  |
| `esoi-for-ai:skill-on-request` | Skill on request |  |  |
| `esoi-for-ai:no-skill` | No skill |  |  |
| `esoi-for-ai:perspective-review` | Perspective review |  |  |
| `the-steps:esoi-steps` | The ESOI steps |  |  |
| `the-steps:board-checklist` | Project Documentation board checklist |  |  |
| `the-steps:one-hour-pass` | One-hour first pass |  |  |
| `the-steps:no-stated-order` | No stated order |  |  |
| `docs-and-templates:README.md` | Documentation folder | docs/README.md |  |
| `follow-the-steps:steps` | The ESOI steps | skill/evolvable-structure/steps.md |  |
| `follow-the-steps:one-hour-pass` | One-hour first pass | docs/guides/apply-by-hand.md |  |
| `local-application-index:live_index` | Index folder in the user's home | implementations/python/evaluation/components/index_projects/impls/live_index.py |  |
| `local-application-index:skill_rows` | Routing rows in the skill's index (retired baseline) | implementations/python/evaluation/components/index_projects/impls/skill_rows.py |  |
| `local-application-index:records_only` | Nothing beyond each project's own records (floor) | implementations/python/evaluation/components/index_projects/impls/records_only.py |  |
| `esoi-behaviour-judge:model-judge-on-the-rubric` | Model judge on the rubric |  |  |
| `esoi-behaviour-judge:regex-checks-only` | Regex checks only |  |  |
| `esoi-behaviour-judge:human-review-of-every-reply` | Human review of every reply |  |  |
| `behave-by-esoi:standing-instructions` | Skill as standing instructions | implementations/python/evaluation/components/behave_by_esoi/impls/standing_instructions.py |  |
| `behave-by-esoi:skill-on-request` | Skill on request | implementations/python/evaluation/components/behave_by_esoi/impls/skill_on_request.py |  |
| `behave-by-esoi:no-skill` | No skill | implementations/python/evaluation/components/behave_by_esoi/impls/no_skill.py |  |
| `judge-esoi-behaviour:model-judge` | Model judge | implementations/python/evaluation/components/judge_esoi_behaviour/impls/model_judge.py |  |
| `judge-esoi-behaviour:regex-only` | Regex only | implementations/python/evaluation/components/judge_esoi_behaviour/impls/regex_only.py |  |
| `specify-from-code:declarations-and-sync` | Declarations read from the code, rows synced | implementations/python/esoi/declarations.py |  |
| `specify-from-code:hand-kept-records` | Records kept by hand |  |  |
| `readable-records:generated-readme` | Generated README per intent folder | implementations/python/esoi/readme.py |  |
| `readable-records:hand-written-readme` | README written by hand |  |  |
| `promote-the-winner:margin-promotion` | Promotion on the leaderboard's verdict | implementations/python/esoi/promote.py |  |
| `promote-the-winner:person-edits-the-records` | A person edits the records |  |  |
| `spec-index:weighted-tfidf` | Field-weighted TF-IDF over the index | implementations/python/esoi/spec_index.py |  |
| `spec-index:term-overlap` | Plain term overlap | implementations/python/esoi/spec_index.py |  |

## Metrics

- `metric-trace-completeness`, Trace completeness: `esoi run own_every_file --impl live_checker`
- `metric-template-agreement`, Template agreement: `esoi run sync_the_template --impl live_parser`
- `metric-resolution-correctness`, Resolution correctness: `none`
- `metric-provenance-completeness`, Provenance completeness: `esoi run measure_implementations --impl live_harness`
- `metric-ranking-correctness`, Ranking correctness: `esoi run rank_implementations --impl live_leaderboard`
- `metric-case-discrimination`, Case discrimination: `none`
- `metric-violation-detection`, Violation detection: `esoi run check_the_structure --impl live_checker`
- `metric-check-dependability`, Check dependability: `esoi run check_the_structure --impl live_checker`
- `metric-review-coverage`, Review coverage: `esoi run review_tracker --impl live_tracker`
- `metric-consumer-soundness`, Consumer soundness: `esoi run check_a_consumer --impl live_consumer_check`
- `metric-adoption-effort`, Adoption effort: `none`
- `metric-structure-cost-against-catches`, Structure cost against catches: `none`
- `metric-decisions-backed-by-current-results`, Decisions backed by current results: `esoi run know_stale_results --impl live_checker`
- `metric-skill-copy-agreement`, Skill copy agreement and leaks: `esoi run sync_the_skill --impl live_skill`
- `metric-esoi-behaviour-adherence`, Behaviour adherence: `none`
- `metric-steps-followed`, Steps followed: `none`
- `metric-docs-and-templates`, Newcomer effort: `none`
- `metric-follow-the-steps`, Steps trial: `none`
- `metric-local-index-lookup`, Local index lookup cases: `esoi run index_projects --impl live_index; esoi run index_projects --impl skill_rows; esoi run index_projects --impl records_only`
- `metric-esoi-judge-agreement`, Judge agreement: `none`
- `metric-behave-by-esoi`, ESOI behaviour cases: `esoi run behave_by_esoi --impl standing_instructions`
- `metric-judge-esoi-behaviour`, ESOI judge agreement cases: `esoi run judge_esoi_behaviour --impl model_judge`
- `metric-record-completeness`, Record completeness: `esoi run record_intent --impl live_checker`
- `metric-declaration-sync`, Declaration sync: `esoi run specify_from_code --impl live_declarations`
- `metric-readme-fidelity`, README fidelity: `esoi run readable_records --impl live_readme`
- `metric-promotion-correctness`, Promotion correctness: `esoi run promote_the_winner --impl live_promote`
- `metric-spec-index-recall`, Specification recall at k: `esoi run spec_index --impl weighted_tfidf; esoi run spec_index --impl term_overlap`
