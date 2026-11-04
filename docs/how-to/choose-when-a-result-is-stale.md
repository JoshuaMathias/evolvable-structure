# Choose when a result is stale

A recorded result is stale when the code, cases or circumstances it measures changed. By default the library judges that by what
each arm measures, so a commit to one component leaves the results of the others current. The reasoning is in
[When metrics are run](../explanation/when-metrics-are-run.md#staleness-and-expiration); this page is how to use it.

## See why a row is stale

```bash
esoi stale --explain <component>     # per arm: the files changed since its commit that count, and the ones ignored, with their owners
esoi stale --count                   # how many rows each rule calls stale now
esoi run --stale --plan              # each row: current, measured code changed (and not re-run, with the reason), or would run
```

A reason names the file and who owns it, for example `pkg/util.py, imported by the arm`, or `pkg/beta.py, owned by component beta`
(ignored for an arm that does not measure it).

## Choose the rule

Set `staleness_rule` in `esoi.toml` to one of:

| Rule | A row is stale when | Use when |
|---|---|---|
| `repo_wide` | any file of `code_paths` or the evaluation folder changed | you want the safest and simplest rule, or the repository has no ownership map |
| `component_paths` | a file the arm's solution and implementation own in `components.csv` changed, or a file no component owns, or the component's evaluation folder or a shared fixture | the arms are not Python, or you can declare every shared dependency in the ownership map |
| `import_closure` | a file the arm's module imports (transitively, found by reading the source) changed, or the component's evaluation folder, or, for a changed file that is not Python, the `component_paths` test says so | the arms are Python modules inside the repository |

With no `staleness_rule`, the library uses the arm the repository's records select for the solution `know-what-a-result-measures`
if it has that solution, else the library default, `import_closure`, which is the arm the staleness precision metric selected.
Each rule falls back per arm to a safer one, so a result is never silently fresh: `import_closure` becomes `component_paths` for an arm
that is not Python or that imports a module by a computed name (the files the scan did find still count, beside the component's own),
and either becomes `repo_wide` for a component with no entry in the ownership map.

One limit to know: a module that an arm loads only by a name computed at run time, and that another component owns, is not seen by
either narrow rule. An arm that does this (a plugin loader, an implementation chosen from the records) is best served by
`staleness_rule = "repo_wide"` until the loader's targets are listed in the component that owns the arm.

## Make the narrow rules pay off

- Give every component of `components.csv` its path globs and its `solutions`, and keep each measured solution's implementation row's
  `filepath` current; the rules read nothing else.
- A file in the code paths that no component owns counts for every arm. Add it to a component to say whom it belongs to.
- A data file the code reads at run time (a prompt, a table) is not found by the import scan; it is judged by ownership, so list it in
  the component that reads it.
- Code the measurement depends on in a sibling repository still goes in `code_paths` (`../sibling/pkg`); it is judged by its own
  repository's commit, as before.

## What a stale row does

Nothing, until it is worth acting on. `esoi run --stale` reports it as measured code changed and re-runs only a selected arm that was
never measured, a selected arm whose declared expiration has passed, the selected arms a pending decision or release depends on
(`--for-decision`), or arms you name (`--include component/impl`). `--all` re-runs every stale arm. `esoi check` gives every staleness fact as
advice and never fails on it: a changed case file ("recorded on other cases"), changed measured code, a row recorded on uncommitted
code, circumstances changed since the slice rows were derived. Each line names the reason and the next action
(`esoi run <component> --impl <arm> --record` when a decision depends on it), and `esoi check --findings` lists them. So editing a case file
never blocks a move, a commit or the check. A malformed row stays a problem: one with no `git_sha` (it cannot say what it measured),
one with no `cases_sha` (S16), or an unreadable `circumstances.csv`. No commit hook and no CI step runs metrics.

## Measure the rules in your own repository

The staleness precision metric ships with the library: `esoi run staleness_precision --impl <repo_wide|component_paths|import_closure>`
builds a small git repository in a temporary folder with several components and a sequence of commits, and scores each rule against a
verdict written by hand per component and commit. A false-fresh decision (a kept result whose measured code changed) disqualifies the
rule; among the rest, fewer needless re-runs win. Add cases of your own to the library's fixture when a repository has a dependency the
fixture does not model.
