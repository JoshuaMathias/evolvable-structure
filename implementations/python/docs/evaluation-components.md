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

## Declared implementations

An implementation the code declares (`@implementation` in `esoi.runtime`) needs no `impls/<name>.py`: `esoi run <component>
--impl <name>` imports the module its record names and calls the implementation with each case's `args` as keyword arguments.
A `score.py` may define `adapt(implementation, meter) -> fn` to call it another way. A wrapper file stays for a baseline, a
reference arm, or an implementation that needs the call meter.

## Simulated arms

An arm that meters a deterministic stand-in for a model (it counts the calls a real model would make, with no tokens and no
price) sets `SIMULATED = True` at module level. Its runs record model `simulated` and cost `0.0`, `esoi run --stale` never
treats it as paid (a `PAID = True` marker or `paid_arms` still wins), and the leaderboard compares it on model calls, never
against a dollar figure. Without the marker the cost stays blank (unknown), the arm is treated as paid, and a known `$0`
baseline is not called cheaper than a cost that is merely unknown.

## Reference arms

Open an implementation's docstring with `BASELINE`, `FLOOR`, `ABLATION`, `ALTERNATIVE` or `VALIDITY` (or set
`ALTERNATIVE = True`) to say it is not the live code. The check requires that every other implementation imports the
package under test (rule S12), so a number measures what ships.

## In this repository

Ten components ship in `implementations/python/evaluation/components/`: the structure check, placement and layering, the
records, template reading, selection, the harness, the leaderboard, the tracker, the consumer check and the public copy of the skill. Their cases build
small synthetic repositories (`repo_fixture.py`, `harness_fixture.py`, `consumer_fixture.py`) and inject one defect at a
time, so a case passes only when the right rule reports the right path.
