# Measure an implementation per circumstance

One implementation is rarely best everywhere. A model that is best for short files may lose on long ones, and an add-on such as a
check or a rewrite step may help under one model or harness and only cost under another. ESOI keeps its rule that a solution has
one authoritative metric and one selected implementation. This guide adds the means to *see* a difference by circumstance, at no
extra model call. It does not select anything: a slice verdict is a proposal for a person.

| Part | What it is |
|---|---|
| Variant, `name@key=value` | The same implementation with other parameters (`esoi.variants`). The string is the `impl` cell of a results row, a `--impl` value, a `using=` value and a `selected` cell, so everything that compares `impl` strings works unchanged. Keys are sorted and values written as what they read as (`true`, `false`, whole numbers, decimals), so one variant has one spelling (`k=01` is `k=1`). |
| `circumstances.csv` | One row per situation: `circumstance_id`, `case_filter`, `run_filter`, `problem_ids`, `solution_ids`. Every cell is an id, a link or a condition a machine reads (`esoi.circumstances`). The id is a name (lower case letters, digits, `_`, `-`): the rule of `esoi.assemble`. A row that cannot be read stops the run. |
| Slice rows | `esoi run --record` appends one derived row per circumstance, `sample` = `slice:<id>`. They are left out of the default verdict. |
| `per_case.csv` | The per-case log beside the results log: one row per case of the newest run of each arm and sample. Appended, then compacted through a temporary file, so two recorders do not lose each other's rows, and rows of older cases are pruned. |

## What a circumstance may be

A circumstance is defined on something that is known before the work, so a slice never describes an outcome. `case_filter` reads the
fields of a case (`max_target_lines>400`). `run_filter` reads the run: its recorded `model` (an exact id) and the parameters in its
variant name, so the harness an add-on is used under is part of the arm's name (`guard@harness=native`). A situation known only
afterwards (difficulty, success) is a stratum of the cases, not a circumstance.

A condition is terms joined by ` and ` (any case): `field op value` (`= == != < <= > >=`, numbers compared as numbers) or
`field in a|b`, an exact match. A value has no spaces. A condition the parser cannot read, a field that no case carries, and an id that
is not a name are errors when the table is loaded or the run starts, never a slice that quietly matches nothing.

Editing `circumstances.csv` makes the derived rows stale: the run's per-case rows record a hash of the table, and
`esoi run --stale` re-derives them (offline arms only; a paid arm is listed, not run).

## An example

The first block makes a repository whose two arms are right on opposite halves of eight cases, with two circumstances on the size
of a case. `live` is the baseline: nothing added.

```python
import csv
import importlib
import json
import tempfile
from pathlib import Path

from esoi import config as config_module, harness, scaffold

root = Path(tempfile.mkdtemp()) / "demo"
scaffold.init(root, "demo_pkg", say=lambda text: None)
component = root / "evaluation" / "components" / "greet_a_person"
build = 'def build(meter, **params):\n    def run(kind, args):\n        n = args["n"]\n        return {"n": n if n %s params.get("cut", 5) else -1}\n    return run\n'
(component / "impls" / "live.py").write_text('"""BASELINE: nothing added, the harness as it is."""\n' + build % "<=")   # right for small n
(component / "impls" / "alt.py").write_text(build % ">")     # right for large n
(component / "cases.json").write_text(json.dumps([
    {"id": f"c{n}", "kind": "k", "size": n, "heldout": n in (3, 7), "args": {"n": n}, "expect": {"eq": {"n": n}}} for n in range(1, 9)]))
(root / "esoi" / "circumstances.csv").write_text(
    "circumstance_id,case_filter,run_filter,problem_ids,solution_ids\n"
    "big,size>5,,greeting-by-hand,greet-a-person\nsmall,size<=5,,greeting-by-hand,greet-a-person\n")
config = config_module.load(root)
harness.prepare_path(config)
score = importlib.import_module("greet_a_person.score").score_case
```

The second block measures both arms, once each. `alt@cut=5` is a variant: `alt` is built with `cut=5`. Each run appends its own row and
one derived row per circumstance.

```python
for arm in ("live", "alt@cut=5"):
    harness.run_component("greet_a_person", score, ["--impl", arm, "--record"], config, lambda text: None)
rows = [(r["impl"], r["sample"] or "full", f"{r['passed']}/{r['cases']}") for r in csv.DictReader(config.results_path.open())]
print([row for row in rows if row[0] == "alt@cut=5"])
# [('alt@cut=5', 'full', '3/8'), ('alt@cut=5', 'slice:big', '3/3'), ('alt@cut=5', 'slice:small', '0/5')]
```

On the full set `live` (5/8) beats `alt@cut=5` (3/8), and the slice rows stay out of that verdict (so does a run of named cases
recorded with `--only`; an arm recorded only on named cases is listed as `not comparable: named cases only`, never skipped).

## Reading a slice verdict

`leaderboard.slice_verdicts` judges one arm against the others inside each circumstance, with the same rules as the board.

```python
from esoi import leaderboard

verdicts = leaderboard.slice_verdicts("greet_a_person", "live", leaderboard.slice_results(config.results_path))
print([(cid, label) for cid, label, _ in verdicts])
# [('big', 'LOSS'), ('small', 'WIN')]
```

Read `big LOSS` as a PROPOSAL: in the big circumstance `alt@cut=5` passed 3 of 3 against 0 of 3. It is a lead for a person to
act on, for example by measuring more cases of that kind. Nothing is selected by it, and a verdict on three cases is weak: the
margin the board uses does not grow as the slice shrinks, so a person weighs the slice's size, its held-out cases and how many
circumstances were looked at.

## The design rule for an add-on

An add-on is only justified by measured marginal value over the baseline "none: provider-native plus the harness as is" in the
circumstance it serves. The baseline is the incumbent and ties go to it, and the margin must scale with slice size.

So pass the baseline arm as the incumbent to `slice_verdicts` (above, `live`): the add-on has to beat it inside the circumstance
it serves, under the same `run_filter`, and a TIE is the baseline keeping its place. The scaling of the margin with slice size is
not built.

## Designed, not built

A routed selection (a map from circumstance to arm, written by `esoi select --promote`, and a `facts=` layer in `esoi.runtime` that
applies it) is designed and not built. It waits for an adopter to show a measured slice disagreement and for an offline
`rank_by_circumstance` component with always-route and never-route validity arms, so that routing is itself measured before it
is adopted. Until then the selection is one arm per solution, as before.

## What stays with the application

Which circumstances exist, their thresholds and the fields that carry them in the cases belong to the application. The library
supplies the table, the variants, the slices and the log.
