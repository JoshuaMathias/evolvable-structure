"""PAID: a cheap model given the prompt the solution's network forms, with the knowledge the situation chooses. One call per case."""
from esoi.understanding.solution_consideration import knowledge, solution_prompt

from solution_consideration.impls import repos
from consideration_verdicts import ask

PAID = True


def build(meter):
    asking = ask.asker(meter)

    def verdict(kind, args):
        made = solution_prompt.prompt(repos.network(args["repo"]), args["solution"], args["task"])
        chosen = knowledge.select(made["knowledge"], args["task"])
        context = made["text"] + ("\n\n## Knowledge that bears on this\n" + "\n".join(knowledge.line(i) for i in chosen) if chosen else "")
        return asking(context, args["task"])
    return verdict
