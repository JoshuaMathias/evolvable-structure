# Changelog

## Unreleased

- **Keep a metric's value before and after a piece of work: `esoi.spec_slice`, `esoi.metric_meter`, `esoi.metric_results`, `esoi.iteration`.** `RepoSliceSource` finds, with no model, the solution a request serves, its next milestone (neither met nor archived), its authoritative metric and the command that records it; `meters_from_names` and `read_value` read that metric in a bounded, announced reading (`recorded_row` while its row is current, `offline_arm` only for an arm that cannot spend money, run with zero model calls and a scrubbed environment you pass in); `MetricResult`, `FileMetricLedger` and `reconcile` keep measured, recorded and not-applicable rows without one overwriting another; `MetricIteration` wires them for one piece of work. Every setting is an argument and the library reads no environment. Also: `fields.parse_milestones(cell, in_order=True)` reads a numbered list only when it runs 1, 2, 3 from the start, and `harness.sample_label_args(row)` reads the run flags of a row's sample label without importing the repository's evaluation. See [Keep a metric's value before and after a piece of work](docs/guides/measure-before-and-after.md). Additive, so the next release is a minor bump.
- **See a difference by circumstance: `esoi.circumstances`, `esoi.variants`.** A `circumstances.csv` table names situations defined on something known before the work (a condition on case fields, `case_filter`, and a condition on the run, `run_filter`, such as its model or harness); the id is a name, and a condition that cannot be read, a field no case carries or a repeated id stops the run. `esoi run --record` appends a derived row per circumstance (`sample` = `slice:<id>`) and keeps a per-case log (`per_case.csv`, appended and compacted atomically, pruned of older cases) at no extra model call; editing the table makes the derived rows stale. `leaderboard.slice_verdicts` reads a slice as a proposal for a person: nothing is selected by it. An implementation name may be a variant, `name@key=value,...` (keys sorted, `true`/`false`/numbers read as such, recorded in the `impl` cell; an unknown key fails the arm once). Also fixed: the default verdict uses only rows that scored a whole run, so recording `esoi run --only` no longer decides it; a rival recorded only on named cases is reported as `not comparable: named cases only`; `esoi run --stale` judges the newest whole-run row. Routing by circumstance (`selections.csv`, a `facts=` layer) is designed and not built. See [Measure an implementation per circumstance](docs/guides/measure-per-circumstance.md) and, for what an adopter sees, [Versioning](docs/explanation/versioning.md). Additive apart from that verdict fix, so the next release is a minor bump.

See [Versioning](docs/explanation/versioning.md) for how a release is numbered and what each section names.

## 0.2.0

Skill source: `SKILL.md` at commit 4432aee (the working copy had uncommitted changes when it was synced; `esoi version` says so). Template version: 1.

