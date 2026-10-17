"""BASELINE: the naive harness. A record carries no commit and no case file hash, run flags such as ``--only`` and
``--max-calls`` are not honoured, and nothing is told apart from a good run. Zero model calls."""


def build(meter):
    def measure(kind, args):
        if kind == "record":
            return {"git_sha": False, "dirty": False, "cases_sha_matches": False, "cases_sha_changes": False,
                    "rows": 1 + (1 if args.get("edit_cases") else 0)}
        if kind == "run":
            return {"cases": 3, "passed": 3 if args["impl"] != "bad" else 0, "error": None, "model_calls": 0}
        return {"cases": 3, "good_passed": 3, "bad_passed": 3}
    return measure
