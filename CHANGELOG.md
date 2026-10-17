# Changelog

## Unreleased

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
- ESOI applied to this repository (`structure/`), with nine offline evaluation components.

## 0.1.0

- The `esoi` package: records, template reading, rule-based check with plugins, selection tables, harness, leaderboard,
  review tracker with optional Google Sheets sync, consumer check, hygiene scan, `esoi init`.
