"""An expert model reads an outline of the project and judges its scoping (``esoi.structure.structure_quality.expert_review``). It costs money: one call per
project reviewed, about 6000 tokens in and 600 out, so the fixture set of this metric costs a few cents on a small model. Run only after Joshua has approved the
spend, in stages of 3, 10 and 30 cases, with a call budget (esoi/metric-run-policy.md). Never run offline: the offline guard refuses its calls."""
from shared_fixtures.interface import model_arms
from shared_fixtures.interface import structure_fixture
from esoi.structure.structure_quality.interface import review
from esoi.structure.structure_quality.interface import load

PAID = True


def build(meter):
    ask = model_arms.provider(meter)

    def run(kind, args):
        report = review(load(structure_fixture.project(args["shape"])), lambda text: ask.answer([{"role": "user", "content": text}], model_arms.model() or None))
        return {"score": report["score"], "verdict": report["verdict"], "flagged": report["flagged"]}
    return run
