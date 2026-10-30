# Versioning

Three things have a version here, and they move for different reasons.

| What | Where it is written | Changes when |
|---|---|---|
| The `esoi` package | `version` in `implementations/python/pyproject.toml` (and `__version__` in `esoi/__init__.py`, which a test keeps equal) | a release, by the rule below |
| The skill the library follows | the `skill` part of the stamp | `esoi skill sync` copies a changed skill |
| The intent template | the `template` part of the stamp: a whole number, the template version | `esoi template sync` finds changed template content |

## The package: semantic versioning

`MAJOR.MINOR.PATCH`. A change to the template, to what a rule reports, to a record column or to a command's behavior
is at least a minor bump, because an adopting repository may need to act on it. A patch fixes a defect without changing
what a repository must do. A major bump removes or renames something an adopter relies on without a migration.

Each `CHANGELOG.md` release section opens with the skill commit its template came from and the template version, so a
reader can tell which wording of ESOI a release carries. `## Unreleased` collects entries until a release; releasing means
renaming it to the version, adding that opening line, bumping `pyproject.toml` and `__version__` in the same commit, and
starting a new empty `## Unreleased`. Tagging and publishing are separate decisions of the library's owner.

### What a feature that adds record files changes for an adopter

Seeing a difference by circumstance (see [the guide](../guides/measure-per-circumstance.md)) is the example of a minor bump that
adds structure. An adopter that does nothing sees only these:

- **One optional record file.** `circumstances.csv` is read when it exists, in any intent folder. It is not one of the five
  template entities, and every cell is an id, a link or a condition a machine reads, so it carries no prose field. A prose field
  on a circumstance (a `description`) is not added by the library: the owner of the specification proposes and approves fields,
  as for any field (rule R7). A repository without the file records exactly what it did before.
- **The results log.** A recorded run of a component that has circumstances also appends derived rows whose `sample` is
  `slice:<id>`, and writes `per_case.csv` beside the log. Both are excluded from the staleness test of the measured code; the
  table's hash is part of it, so editing `circumstances.csv` makes the derived rows stale until `esoi run --stale` derives them
  again.
- **A behavior change in the default verdict.** Only a row that scored a whole run (the full set or `sample:N`) decides it. A row
  recorded with `--only` no longer does, which is the defect that made a recorded subset the newest key two arms share. A
  repository whose only shared rows were `only:` rows now reads UNMEASURED until the arms are run on the same sample, and a rival
  recorded only on named cases is listed as `not comparable: named cases only`.
- **Names.** An implementation name may be a variant, `name@key=value`; the metric command pattern accepts it.

Routing a call by circumstance (a map written by `esoi select --promote` and applied at run time) is designed and not built.

## The stamp: which skill and template this library follows

`implementations/python/esoi/data/skill_version.json` is generated, never edited. It holds commits and hashes only, no
path or name, and syncing again from the same source changes nothing.

- `skill`: the git `commit` that last touched the synced skill files in their source repository, `committed` (false when
  the source had uncommitted changes, as the author's working copy often has), the `date` (the commit's date, else the day
  it was first stamped), `skill_md_sha256` (a hash of the source `SKILL.md`, so it identifies the content without git)
  and `copy_sha256` (a hash of the shipped copy).
- `template`: the current `version`, the first 12 digits of the `sha256` of the parsed template, the `skill_commit`
  and `skill_md_sha256` it came from, the `date`, and `changes`: the fields added, removed, made optional or required,
  moved between the specify and interface groups, or reworded since the version before. A field's key comes from its question,
  so rewording a question shows as one field removed and one added.
- `history`: the earlier template versions, oldest first, in the same shape.

The template version goes up by one when the content changes and by nothing otherwise, so it orders the changes the way a
hash cannot. Version 1 is the first recorded one; its change list says so.

`esoi version` prints the package version, the skill commit and date, and the template version.

## A repository records the template version its records follow

```toml
[records]
template_version = 1
```

`esoi version --record` writes the line (`esoi init` writes it for a new repository). Rule **S34** compares it with the
library's:

- recorded older than the library's: `esoi check` fails and names, for each newer version, its date, the skill commit and
  the fields that changed, then the way forward. If `esoi fields migrate` would change the repository's records, it says to
  run `esoi fields migrate --apply`; otherwise the records are updated by hand where a change affects them. After that,
  `esoi version --record` records the new version.
- recorded newer than the library's: the installed `esoi` is older than the repository expects; upgrade it.
- nothing recorded: no failure. `esoi check` prints one note suggesting `esoi version --record`.

Recording a version says the records follow that template; it does not check that they do. `esoi check` still reports
the fields the records lack under R1 and R2.
