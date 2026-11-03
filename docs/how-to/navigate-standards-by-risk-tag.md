# Navigate standards by risk tag

A standards index that every author must read fails twice: it is too long to read, and a rule nobody met is a rule that was
not applied. Tag each standard with the risk it mitigates and the paths it applies to, and show an author only the matching
rules at the moment they edit, then check the commit against them. The skill's tags work this way: a tag names the risk it
mitigates, and here the risk is low quality code.

## Write a standard so it can be found

One small file per standard in `docs/standards/`. These header lines make it take part:

```
**Tags:** request-path-cost, low-quality-code
**Paths:** app/api/endpoints/**/*.py; app/api/routes/**/*.py
**Rule:** One sentence an author can act on without opening the file.
**Check:** regex:\bembed_text\( => Why this is a problem and what to do instead.
**Check:** undecorated-def => A route module holds handlers only.
**Check:** needs-test:tests/api/** => A route change ships with a test.
```

A file without Tags, Paths and Rule is skipped, so a repository adopts the convention one standard at a time. Each tag is
a row of `docs/standards/tags.csv` naming the problem in the repository's records it mitigates, so a tag is a handle on a
risk and never a topic.

## See the rules while editing

`python -m esoi.standards_nav for-file <path>` prints the rules whose paths match, at most four, as one line each with the
file to open for detail. A hook on the agent's edit tool calls it, so an author sees three lines for the file in hand and
not the index.

## Check the commit

`python -m esoi.standards_nav check-staged <repo>` runs every `Check:` line over the lines the staged change adds. Old code
is never flagged, so a repository with a long history adopts a standard without a waiver per old violation. It exits 1 on a
finding; a hook on `git commit` turns that into a block. Three kinds of check exist: `regex:` over added lines,
`undecorated-def` (a top-level function with no decorator in a module that should hold handlers only), and
`needs-test:<glob>` (a change under the paths with no staged file matching the glob).

A finding is waived at its line with `standards-waive: <standard id> <reason of three or more words>`. The reason stays in
the code for review, which is the point: the author has to say why this case differs.

## When to add a rule

Add one when a mistake has happened twice, as [apply with tools](apply-with-tools.md) says. Write the standard, give it the
tag of the risk, and write the `Check:` line that would have stopped it. A rule with no check still earns its place when
the one-line rule shown at the edit is enough.
