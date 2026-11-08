"""CURRENT: the prompt formed from the solution's network of records, filled by tier within the budget, with the knowledge items the
situation chooses (the library's reference retriever over the candidates, as a caller without its own retriever would). Zero model calls."""
from esoi.understanding.solution_consideration import knowledge, solution_prompt

from . import repos


def build(meter):
    def prompt(kind, args):
        made = solution_prompt.prompt(repos.network(args["repo"]), args["solution"], args.get("task", ""), args.get("budget", 24000))
        chosen = knowledge.select(made["knowledge"], args.get("task", ""))
        text = made["text"] + ("\n\n## Knowledge that bears on this\n" + "\n".join(knowledge.line(i) for i in chosen) if chosen else "")
        return {"text": text, "chars": len(text), "knowledge_ids": [i["id"] for i in chosen], "knowledge_count": len(chosen)}
    return prompt
