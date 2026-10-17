# Evaluation components

A component is a folder under `evaluation_dir` that measures one solution:

```
evaluation/components/<component>/
  score.py        score_case(fn, case) -> {"ok": bool, "got": ..., "note": ...}; optional aggregate(rows), load_cases()
  cases.json      the cases (or cases.csv, when the dataset is reviewed as a sheet; a "heldout" cell marks held-out cases)
  interface.py    the one function every implementation exposes (a docstring is enough)
  impls/<name>.py build(meter) -> fn          one file per alternative; drives the real code
  broken/<name>.py                            the naive baseline an invariant solution's cases must fail
  noise.json      optional {"pass_margin": 0.15, "spend_tolerance": 0.2} for a sampled comparison
```

Run one with `esoi run <component> --impl <name>`; add `--record` to append a row to the results log, `--only ID,ID` to run
named cases, `--sample N` to run N cases spread over the strata, and `--max-calls N` to abort a run that exceeds a
model-call budget.

## Case-driven components

Most components give each case a `kind`, `args` and a declarative `expect` (see `esoi.expect`): `eq`, `has`, `contains`,
`not_contains`, `max_len`, `min_len`, `approx`. A new case is then data only.

## Reference arms

Open an implementation's docstring with `BASELINE`, `FLOOR`, `ABLATION`, `ALTERNATIVE` or `VALIDITY` (or set
`ALTERNATIVE = True`) to say it is not the live code. The check requires that every other implementation imports the
package under test (rule S12), so a number measures what ships.

## In this repository

Nine components ship in `implementations/python/evaluation/components/`: the structure check, placement and layering, the
records, template reading, selection, the harness, the leaderboard, the tracker and the consumer check. Their cases build
small synthetic repositories (`repo_fixture.py`, `harness_fixture.py`, `consumer_fixture.py`) and inject one defect at a
time, so a case passes only when the right rule reports the right path.
