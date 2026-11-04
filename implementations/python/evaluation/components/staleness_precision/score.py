"""Score one staleness decision against what the fixture's code really reads (written by hand in the case).

A decision that keeps a result whose measured code changed is a false-fresh (never acceptable: it disqualifies the arm); a decision
that calls a result stale when nothing it measures changed is a false-stale (a metric re-run, or a row flagged, for nothing).
``aggregate`` reports both counts, and ``disqualify`` names the arm's false-fresh decisions so the record cannot rank it.
"""


def score_case(fn, case):
    out = fn(case["kind"], case["args"])
    want = bool(case["expect"]["stale"])
    got = bool(out["stale"])
    if got == want:
        return dict(ok=True, got="agree", note="ok")
    if want and not got:
        return dict(ok=False, got="false-fresh", note=f"FALSE FRESH: kept a result whose measured code changed ({case.get('note', '')})")
    return dict(ok=False, got="false-stale", note=f"false stale: {out.get('why', '')[:120]}")


def aggregate(rows):
    fresh = sum(r.get("got") == "false-fresh" for r in rows)
    stale = sum(r.get("got") == "false-stale" for r in rows)
    return dict(false_fresh=fresh, false_stale=stale, decisions=len(rows))


def disqualify(rows):
    fresh = [r["id"] for r in rows if r.get("got") == "false-fresh"]
    return f"false-fresh in {len(fresh)} decision(s): {', '.join(fresh[:6])}" if fresh else ""
