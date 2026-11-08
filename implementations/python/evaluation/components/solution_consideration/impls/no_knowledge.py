"""BASELINE: the prompt with no knowledge items at all; what a pass reads when knowledge is left out. Zero model calls."""
from esoi.understanding.solution_consideration import solution_prompt

from . import repos


def build(meter):
    def prompt(kind, args):
        made = solution_prompt.prompt(repos.network(args["repo"]), args["solution"], args.get("task", ""), args.get("budget", 24000),
                                      knowledge="none")
        ids = [i["id"] for i in made.get("knowledge", []) + made.get("knowledge_inactive", [])] if "none" == "ranked" else []
        return {"text": made["text"], "chars": made["chars"], "knowledge_ids": ids}
    return prompt
