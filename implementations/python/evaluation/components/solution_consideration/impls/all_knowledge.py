"""BASELINE: every knowledge item of the solution written into its prompt in the no-retriever order (status, source, recency), inactive ones labelled; what a pass reads when the situation chooses nothing. Zero model calls."""
from esoi.understanding.solution_consideration import solution_prompt

from . import repos


def build(meter):
    def prompt(kind, args):
        made = solution_prompt.prompt(repos.network(args["repo"]), args["solution"], args.get("task", ""), args.get("budget", 24000),
                                      knowledge="ranked")
        ids = [i["id"] for i in made.get("knowledge", []) + made.get("knowledge_inactive", [])] if "ranked" == "ranked" else []
        return {"text": made["text"], "chars": made["chars"], "knowledge_ids": ids, "knowledge_count": len(ids)}
    return prompt
