# Generate the wiki from the docs

Use this to publish a GitHub wiki that cannot drift, because it is generated from `docs/` and never edited.

## Keep the docs in four folders

Every page sits in exactly one of `docs/tutorials/`, `docs/how-to/`, `docs/explanation/` and `docs/reference/`, plus the index
`docs/README.md`. Check it, including that every internal link resolves:

```
esoi docs check
```

## Write the wiki pages

```
esoi docs wiki --out ../my-repo.wiki
```

The pages are written to that folder, replacing the pages there. The repository address is read from the `origin` remote; pass
`--repo-url` to name it. Add `--extra path/to/page.md` for a page outside `docs/`, or list such pages once in `esoi.toml` as `[docs] wiki_extra = ["path/to/page.md"]` (used when `--extra` is not given). Nothing is pushed.

To publish, review the folder, then either commit it in the wiki checkout yourself or pass the wiki's git address:

```
esoi docs wiki --out /tmp/wiki-work --push https://github.com/OWNER/REPO.wiki.git
```

Pushing is the one step that uses the network, and it happens only when `--push` is given.
