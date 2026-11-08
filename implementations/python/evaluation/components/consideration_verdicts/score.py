"""Score one verdict: the expected verdict, and at least one of the strings that cite the deciding record (case-insensitive)."""


def score_case(fn, case):
    out = fn(case["kind"], case["args"])
    want = case["expect"]
    text = (out.get("text") or "").lower()
    cites = any(c.lower() in text for c in want.get("cites", []))
    ok = out.get("verdict") == want["verdict"] and cites
    note = f"verdict {out.get('verdict') or 'none'} (want {want['verdict']})" + ("" if cites else "; cites none of the deciding records")
    return dict(ok=ok, got=case["kind"], note=note)


def aggregate(rows):
    return {"verdicts_right": sum(bool(r.get("ok")) for r in rows), "cases": len(rows)}
