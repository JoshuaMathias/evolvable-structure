"""The scoring every verdict-checking component shares: a case passes when every named check passes (``verdict_row``), and ``tally`` reports how many cases passed each check."""
from collections import Counter


def verdict_row(found, checks):
    """The score row of one case whose checks gave ``found`` (check name to pass or fail)."""
    failed = [c for c in checks if not found.get(c)]
    return dict(ok=not failed, got=",".join(c for c in checks if found.get(c)), note="ok" if not failed else "fails " + ", ".join(failed))


def tally(rows, checks):
    """How many of the rows passed each check, as one line."""
    seen = Counter()
    for r in rows:
        for c in (r.get("got") or "").split(","):
            if c in checks:
                seen[c] += 1
    return ", ".join(f"{c} {seen[c]}/{len(rows)}" for c in checks)
