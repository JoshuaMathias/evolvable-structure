"""CURRENT: the prompt formed from the solution's network of records, filled by tier within the budget. Zero model calls."""
from esoi.understanding.solution_consideration import solution_prompt

from . import repos


def build(meter):
    def prompt(kind, args):
        made = solution_prompt.prompt(repos.network(args["repo"]), args["solution"], args.get("task", ""), args.get("budget", 24000))
        return {"text": made["text"], "chars": made["chars"]}
    return prompt
