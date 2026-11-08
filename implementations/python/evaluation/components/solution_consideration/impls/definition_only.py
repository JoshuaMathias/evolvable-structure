"""BASELINE: the solution's own record and nothing connected to it (what `esoi spec show ID --tier 2` prints), cut to the budget.
It is what a pass reads when no network forms its prompt. Zero model calls."""
from esoi.understanding.solution_consideration import solution_prompt

from . import repos


def build(meter):
    def prompt(kind, args):
        net = repos.network(args["repo"])
        row = net.solutions[args["solution"]]
        text = "\n".join(f"{key}: {' '.join(value.split())}" for key, value in row.items() if (value or "").strip())
        text = text[:args.get("budget", 24000)]
        return {"text": text, "chars": len(text)}
    return prompt
