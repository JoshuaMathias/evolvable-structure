# Changelog

## Unreleased

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
