"""Score one consumer-registry mutation case: the checker must report the expected rule (and the expected substring) for the
injected violation, or stay clean on the clean fixture (the same scoring as check_the_structure)."""


def score_case(fn, case):
    out = fn(case["kind"], case["args"])
    want = case["expect"]
    problems = out["problems"]
    if want.get("clean"):
        ok = out["exit"] == 0 and not problems
        return dict(ok=ok, got="clean", note="ok" if ok else f"false positive: {problems[:2]}")
    hits = [p for p in problems if p.startswith(want["rule"] + " ") and want.get("contains", "") in p]
    ok = out["exit"] == 1 and bool(hits)
    return dict(ok=ok, got=f"{case['kind']}:{want['rule']}",
                note="ok" if ok else f"{want['rule']} {want.get('contains', '')!r} not reported; saw {[p[:60] for p in problems[:3]]}")


def aggregate(rows):
    clean = [r for r in rows if r.get("got") == "clean"]
    muts = [r for r in rows if r.get("got") != "clean"]
    caught = sum(bool(r["ok"]) for r in muts)
    return (f"mutations detected {caught}/{len(muts)}, clean fixtures passed "
            f"{sum(bool(r['ok']) for r in clean)}/{len(clean)}")
