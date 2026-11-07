"""Score one mutation case, shared by every checker component: the checker must report the expected rule (and the expected substring) for the
injected violation, or stay clean on the clean fixture. A case may instead expect the rule as advice (``advice``: listed under the output's
``advisory``; ``advisory``: noted under its ``notes``), never as a problem, or be a ``scale`` case that checks the time the check takes on a
large generated repository against a ceiling. ``aggregate`` reports mutations detected and false positives apart. A component's ``score.py``
imports ``score_case`` and ``aggregate`` from here."""
from esoi.optimization.measurement_harness import expect


def scale_row(out, want):
    problems = expect.check(out, want)
    return dict(ok=not problems, got="scale", note=("ok" if not problems else "; ".join(problems))
                + f" (cold {out.get('cold_seconds')}s, warm {out.get('warm_seconds')}s)")


def advice_row(out, case, want):
    problems = out["problems"]
    hits = [p for p in out.get("advisory", []) if p.startswith(want["rule"] + " ") and want.get("contains", "") in p]
    ok = bool(hits) and not any(p.startswith(want["rule"] + " ") for p in problems)   # advice, never a problem
    return dict(ok=ok, got=f"{case['kind']}:{want['rule']}",
                note="ok" if ok else f"{want['rule']} {want.get('contains', '')!r} not given as advice, or it is a problem")


def noted_row(out, case, want):
    problems = out["problems"]
    seen = [n for n in out.get("notes", []) if want["rule"] + " " in n and want.get("contains", "") in n]
    ok = out["exit"] == 0 and not problems and bool(seen)
    return dict(ok=ok, got=f"{case['kind']}:{want['rule']}:advisory",
                note="ok" if ok else f"advisory {want['rule']} {want.get('contains', '')!r} not noted, or raised as a problem; "
                                     f"problems {[p[:60] for p in problems[:3]]}")


def score_case(fn, case):
    out = fn(case["kind"], case["args"])
    want = case["expect"]
    if case["kind"] == "scale":
        return scale_row(out, want)
    if want.get("clean"):
        return clean_row(out)
    if want.get("advice"):   # information only: reported as advice and never as a problem
        return advice_row(out, case, want)
    if want.get("advisory"):
        return noted_row(out, case, want)
    return problem_row(out, case, want)


def clean_row(out):
    """The row for a fixture that must raise no problem."""
    ok = out["exit"] == 0 and not out["problems"]
    return dict(ok=ok, got="clean", note="ok" if ok else f"false positive: {out['problems'][:2]}")


def problem_row(out, case, want):
    """The row for a mutation that must be reported as a problem of the named rule."""
    problems = out["problems"]
    hits = [p for p in problems if p.startswith(want["rule"] + " ") and want.get("contains", "") in p]
    ok = out["exit"] == 1 and bool(hits)
    return dict(ok=ok, got=f"{case['kind']}:{want['rule']}",
                note="ok" if ok else f"{want['rule']} {want.get('contains', '')!r} not reported; saw {[p[:60] for p in problems[:3]]}")


def aggregate(rows):
    clean = [r for r in rows if r.get("got") == "clean"]
    muts = [r for r in rows if r.get("got") not in ("clean", "scale")]
    caught = sum(bool(r["ok"]) for r in muts)
    return (f"mutations detected {caught}/{len(muts)}, clean fixtures passed "
            f"{sum(bool(r['ok']) for r in clean)}/{len(clean)}")
