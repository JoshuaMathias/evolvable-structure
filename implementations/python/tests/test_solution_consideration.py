"""Solution Consideration and Solution Relevance: the prompt formed from a solution's network, its order and budget, the fan-out, the
finding files and rule S60, over a small synthetic repository shaped like the incident that motivated them."""
import json
import sys
from pathlib import Path

import pytest

from esoi import __main__ as cli
from esoi.optimization.leaderboard import results_log
from esoi.structure.intent_registry import config as config_module, registry
from esoi.structure.intent_registry.tables import read_csv, write_csv
from esoi.structure.structure_check.rules import consideration_rules
from esoi.structure.structure_check.rules.base import Context
from esoi.understanding.solution_consideration import fan_out, knowledge, network_records, solution_prompt
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
    lines = [line for line in lines if line.startswith("S60")]
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


def test_knowledge_is_offered_beside_the_stable_prompt_not_dumped_into_it(net):
    made = solution_prompt.prompt(net, "card-builder")
    assert [i["id"] for i in made["knowledge"]] == ["k-cb-2", "k-cb-1", "k-cb-4", "k-cb-6", "k-cb-3"]
    assert {i["id"]: i["status"] for i in made["knowledge_inactive"]} == {"k-cb-5": "contradicted", "k-cb-7": "expired"}
    assert "Graph groups lost to import cards" not in made["text"] and "5 knowledge item(s) are offered" in made["text"]
    ranked = solution_prompt.prompt(net, "card-builder", knowledge="ranked")["text"]
    assert "k-cb-5 (theory; evidence, grade D) [CONTRADICTED by k-cb-1]" in ranked
    assert "knowledge" not in solution_prompt.prompt(net, "card-builder", knowledge="none")
    with pytest.raises(ValueError):
        solution_prompt.prompt(net, "card-builder", knowledge="everything")


def test_the_situation_chooses_the_knowledge(net):
    active, _ = knowledge.items(net, "card-builder")
    assert [i["id"] for i in knowledge.select(active, "Should we adopt the graph tool for building cards?")][0] == "k-cb-1"
    assert "k-cb-6" not in [i["id"] for i in knowledge.select(active, "Should each file get its own card?")]
    assert knowledge.select(active, "") == []


def test_sources_are_read_by_kind():
    assert knowledge.source_kind("result:cards/graph@2026-01-02") == ("result", "")
    assert knowledge.source_kind("url:https://example.org grade B") == ("evidence", "B")
    assert knowledge.source_kind('person:the owner, 2026-01-01: "yes"')[0] == "person"
    assert knowledge.source_kind("mistake:M-1")[0] == "mistake"


def test_add_is_ensure_one_and_migrate_moves_free_text(toy):
    found, created = knowledge.add(toy, {"claim": "Cards age.", "kind": "lesson", "source": "mistake:M-2", "solution_ids": ["card-store"]})
    assert created and found.startswith("k-card-store-")
    assert knowledge.add(toy, {"claim": "Cards  age.", "kind": "lesson", "source": "x", "solution_ids": ["card-store"]}) == (found, False)
    with pytest.raises(ValueError):
        knowledge.add(toy, {"claim": "No source.", "solution_ids": ["card-store"]})
    path = toy.root / "esoi" / "recall_parts" / "solutions.csv"
    rows = read_csv(path)
    rows[1]["knowledge"] = "[lesson] Ids last. (source: mistake:M-3)"
    write_csv(path, list(rows[0]), rows)
    assert knowledge.migrate(toy) == ["card-store: 1 item(s) -> new"] and "knowledge.csv:" not in path.read_text()
    assert knowledge.migrate(toy, apply=True) == ["card-store: 1 item(s) -> k-card-store-2"]
    assert "knowledge.csv: k-card-store-2" in path.read_text() and knowledge.migrate(toy) == []
    assert any(i["id"] == "k-card-store-2" and i["kind"] == "lesson" and i["source"] == "mistake:M-3" for i in knowledge.all_items(toy))


def test_s61_flags_a_missing_source_an_expired_item_and_a_newer_result(toy):
    lines = [line for line in rule_lines(toy) if line.startswith("S61")]
    assert lines == ["S61 k-cb-7: expired on 2025-06-30; renew it with a new source or set its status to expired"]
    results = toy.root / "esoi" / "results.csv"
    results.write_text(results.read_text() + "2026-02-01,card_builder,graph_groups,63,40,,,0,0,0,0.0,50,bbbbbbb,c1,none,,,0.7\n")
    path = toy.root / "esoi" / "recall_parts" / "knowledge.csv"
    path.write_text(path.read_text() + "k-cb-8,An unsourced claim.,lesson,,card-builder,active,,,\n")
    found = [line for line in rule_lines(toy) if line.startswith("S61")]
    assert any("S61 k-cb-1: a newer result may contradict it" in line for line in found)
    assert any("S61 k-cb-8: has no source" in line for line in found)


def test_cards_carry_kind_and_source_and_the_stable_part_is_managed(toy, capsys):
    assert cli.main(["--config", str(toy.root), "knowledge", "cards", "--solution", "card-builder"]) == 0
    out = json.loads(capsys.readouterr().out)
    stable, *items = out["cards"]
    assert stable["id"] == "solution-card-builder" and "content" in stable["managed_fields"]
    assert {c["id"] for c in items} == {"knowledge-k-cb-1", "knowledge-k-cb-2", "knowledge-k-cb-3", "knowledge-k-cb-4", "knowledge-k-cb-6"}
    assert all(c["tags"][0] == "solution:card-builder" and c["source"] for c in items)
    assert {c["status"] for c in out["quarantine"]} == {"contradicted", "expired"}
