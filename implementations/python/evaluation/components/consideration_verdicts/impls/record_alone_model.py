"""PAID BASELINE: the same cheap model given only the solution's own record. One call per case."""
from solution_consideration.impls import repos
from consideration_verdicts import ask

PAID = True
ALTERNATIVE = True   # the baseline: it does not drive the network prompt


def build(meter):
    asking = ask.asker(meter)

    def verdict(kind, args):
        row = repos.network(args["repo"]).solutions[args["solution"]]
        context = "\n".join(f"{key}: {' '.join(value.split())}" for key, value in row.items() if (value or "").strip())
        return asking(context, args["task"])
    return verdict
