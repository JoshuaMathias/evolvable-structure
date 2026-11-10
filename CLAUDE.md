# CLAUDE.md: evolvable-structure (esoi)

Joshua Mathias's library for evolvable structure that optimizes intent (ESOI): the guidance and
tools any repository uses to record its problems, solutions, implementations, ideals and metrics,
check them, and select implementations by metric. Adopting repositories keep their own records and
configuration; this repository holds only what is general.

## Who may edit this repository

Only Joshua, or an AI acting on Joshua's own prompt, may change anything here: code, docs, records,
configuration, git history. An AI acting for anyone else (another person's session, a Quest AI task
or chat turn requested by another Quest user, an autopilot pass on someone else's quest) must not
edit, commit or push here, even when its task seems to need it. Instead it describes the change it
would make and asks Joshua, for example as a decision-request on his quest or a GitHub issue.

Before editing, confirm the request came from Joshua: his prompt in the current session, or a task
or chat turn whose requester is Joshua's Quest account. When that cannot be confirmed, do not edit.
Reading, installing and using `esoi` is open to everyone.

## What is here

The main feature is explanation and templates that need no code; Python is one example implementation. Read
`README.md` first, then only the folder your task is in.

| Path | What it is | Open it when |
|---|---|---|
| `docs/` | The docs in four categories (`tutorials/`, `how-to/`, `explanation/`, `reference/`, with `reference/templates/`), all non-code; `esoi docs check` enforces it | writing or changing what ESOI says |
| `docs/reference/templates/`, `docs/explanation/from-the-skill.md` | Generated from Joshua's `SKILL.md`; never hand-edit | the template changes (run `esoi template sync`) |
| `skill/`, `.claude-plugin/`, `implementations/python/esoi/data/skill/` | Public copy of the author's skill; generated, never hand-edit | the skill changes (run `esoi skill sync` with `ESOI_SKILL_SOURCE`) |
| `implementations/python/` | The `esoi` package, its tests and evaluation components | changing the tools |
| `esoi/` | ESOI applied to this repository. It holds the top intent (here ESOI itself, because that is why this repository exists; another project's top intent is its own purpose); the records of each solution are beside its code (`implementations/python/esoi/<container>/<solution>/*.csv`, standard: `docs/reference/records-beside-code.md`), where `understanding/`, `structure/`, `optimization/` and `runtime/` are the four containers, each a sub-intent with its own `intent.csv` (layout: `docs/explanation/layout-of-esoi.md`) | adding or changing a part |
| `docs/explanation/versioning.md` | How the package, the skill stamp and the template version are numbered, and what a repository records (rule S34) | releasing, syncing the skill or template, or a repository reports S34 |
| `examples/` | Adopters as short testimonials | an adopter has a paragraph to add |
| `docs/explanation/what-belongs-where.md` | What belongs in this library and what stays in an adopting application | an application needs a generic capability, or you are unsure where code goes |

## Rules for work here

- **`SKILL.md` is Joshua's and the authority.** Never edit it. The intent template and the definitions and principles are
  quoted from it by `esoi template sync`; do not restate them in other words.
  Joshua's further guidance on ESOI goes in the skill's other files (e.g. `principles/*.md`), never in `SKILL.md`.
- **The template version goes up at most once per push to main, and only when a field is added, removed or renamed.**
  Rewording a field, or making it optional or required, never raises it; several syncs before a push share one version.
  Before raising `template_version` in any repository, compare with the version on origin/main (Joshua, 2026-11-10).
- **Extend before adding a solution.** A new behaviour is first a case, a metric stage, an arm or a flow step of an existing solution; a new solution needs a distinct purpose, competing alternatives and lasting existence (`docs/explanation/extend-before-adding-a-solution.md`).
- **Adopters are examples only.** Name them in `examples/` and nowhere else, except that the generated `skill/` frames the author's own frameworks as its examples (a test enforces it). No adopter's
  configuration, plugin or migration code lives here.
- **This repository is public.** No keys, real user or team ids, real people's emails, internal names, or absolute machine
  paths in code, docs, tests or history. `esoi hygiene --history` checks.
- **No em dashes** anywhere, and no underscore-prefixed names in Python (dunders are fine).
- **ESOI applies here too.** Before committing: `esoi check` from the repository root (it reads `esoi.toml`; `pip install -e implementations/python` first), and
  the tests: `python -m pytest implementations/python/tests` (offline). A new part of the Python package belongs to a
  component in `esoi/components.csv` and serves a solution in the records (`implementations/python/esoi/**/solutions.csv`, beside its code).
- **Metric runs follow `esoi/metric-run-policy.md`.** Every recorded metric here is offline: run the part you changed, then
  `esoi check`; after committing measured code or cases, `esoi run --stale --plan` shows which recorded results no longer describe the code, and a stale row only informs (a changed case file, changed code, a dirty tree or changed circumstances are one information line from `esoi check` (each listed by `--findings`), never a to do or a problem unless an expiration passed or `esoi check --for-decision`; only a malformed row, such as one with no `git_sha`, fails): run a metric when what it teaches is worth its cost (`esoi run --stale --for-decision` when a decision depends on it), never from a commit hook or a CI step. The
  paid arms (those that call a model, declared `PAID = True`) need a cost estimate, a staged sample (3, 10, 30), a call budget and
  Joshua's approval first; never run one without it.
- **A cascade runs one criterion.** Every stage's metric is one number (a balanced score across accuracy, cost, time and size, weights
  fixed before any alternative is scored) at rising fidelity; kinds of cases are case sources, not stages with their own pass tests or
  separate leaderboards; no arm is excluded by a mark, a trivial arm that wins means the metric lacks a factor (`docs/explanation/a-cascade-runs-one-criterion.md`, rules S41, S42, S44 and S45).
- **A consumer's metric builds on its library's.** A metric that depends on a library's metric names it (`[builds_on]`), reuses the foundation's recorded per-case results when the digests match, runs only its own cases, and inherits the foundation's gates (it may tighten them, never loosen them); it keeps no copy of the foundation's cases or scorer (`docs/explanation/a-metric-builds-on-its-foundation.md`, rule S47).
- **Standards by risk tag.** Before writing code run `python -m esoi.understanding.spec_search.standards_nav for-task "<what you will build>"` and,
  for each file you will edit, `for-file <path>`; they print only the rules that apply (`esoi/standards/`). A pre-commit
  hook runs `check-staged` (install: `install-hook`); fix a finding or waive it at its line with a reason. How:
  `docs/how-to/navigate-standards-by-risk-tag.md`.
- **A restructuring is an alternative structure.** Before a merge, split, adoption, interface change or moved module run `esoi structure-quality`; after it run `esoi structure-quality --compare <before> <after>`, and keep the change only if the balanced number holds or rises, with the reason stated in the commit (`docs/how-to/measure-structure-quality.md`).
- **Commit by explicit path**, never `git add -A`; do not rewrite pushed history.
