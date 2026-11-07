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
| `import_closure` | the arm's own code changed: its implementation module (the wrapper in `impls/` and the file its record names) or helper code it imports (transitively, found by reading the source) that belongs to no implementation and that no other implementation imports. A helper imported by two or more arms stales none of them. Never a test or shared fixture, the scorer or datasets, a package `__init__`, or another implementation's file, even if imported. For a changed file that is not Python, the `component_paths` test says so | the arms are Python modules inside the repository |

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
(`--for-decision`), or arms you name (`--include component/impl`). `--all` re-runs every stale arm. `esoi check` never fails on a staleness fact
(a changed case file, "recorded on other cases"; changed measured code; a row recorded on uncommitted code; circumstances changed since
the slice rows were derived). Whether one is a to do depends on the situation:

| Situation | What `esoi check` prints |
|---|---|
| The result's metric (or the project's `[expiration] default`) declares an expiration and it has passed | a to do (`S20 ...: its metric declares an expiration of N days ...`), even when the code is unchanged |
| A decision or release depends on the results and you say so with `esoi check --for-decision` | a to do for each stale selected result, naming the re-run command |
| Anything else (the default: expiration is never) | one line outside the to-do count, such as `info: 21 recorded result(s) describe older code; esoi run --stale --plan lists them` |

`esoi check --findings` and `--strict` list every stale result in full under that line, each with its reason and the next action
(`esoi run <component> --impl <arm> --record` when a decision depends on it). So editing a case file
never blocks a move, a commit or the check. A malformed row stays a problem: one with no `git_sha` (it cannot say what it measured),
one with no `cases_sha` (S16), or an unreadable `circumstances.csv`. No commit hook and no CI step runs metrics.

## Measure the rules in your own repository

The staleness precision metric ships with the library: `esoi run staleness_precision --impl <repo_wide|component_paths|import_closure>`
builds a small git repository in a temporary folder with several components and a sequence of commits, and scores each rule against a
verdict written by hand per component and commit. A false-fresh decision (a kept result whose measured code changed) disqualifies the
rule; among the rest, fewer needless re-runs win. Add cases of your own to the library's fixture when a repository has a dependency the
fixture does not model.

## When a change cannot move the number

A rename, a comment or a refactor that keeps behaviour still changes the arm's own code, so its result goes stale. If you know it
does not change what the result measures, attest it instead of re-running:

```
esoi attest <component> <impl> --reason "renamed two locals; behaviour unchanged"
git add <evaluation>/attestations.csv && git commit
```

The result then counts as current for that commit range, `esoi leaderboard` says `current by attestation (reason)`, and the arm goes
stale again on any later change to its own code outside the range. The command refuses an empty reason, and refuses when the arm's
own code changed outside the range (an uncommitted edit, or a commit after `--through`). Staleness only informs: it never fails
`esoi check` or starts a re-run by itself. Details: [`esoi attest`](../reference/attest.md).
