# Generate the README of every intent folder

Use this so that anyone clicking into an intent folder sees what the intent is, how its solutions fit and where to go next, from a
page the records themselves produce. The page standard is in [the intent README standard](../reference/intent-readme.md).

## Write the pages

```
esoi readmes
```

It writes `README.md` in every intent folder (the top intent and each sub-intent) and lists the files it changed. Commit them.
`esoi check --write-docs` calls the same code, and rule S8 reports a page that is out of date.

## Keep them current

```
esoi readmes --check
```

lists the pages that no longer match the records and exits 1 when there are any. Run `esoi readmes` after editing a record, after
recording a result (each metric's leader is on the page) and after declaring a solution's entry (`@solution(..., entry=..., example=...)`
puts its one-line call in the solutions table).

## Choose another layout

The selected layout is the one the measurement chose. To use a rival, set it in `esoi.toml`:

```toml
[readme]
layout = "links"   # or "full"
```

## Measure a layout on your own folders

`esoi run readme_at_a_glance --impl at_a_glance` scores every intent folder of this repository on the glance checks. Set
`ESOI_GLANCE_ADOPTERS` to the paths of other repositories (separated as `PATH` is) to measure theirs as `adopter-1`, `adopter-2` and
so on.