- **Versions you can read and compare.** `esoi skill sync` and `esoi template sync` write a stamp of what they copied from into `implementations/python/esoi/data/skill_version.json` (the source's git commit, whether the source matched it, the date, a content hash of `SKILL.md`, and a hash of the shipped copy; no path or name). The template has a version: a whole number that grows by one each time its content changes, with the fields added, removed, made optional or required, or reworded since the version before. An adopting repository records the version its records follow with `esoi version --record` (`[records] template_version` in `esoi.toml`; `esoi init` writes it), and the new rule S34 reports a recorded version older than the library's, naming what changed and `esoi fields migrate` when it applies. A repository that records none is not failed: `esoi check` prints one note. `esoi version` prints the package version, the skill stamp and the template version. `esoi skill check` also finds a stale stamp. The package follows semantic versioning: see [Versioning](docs/explanation/versioning.md).

- **Depend on other solutions by name: `esoi.assemble`.** `Assembler(scope, package_dir, modules=(...), records=None)` gives a package name-based `register`, `resolve`, `names` and `choice` (a name must match `^[a-z0-9][a-z0-9_-]*$`, so no dots or colons; `modules` are the package's own modules that declare its solutions and arms and `prepare` imports them; a packaged arm's module must start with the scope and its file must lie inside the package folder, decided from the file's position and checked package by package before any import). Under an Assembler the records come from one explicit folder (`records`, never searched for upward) or the snapshot beside the package; the deployment table, selection table, `override()`, the process environment and `sys.path` are not touched, and load errors raise. It reads needs from constructor parameters typed with a solution's Protocol, builds the solutions in dependency order with `assemble(config, provided=...)` (a frozen result: `choice`, `implementation`, one reason line per solution), checks provided objects by the Protocol's member names, refuses to let `runtime.register(..., replace=True)` shadow a package's own arm at load, and fails at startup on a cycle or an unmet need, naming the chain. `problems`, `Assembler.uses_problems` and `Assembler.sync_uses` check and write `uses_solution_ids` from those needs and report an arm that cannot be imported as a finding. The metric is `esoi run assemble_by_name` (41 offline cases and a naive baseline) and the examples in the docs are run by a test. See [Assemble the parts of a program by name](docs/guides/assemble-by-name.md), [Depend on other solutions by name](docs/explanation/cross-dependency-by-name.md) and [What belongs where](docs/explanation/what-belongs-where.md). The records are unconfirmed prose for Joshua to confirm.
- **Cascading conditionals are code, not only a field.** A metric's `cascading_conditionals` cell is now an ordered list of stages, `name [sample=... | real=... | gate=... | min-pass-rate=... | max-age-days=... | when=...]` joined by ` > ` (`esoi.cascade.parse`). `esoi select --promote` follows the cascade when the solution's metric has one (the evidence it prints says so). `esoi cascade [SOLUTION] [--strict]` reports each implementation's result per stage (`not run` is a null, never an estimate), the implementation the cascade chooses (the highest result at the latest stage run, unless another scored higher at an earlier shared stage and has not been run at the latest one), expired results (measured code or cases changed, or older than `max-age-days`) and the next stage worth running with its `esoi run` line. Rule S32 checks that the list reads; S33 that the arm the metric's command names is the one the cascade chooses (waive as `<solution>`). The parser reads `Name (optional; a note): ...` as an optional field, and the bundled template copy now carries `cascading_conditionals` and the Measures of Success note.
- **Optional fields and met milestones (SKILL.md 83bb54d).** A field line written `Name (optional): ...` is optional: the parser strips the marker from the name and records `required` = `no` in `esoi_template.csv` (and the generated tables); the record-headers still list the column, and S26 (R1, R2) neither demands the column nor its text (`records.checked_fields`). Now optional: a solution's `out_of_scope`, `knowledge` and `tags`, an implementation's `dependencies`. Every solution states at least one milestone: the old allowance for an empty `milestones` cell is gone (R2). A milestone has a new sub-field Met, encoded inside the `milestones` cell as a marker ending the milestone's own text: `1. Share of greetings in the standard form: 100%. [met: 2026-10-26] 2. Next one.` (`[met]` when the date is unknown; no marker means not met). Use `esoi.fields.parse_milestones(cell)` and `esoi.fields.format_milestones(milestones)`; cells without markers parse as all unmet.
- **Solution and metric fields follow the author's SKILL.md (2026-10-26).** A solution's `scoped_purpose` is split into `description` (its unique value proposition), `purpose`, `approach` (its strategy statement) and `out_of_scope`; the flat `risk_addressed` column is gone, because each tag now carries the problem ids it mitigates. A metric's `scoped_purpose` is renamed `purpose`, and the new `disadvantages` says what the metric cannot see or could reward wrongly. An implementation's `dependencies` are its `uses_solution_ids` (no new column). Encoding: a solution's `tags` cell is a JSON array `[{"tag": "dedup", "risk_ids": ["R1"]}]`, the shape the JSON APIs use; consumers call `esoi.fields.parse_tags(cell)` and `esoi.fields.format_tags(tags)` and never parse it by hand (the older `;`-separated labels still parse, as tags with no risk ids). Deprecation path: records that still carry `scoped_purpose` keep loading (the old text is split on read, `esoi.fields.upgrade_row`), and `esoi check` reports the old column in R1 until `esoi fields migrate --apply` rewrites the records folders in place. The migration is mechanical and writes no wording: sentences that state exclusions ("avoids", "is not", "does not") move whole to `out_of_scope`, the rest stays as `purpose`; for a metric, only a sentence saying what it cannot see moves to `disadvantages`; `description`, `approach`, `tags` and a new `disadvantages` stay empty for the owner to write (R2 reports them).
- **A tool or an AI does not add specification fields on its own.** Rule S26 (R7) now fails when a records file has a column
  that is not a field of the template, not technical (an id or link ending `_id` or `_ids`, `filepath`, `command`,
  `interface_name`, `implementations`, `selected`, `sub_intent`, `implements`, `tracking_*`; the one list is
  `records.TECHNICAL_COLUMNS`) and not approved by the specification's owner in `esoi.toml` under `[records.approved_fields]`. The message
  says to propose the field to the person who owns the specification. The scaffold, `esoi records sync` and `esoi add` no
  longer write `selected_by`; `esoi select --promote` stores its evidence there only where the project approved the column,
  and prints it otherwise.
- **Every metric outputs a number, so there is no metric kind.** The solution columns `metric_kind` and `invariant_reason` are
  removed: a rule that holds or does not is measured as the pass rate on its cases, ranked like any other, and a solution
  with a single implementation keeps a deliberately naive baseline in `broken/` that its cases must fail (S25). A solution none
  of whose metrics has a command that records a run (`esoi run <component> --impl <name>`) is a specification, derived and never declared. When a solution has
  several metrics, the new link column `authoritative_metric_id` names the one that decides which implementation is best (R6).
  `gap` and `action` are removed too: a next step is a milestone (a value of a metric), and what a metric cannot see goes in
  the metric's `scoped_purpose`. A repository with the old columns gets an R1 finding that says where each one's content goes.
- **An empty `milestones` or `opportunities` is allowed.** `records.MAY_BE_EMPTY` names the two template fields a record may leave empty: a solution with no milestone has none its owner has chosen, and an intent need not state opportunities. Every other template field is still required (R2), and a sub-intent still states its opportunities (S28).
- **Three record columns renamed.** `solutions.csv` `port` is `interface_name`, `implementations.csv` `path` is `filepath` (components and waivers keep `path`), and `intent.csv` `opportunity` is `opportunities`, now a field of the Intent template for every intent (the top intent states its own). A repository with the old headers gets an R1 or S28 finding naming the new column, not a crash; there is no migration. The `port` keyword of a code declaration is unchanged.
- **A solution has Milestones, not Goals.** The solution column `goals` is now `milestones`: the solution's priorities in order, each a value of one or more metrics, with an optional end condition (when it stops being a priority and is archived) and an optional target time (a planned completion, which is not an end condition). The template parser attaches lines indented under a field to that field's question as guidance instead of reading them as new fields. Rule S22 lets `milestones` state target values. The implementation description asks how it achieves the purpose of its solution's definition. Standing conditions belong in `measures_of_success`; a constraint shared by many intents is specified once in its own intent, not as a milestone of each solution it limits. Existing records: rename the column and sort each cell.
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
