"""Score one case of the structure-quality metric: an ``assess`` case by what the arm flags, a ``compare`` case by which of two shapes it scores higher.

``aggregate`` reports passes by kind and by source, so a scorer that is right for one source of cases and blind to the others is visible.
"""
from collections import Counter

from shared_fixtures.interface import structure_fixture


def run(fn, shape, stage=1):
    return fn("assess", {"shape": shape, "stage": stage, "consumers": structure_fixture.options(shape).get("consumers", ())})


def score_case(fn, case):
    args, want = case["args"], case["expect"]
    if case["kind"] == "compare":
        better, worse = run(fn, args["better"], args.get("stage", 1)), run(fn, args["worse"], args.get("stage", 1))
        ok = better["score"] is not None and worse["score"] is not None and better["score"] > worse["score"]
        return dict(ok=ok, got="compare", note="ok" if ok else f"{args['better']} {better['score']} is not above {args['worse']} {worse['score']}")
    out = run(fn, args["shape"], args.get("stage", 1))
    if want.get("clean"):
        ok = out["verdict"] == "at_reference" and not out["flagged"]
        return dict(ok=ok, got="assess", note="ok" if ok else f"clean exemplar called {out['verdict']} and flagged {out['flagged']}")
    missing = [d for d in want["flags"] if d not in out["flagged"]]
    return dict(ok=not missing, got="assess", note="ok" if not missing else f"did not flag {missing}; flagged {out['flagged']}")


def aggregate(rows):
    kinds = Counter(r["got"] for r in rows)
    passed = Counter(r["got"] for r in rows if r["ok"])
    return ", ".join(f"{k} {passed[k]}/{kinds[k]}" for k in sorted(kinds))
