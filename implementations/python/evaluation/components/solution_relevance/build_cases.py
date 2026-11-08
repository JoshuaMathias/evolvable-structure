"""Write ``cases.json``: the hand-labelled cases of ``hand_cases.json`` and the cases mined from this repository's git history.

Run it deliberately (``python build_cases.py``) when the history has grown enough to be worth a new case set; the case digest
then changes and every arm is re-run on the new set. The miner is ``esoi.understanding.solution_relevance.relevance_cases.mine``.
"""
import json
from pathlib import Path

from esoi.structure.intent_registry import config as config_module, registry
from esoi.understanding.solution_relevance import relevance_cases

HERE = Path(__file__).resolve().parent


def main() -> None:
    config = config_module.load(next(p for p in HERE.parents if (p / "esoi.toml").is_file()))
    hand = json.loads((HERE / "hand_cases.json").read_text(encoding="utf-8"))
    cases = relevance_cases.build(config, registry.load(config), hand)
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases ({len(hand)} by hand)")


if __name__ == "__main__":
    main()
