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

## Match reliably: path, content, then task words

Matching uses no model, so it is cheap, repeatable and measurable. Three signals, cheapest first:

1. **Path** (`Paths:`), a glob on the file being edited. It decides whether a standard can apply at all.
2. **Content** (`When:`, optional), a regex on the file's text. A standard that only matters when a file embeds, calls a
   model or loops over records says so, and stays silent in a file that does none of that. This is what keeps three lines
   from becoming twelve.
3. **Task words** (the tag's `keywords`), for the moment before any file exists. `for-task "<what you are about to build>"`
   scores each standard by the keywords of its tags (one point each) and by words found in its own rule (half a point), and
   shows nothing under one point, so a vague task gets silence and not a guess.

The field that makes tag matching work is the tag's row in `docs/standards/tags.csv`:

| Column | Holds | Used for |
|---|---|---|
| `tag` | kebab-case name of the risk | the handle standards list under `Tags:` |
| `mitigates` | id of the problem in the repository's records | keeps a tag a risk and never a topic |
| `meaning` | one sentence starting "Risk of ... because ..." | what the tag protects, in the words of the failure |
| `keywords` | `;`-separated task-language words and synonyms | `for-task` matching before code exists |

Keep an umbrella tag (such as `low-quality-code`) to a keyword that rarely occurs, or it matches every task. When a standard
is missed or shown in vain, the fix is a keyword, a `When:` regex or a path, and the miss becomes a labelled case (task or
file, expected standards) so precision and recall can be recorded as the metric of this matching.

## Write the text so it can be used

`python -m esoi.standards_nav lint` checks these, and the commit hook runs it whenever the standards folder changes:

- A **Rule** is one sentence of at most 40 words, ending in a full stop, that states what to do (an imperative, no hedges
  such as "should", "consider", "ideally"). Its job is to be acted on without opening the file.
- A **Check** message says what is wrong and what to do instead, in at most 45 words.
- A **tag meaning** starts "Risk of" and names the failure, not the subject area.
- No em dashes, and a rule lives in one standard only; detail goes below the header, never into the Rule line.
- Add a standard when a mistake has happened twice; never grow an existing file.

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

`python -m esoi.standards_nav install-hook [repo]` writes a `pre-commit` hook where git looks for hooks (it honours
`core.hooksPath` and never overwrites another hook). It blocks on findings and, when there are none, lists the rules for
the staged files that have no automatic check so the author confirms them by hand. It does nothing when esoi is not
importable, so a server checkout still commits.

A finding is waived at its line with `standards-waive: <standard id> <reason of three or more words>`. The reason stays in
the code for review, which is the point: the author has to say why this case differs.

## When to add a rule

Add one when a mistake has happened twice, as [apply with tools](apply-with-tools.md) says. Write the standard, give it the
tag of the risk, and write the `Check:` line that would have stopped it. A rule with no check still earns its place when
the one-line rule shown at the edit is enough.
