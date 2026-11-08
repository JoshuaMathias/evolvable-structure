"""PAID: The lexical arm's wider candidate list, then a cheap model chooses among those candidates. One model call per case through the provider the environment names (shared_fixtures.model_arms); run only within an
approved budget."""
from pathlib import Path

from esoi.understanding.solution_relevance import relevance, relevance_cases
from shared_fixtures import model_arms

PAID = True
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "esoi.toml").is_file())


def build(meter):
    chosen = model_arms.provider(meter)

    def answer(prompt):
        return chosen.answer([{"role": "user", "content": prompt}], model=model_arms.model())
    return relevance_cases.runner(ROOT, "", rank=relevance.model_arm(answer, "lexical_index"))
