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
| `docs/` | Explanation, guides and templates, all non-code | writing or changing what ESOI says |
| `docs/templates/`, `docs/explanation/from-the-skill.md` | Generated from Joshua's `SKILL.md`; never hand-edit | the template changes (run `esoi template sync`) |
| `skill/`, `.claude-plugin/`, `implementations/python/esoi/data/skill/` | Public copy of the author's skill; generated, never hand-edit | the skill changes (run `esoi skill sync` with `ESOI_SKILL_SOURCE`) |
| `implementations/python/` | The `esoi` package, its tests and evaluation components | changing the tools |
| `esoi/` | ESOI applied to this repository. It holds the top intent (here ESOI itself, because that is why this repository exists; another project's top intent is its own purpose); `esoi-runtime/` is a sub-intent with its own `intent.csv`; its folder is named by its intent id | adding or changing a part |
| `examples/` | Adopters as short testimonials | an adopter has a paragraph to add |

## Rules for work here

- **`SKILL.md` is Joshua's and the authority.** Never edit it. The intent template and the definitions and principles are
  quoted from it by `esoi template sync`; do not restate them in other words.
- **Adopters are examples only.** Name them in `examples/` and nowhere else, except that the generated `skill/` frames the author's own frameworks as its examples (a test enforces it). No adopter's
  configuration, plugin or migration code lives here.
- **This repository is public.** No keys, real user or team ids, real people's emails, internal names, or absolute machine
  paths in code, docs, tests or history. `esoi hygiene --history` checks.
- **No em dashes** anywhere, and no underscore-prefixed names in Python (dunders are fine).
- **ESOI applies here too.** Before committing: `esoi check` from the repository root (it reads `esoi.toml`; `pip install -e implementations/python` first), and
  the tests: `python -m pytest implementations/python/tests` (offline). A new part of the Python package belongs to a
  component in `esoi/components.csv` and serves a solution in `esoi/solutions.csv`.
- **Metric runs follow `esoi/metric-run-policy.md`.** Every recorded metric here is offline: run the part you changed, then
  `esoi check`; after committing measured code or cases, `esoi run --stale` (it skips paid arms) and commit the results log. The
  paid arms (those that call a model, declared `PAID = True`) need a cost estimate, a staged sample (3, 10, 30), a call budget and
  Joshua's approval first; never run one without it.
- **Commit by explicit path**, never `git add -A`; do not rewrite pushed history.
