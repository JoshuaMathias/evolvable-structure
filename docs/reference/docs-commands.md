# Docs commands

## `esoi docs check`

`esoi docs check [--root DIR] [--docs-dir docs]`

Fails (exit 1) when `docs/README.md` is missing, a markdown page sits outside the four category folders (`tutorials`,
`how-to`, `explanation`, `reference`), or a relative link does not resolve to a file. Links inside code spans and fenced
blocks are ignored. Exit 0 prints `esoi docs ok`.

## `esoi docs wiki`

`esoi docs wiki --out DIR [--repo-url URL] [--branch main] [--extra FILE ...] [--check] [--push WIKI_GIT_URL]`

Writes one page per markdown file under `docs/` (named after its first heading) and each `--extra` file into `DIR`, replacing
the pages there. `docs/README.md` becomes `Home`. `_Sidebar.md` lists Home and then one group per category, in the order
Tutorials, How-to guides, Explanation, Reference (pages the index links to first, in its order); pages outside the four folders
go under More. Relative links to other pages become wiki links; other relative links point at the file on the repository host.
Each page ends with a note naming its source file. `--check` fails when the index does not link to a page. `--push` clones the
wiki repository, replaces its pages and pushes.
