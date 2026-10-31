"""Shared by the arms: rows from a case into ``esoi.evidence.Evidence``, and the output dicts the cases check."""
import datetime

from esoi import evidence

DEFAULT = dict(value="0.7", dimension="quality", measure="pass_rate", unit="fraction", better="higher", comparator="bench-1",
               source_kind="independent_benchmark", run_by_independent="yes", method_disclosed="yes", n="500",
               benchmark_status="live", date_published="2026-09-01", date_checked="2026-10-30", confounds="", note="")


def read(rows):
    filled = [dict(DEFAULT, source_url=f"https://example.org/{r['evidence_id']}", **{k: str(v) for k, v in r.items()}) for r in rows]
    found, problems = evidence.parse_rows(filled)
    assert not problems, problems
    return found


def today(args):
    return datetime.date.fromisoformat(args["today"])


def runner(estimate_fn, rank_fn):
    def run(kind, args):
        rows = read(args["rows"])
        if kind == "grade":
            got = estimate_fn(rows, today(args))
            key = lambda k: f"{k[0]}/{k[1]}"
            return {"grades": {key(k): e.grade for k, e in got.items()}, "flags": {key(k): list(e.flags) for k, e in got.items()},
                    "needs_own_run": {key(k): e.needs_own_run for k, e in got.items()}}
        got = rank_fn(rows, {d: 1 for d in args["dims"]}, today(args))
        return {"order": {d: [p.candidate for p in r.ordered] for d, r in got.dimensions.items()}}
    return run
