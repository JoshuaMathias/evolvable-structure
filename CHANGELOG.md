# Changelog

## Unreleased

- **Rule S31: a metric must be meaningfully real.** `esoi check` reports an implementation in a metric's evaluation folder that
  declares `SIMULATED = True`, and a metric record that calls its judge or model scripted, simulated, mocked, stubbed, fake, canned
  or a stand-in; a waiver names why a metric cannot be real. Documented in `docs/explanation/metrics-must-be-real.md`. The
  `spec_index` cases were strengthened with longer, noisier requests, two-record requests and requests that concern nothing, so
  the two implementations no longer pass nearly the same cases.
- **Specification index.** `esoi spec index|find|show` and `esoi.spec_index`: a deterministic, non-AI JSON map of the records (stable
  ids, tier-0 and tier-1 descriptions, two-way links, weighted terms, document frequencies, digests) for finding the few
  specifications a new use case needs. Solution `spec-index`, metric `metric-spec-index-recall`. No vectors or models here: a
  system on top adds them. See `docs/explanation/finding-specifications.md`.

Graceful declarations (declare once where the code is; derive or check the rest). See `docs/explanation/graceful-selection.md`
and the migration steps in `docs/guides/migrate-to-intents.md`:

- **Scopes, older variables and installed packages.** Two packages in one process may declare the same solution id: a
  declaration belongs to its package, and `resolve(id, scope="pkg")` reaches that package's alone (scoped variable
  `ESOI_SELECT_<SCOPE>_<ID>` first). A scope also tells the lookup where to start before anything is imported, and the
  folders around a package installed into `site-packages` are not searched for records (it reads its snapshot). `selection_env`
  in `esoi.toml` keeps an older environment variable working, named in the error. An unknown solution lists the solutions that
  have implementations; `explain` returns where each name came from. `register(..., replace=True)` lets a consumer put its own
  implementation under a name a package declares, whichever is imported first.
- **Gentle default folder.** When `structure_dir` is not set and `esoi/` does not exist, a previous default (`docs/structure`,
  `structure`) that holds records is used, with one note suggesting `git mv docs/structure esoi`. Two folders holding records
  are never guessed between: the error names both. The same resolution serves `esoi projects` and the consumer check.
