"""Shared by the verdict arms: the instruction, the model call and the reading of the verdict line."""
import re

from shared_fixtures import model_arms

INSTRUCTION = ("Answer the matter for this one solution. Your first line is exactly one of: VERDICT: adopt, VERDICT: reject, "
               "VERDICT: measure first. Then at most five sentences naming the records your verdict rests on, with their numbers. "
               "Use no em dashes.")
VERDICT = re.compile(r"verdict:\s*(adopt|reject|measure first)", re.I)


def asker(meter):
    chosen = model_arms.provider(meter)

    def ask(context, task):
        reply = chosen.answer([{"role": "user", "content": f"{context}\n\n## The matter\n{task}\n\n{INSTRUCTION}"}], model=model_arms.model())
        found = VERDICT.search(reply or "")
        return {"text": reply, "verdict": found.group(1).lower() if found else ""}
    return ask
