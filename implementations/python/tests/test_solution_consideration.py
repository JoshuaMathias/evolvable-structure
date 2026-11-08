"""Solution Consideration and Solution Relevance: the prompt formed from a solution's network, its order and budget, the fan-out, the
finding files and rule S60, over a small synthetic repository shaped like the incident that motivated them."""
import json
import sys
from pathlib import Path

import pytest

from esoi import __main__ as cli
from esoi.optimization.leaderboard import results_log
from esoi.structure.intent_registry import config as config_module, registry
from esoi.structure.structure_check.rules import consideration_rules
from esoi.structure.structure_check.rules.base import Context
from esoi.understanding.solution_consideration import fan_out, network_records, solution_prompt
from esoi.understanding.solution_relevance import relevance, relevance_cases
from esoi.understanding.spec_search import spec_index

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation" / "components"))
from shared_fixtures.consideration_fixture import write_repo  # noqa: E402


@pytest.fixture
def toy(tmp_path):
    root = write_repo(tmp_path / "toy")
    return config_module.load(root)


@pytest.fixture
def net(toy):
    return solution_prompt.load(toy, stale=False)


def test_the_losing_result_and_the_finding_reach_the_prompt(net):
    text = solution_prompt.prompt(net, "card-builder", "Adopt Graph groups?")["text"]
    assert "graph_groups: passed 3 of 63" in text and "import_cards [selected]: passed 43 of 63" in text
    assert "F-2" in text and "The matter to consider: Adopt Graph groups?" in text
    assert text.index("## Recorded results") < text.index("## Findings and candidates") < text.index("## Parent")


def test_edges_are_read_at_their_depth(net):
    builder = solution_prompt.prompt(net, "card-builder")
    assert builder["parent"] == "recall" and builder["children"] == []
    assert "Card Store (card-store): Keep cards" in builder["text"] and "Selected: local_store" in builder["text"]
    assert "Card Builder (card-builder) delegates to it" in solution_prompt.prompt(net, "card-store")["text"]


def test_a_parent_is_judged_on_how_its_children_combine(net):
    made = solution_prompt.prompt(net, "recall")
    assert made["children"] == ["card-builder", "card-store"]
    assert "## How its children combine" in made["text"] and "Card Builder -> Card Store" in made["text"]


@pytest.mark.parametrize("budget", [900, 1500, 2200])
def test_the_budget_holds_and_cuts_far_records_first(net, budget):
    made = solution_prompt.prompt(net, "card-builder", "", budget)
    assert made["chars"] <= budget
    cut = {o["section"] for o in made["omitted"]}
    if "Recorded results" in cut:
        assert "Dependencies" in cut and "Parent (the scope above)" in cut
    assert all(o["tier"] >= 0 for o in made["omitted"])


def test_an_unknown_solution_is_a_key_error(net):
    with pytest.raises(KeyError):
        solution_prompt.prompt(net, "no-such-solution")


def test_fan_out_names_solutions_then_their_parents(toy, net):
    index = spec_index.build(toy)
    found = fan_out.consider(net, index, "card builder groups files into cards", limit=3)
    roles = [(p["solution_id"], p["role"]) for p in found["prompts"]]
    assert roles[0] == ("card-builder", "solution") and ("recall", "parent") in roles
    assert [r for _, r in roles].index("parent") > [r for _, r in roles].index("solution")
    named = fan_out.consider(net, index, "", only=["card-store"])
    assert [p["solution_id"] for p in named["prompts"]] == ["card-store", "recall"]


def test_relevance_arms_and_the_shared_scorer(toy, net):
    index = spec_index.build(toy)
    for arm in relevance.ARMS:
        assert relevance.ARMS[arm](index, "graph groups", 3)[0]["solution_id"] == "card-builder"
    returned = [{"solution_id": "card-builder", "role": "solution"}, {"solution_id": "card-store", "role": "solution"},
                {"solution_id": "recall", "role": "parent"}]
    judged = relevance_cases.judge(["card-builder", "recall"], returned)
    assert judged == {"recall": 1.0, "precision": 0.5, "missed": [], "ok": True}
    assert relevance_cases.judge(["card-store"], returned[:1])["missed"] == ["card-store"]


def test_a_candidate_reaches_the_solution_of_the_implementation_it_names(toy):
    loaded = registry.load(toy)
    record = network_records.RecordFile(Path("x.csv"), "finding", "id", "", "candidate")
    reached = network_records.row_solutions(record, {"id": "1", "candidate": "Graph"}, loaded.implementations, {}, set())
    assert reached == {"card-builder": "candidate Graph is implementation card-builder:graph_groups"}
    assert network_records.candidate_words("any-llm") == set()


def rule_lines(cfg):
    ctx = Context(cfg, registry.load(cfg), [], {}, {}, history=results_log.all_results(cfg.results_path))
    return consideration_rules.run(ctx)


def test_s60_asks_a_rating_to_cite_the_recorded_results(toy):
    lines = rule_lines(toy)
    assert len(lines) == 1 and lines[0].startswith("S60 registry/findings.csv F-1: rated against card-builder")
    path = toy.root / "registry" / "findings.csv"
    path.write_text(path.read_text() + "F-3,card-builder;card-store,,0.5,both (esoi/results.csv)\n")
    assert any("F-3: one row rates 2 solutions" in line for line in rule_lines(toy))


def test_s60_needs_a_solution_column(toy):
    path = toy.root / "registry" / "findings.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join(line.replace("solution_id,", "area,", 1) for line in lines) + "\n")
    assert any("no column names the solution" in line for line in rule_lines(toy))


def test_the_command_line_prints_a_prompt_and_the_fan_out(toy, capsys):
    root = str(toy.root)
    assert cli.main(["--config", root, "spec", "prompt", "card-builder", "--no-stale", "--budget", "4000"]) == 0
    assert "graph_groups: passed 3 of 63" in capsys.readouterr().out
    assert cli.main(["--config", root, "consider", "graph groups cards", "--no-stale"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["prompts"][0]["solution_id"] == "card-builder"
    assert cli.main(["--config", root, "spec", "prompt", "nothing", "--no-stale"]) == 1