- **Declare in code.** `@solution("id")` on an interface and `@implementation("id", "name")` on each alternative (or
  `register(...)` for another package's class). Calling the interface runs the selected implementation; `using="name"` picks
  one for a call, `with override(...)` for a block, `ESOI_SELECT_<ID>` for a process, `[selection]` in `esoi.toml` for a
  deployment, and the solution's `selected` in the records is the project default. Unknown names fail with the choices and the
  layer that named them. The selection table and `Selector` remain the lower layer, and their names join the declared ones.
- **One copy of the default.** A table entry may omit `default`; the records' `selected` is used (`Selector.from_config`). Rule
  S23 compares only a table that still holds its own default. `esoi select --snapshot` writes the defaults for a package
  shipped without the records.
- **Records follow the code.** `esoi records sync` writes the solution and implementation rows the code declares and the records
  lack, never over text a person wrote; rule S30 reports the drift. `esoi new solution <id>` writes the records, a code skeleton
  with the decorators and an evaluation folder. The harness runs a declared implementation without an `impls/` wrapper.
- **Promote the winner.** `esoi select --promote` switches `selected`, the metric's command and the evidence in `selected_by`
  when a rival clearly wins on the solution's own metric and the solution's `promotion` cell is `automatic`, otherwise prints the
  exact proposal. It never acts on unverified, incomparable or stale rows.
- **Readable records.** `esoi check --write-docs` writes a `README.md` in each intent folder from its records; rule S8 keeps
  it current.
- **Simulated arms.** An arm that meters a deterministic stand-in for a model declares `SIMULATED = True`: its runs record
  model `simulated` and cost 0.0, `esoi run --stale` does not treat it as paid, and the leaderboard compares it on model calls
  instead of calling a known $0 baseline cheaper than an unknown cost (the false LOSS).
- `esoi init` writes the example declared in code.

Intents are the containers and the unit of hierarchy (from the author's updated SKILL.md):

- **Default folder `esoi/`.** A new project's specifications live in `esoi/` (the one constant `DEFAULT_STRUCTURE_DIR`); the name
  matches `esoi.toml`, `~/.esoi` and the skill. `structure/` and `docs/structure/` keep working when `structure_dir` names them.
  This repository's own `structure/` is now `esoi/`.

- The intent template now has the **Intent** itself (name, vision statement) as its own item, parsed beside the five
  specification templates; `esoi template sync` writes `docs/templates/intent.md`, an `intent.csv` header and the new
  definitions and principle bullets verbatim.
- **Layout.** An intent is a folder with an `intent.csv` and the five record files. The configured folder holds a project's
  **top intent**, which is why that project exists, in its own words (a product's is about the product, not ESOI; in this repository it is
  ESOI because that is why it exists). The evolvable structure a project applies is a **solution inside** its top intent, whose
  implementation may use esoi's solutions. A **sub-intent** is a subfolder with its own `intent.csv`; it arises as an
  implementation of a solution in its parent (`implements`, and `sub_intent` on that implementation) and states the
  `opportunity` that justifies it. `implementations.csv` gains `sub_intent` and `uses_solution_ids` (`@project_id/solution_id`
  for another project's solution). Ids are unique across the tree and links resolve anywhere in it. The folder default is one
  constant (`DEFAULT_STRUCTURE_DIR`).
- **Rules** S28 (intent folders and the sub-intent link) and S29 (ids across the tree, `uses_solution_ids`); S26 checks the
  records of every intent as one set, reports the retired `overall_solution_ids`, and a solution with
  `metric_kind` `specification` (defined, with alternatives, not yet measured by a run) needs no interface fields or metric command.
- **Legacy.** The two-level `overall` layout loads and passes as before, with one note pointing at
  `docs/guides/migrate-to-intents.md`. `esoi intent migrate [--apply]` moves the overall records into the top intent and
  turns `overall_solution_ids` into `uses_solution_ids`; it leaves the top intent's name and vision for the project to
  write and never invents a sub-intent.
- `esoi init` writes the intent layout: a top intent with its name and vision left empty (the check reports them until the
  project fills them), a starter `project-structure` solution that uses esoi, and no sub-intent.
- **Local ESOI index.** `esoi projects init|add|list|check|index|where` keeps `projects.csv` and a generated `INDEX.md` in
  `$ESOI_HOME` (else `~/.esoi`): which projects ESOI is applied to, how they relate and where to look first. No network calls.
  This repository records it as the `local-application-index` solution with a measured live implementation, the retired
  baseline of routing rows in a skill index, and the floor of each project's own records.
- This repository's own `structure/` is converted: top intent `esoi` with one sub-intent, `esoi-runtime` (the package as a
  runtime dependency of other people's code; its opportunity is marked unconfirmed). The earlier `esoi-python` and
  `esoi-for-ai-behaviour` sub-intents are folded back: their opportunities were not opportunities (the first mirrored top
  solutions one to one, the second repeated the goals and metric of `esoi-for-ai`).
- **Corrections after review.** A sub-intent's folder must be named by its intent id (S28). `esoi init` also writes a
  `project-purpose` top solution, left empty for the project, whose implementation builds on the project's other solutions;
  the structure is a solution inside the top intent, not the top. `esoi projects` reads a project's name and vision statement
  from its top `intent.csv` (the index cells are overrides for a project without one), reports a row that disagrees, derives
  `used-by` from other rows' `uses`, resolves `add .`, no longer guesses a name from legacy records, and reads
  `[tool.esoi]` in `pyproject.toml`. `esoi intent migrate` reports an overall solution with no implementation instead of
  dropping the dependency. The tracker folder name is configurable (`tracker_folder`) and never read as an intent.

Fixes from an adopter report (a verdict that compared different samples):

- The leaderboard compares arms only on the same cases and sample: the same `cases_sha`, the same new `sample` column (blank for
  the full set, `sample:N`, `only:ids`) and the same case count, so a log without the column still tells a 40-case run from a
  1,137-case one. Each rival is compared with the selected arm on the newest run both have; a rival with none is not compared
  (UNMEASURED, with the mismatch named) and `--strict` fails on it (`esoi leaderboard`, rule S20). Before, a 10-point gap between
  a full run and a 40-case sample was called WIN.
- `esoi run --stale` re-runs an arm on the sample its latest row used, and a rival on the selected arm's sample; `--full` runs the
  whole set. A rival on another sample is "not comparable", not stale.

Fixes from three adopter migrations:

- A registry file that lacks a column the rules read (`port`, `gap`, `role` ...) is reported, not a crash; the record header
  template now carries `port`.
- Several implementations may live in one module: rule S14 also accepts a module listed by the `path` of an `implementations.csv`
  record, and records are matched to a solution's `implementations` cell by id, `solution:name` or path.
- A verdict that rests on a rival recorded before the measured code changed is flagged (S20 in strict mode, `esoi leaderboard`);
  `esoi run --stale` re-runs those rivals too, and skips arms that spend money unless asked (`--include`, `--include-paid`,
  `paid_arms`, `PAID = True`).
- `code_paths` may point into a sibling repository; its commit is recorded per row in `code_shas`.
- Rule S3 can be waived per file (`root_python_allow`, or a waiver by path).
- The tracker lists a metric that serves several solutions once (no false S18), and the S18 message no longer blames file names.
- `esoi hygiene` works outside a git checkout and takes your own secret patterns (`[hygiene.patterns]`).
- `cost_usd` is computed from a `prices` table when the provider reports none, and left blank when the price is unknown.
- A waiver for a finding only `--strict` reports is no longer called unused outside strict mode.
- Plugin results remembered by `ctx.memo` are dropped when the configuration or a structure file changes.
- Clear messages instead of tracebacks: a malformed `esoi.toml`, an unknown `--impl`, `--only` that matches nothing, `--sample 0`,
  `esoi select` and `esoi consumer check` mistakes; a CSV with a byte-order mark is read; one malformed results line no longer stops
  the board.

- The author's `evolvable-structure` skill as a complete public folder (`skill/evolvable-structure/`), installable as a Claude Code
  plugin (`.claude-plugin/marketplace.json`), by downloading the folder, or with `esoi skill install`. It is generated from the
  author's own skill by `esoi skill sync`, and `esoi skill check` fails on a stale copy or a leak. See
  [docs/guides/install-the-skill.md](docs/guides/install-the-skill.md).
- When metrics are run: an explanation, a fill-in template and this repository's own policy; records link a policy solution to the
  metrics it governs (`governs_metric_ids`, `run_policy_ids`).
- `esoi check --strict` also calls a result stale when the measured code changed since its commit; `esoi run --stale` re-runs
  and records what is stale.
- Faster check: one parse per module, cached on disk (`.esoi_cache/`, `cache = false` to turn off), cold modules scanned in
  parallel, and `ctx.memo` for plugins; on a repository of about 1,200 files the check took about 3 seconds before, and takes about 1 second cold and under half a second warm.
- A continuous integration workflow for this repository.
- Documentation first: explanation, guides and non-code templates in `docs/`, generated from the author's `SKILL.md`.
- The Python implementation moved to `implementations/python/` and installs from that subfolder.
- Records can link up to an overall solution network (`parent_problem_ids`, `parent_ideal_ids`, `overall_solution_ids`,
  `parent_metric_ids`), and a detailed solution may take its problem and ideal from its parents.
- `esoi template sync` also writes the per-type templates, the record headers, the review sheet layout and the quoted
  excerpts.
- ESOI applied to this repository (`structure/`), with ten offline evaluation components.

## 0.1.0

- The `esoi` package: records, template reading, rule-based check with plugins, selection tables, harness, leaderboard,
  review tracker with optional Google Sheets sync, consumer check, hygiene scan, `esoi init`.
