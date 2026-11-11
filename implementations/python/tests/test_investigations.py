"""Investigation records (docs/reference/knowledge-search-standard.md): the required parts per kind and size, counts that add up, grades,
decisions, applied entries and their grace period, refresh dates, knowledge with no search, and the solution page's list of reviews."""
import datetime
import sys
from pathlib import Path

import pytest

from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry.tables import read_csv, write_csv
from esoi.understanding.solution_consideration import experiments, investigations, knowledge

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation" / "components"))
from shared_fixtures.consideration_fixture import write_repo  # noqa: E402

DAY = datetime.date(2026, 11, 20)


@pytest.fixture
def toy(tmp_path):
    return config_module.load(write_repo(tmp_path / "toy"))


def folder_of(config):
    return knowledge.folder_of(config, "card-builder")


def record(**changes):
    row = {"investigation_id": "r-1", "kind": "review", "intent_id": "recall", "links": "solution:card-builder", "question": "Which graph libraries can build cards?",
           "decision": "adopt or build", "method": "web search against fixed criteria", "size": "quick", "protocol_date": "2026-11-10", "criteria": "open licence; maintained since 2025",
           "sources": "web search", "queries": "web | graph card builder | 2026-11-10 | 40", "done_on": "2026-11-10", "found": "40",
           "screened_out": "37 not a library;1 unmaintained", "kept": "2", "limitations": "titles and readmes only",
           "decisions": "libx: adopt: fits and is open;liby: reject: unmaintained", "refresh_on": "2027-02-10", "status": "open"}
    row.update(changes)
    return {c: row.get(c, "") for c in investigations.COLUMNS}


def item(item_id, **changes):
    row = {"investigation_id": "r-1", "item_id": item_id, "claim": "libx builds cards", "source": "https://example.org/x", "source_date": "2026-10-01",
           "independent": "yes", "verified": "opened", "licence": "MIT", "grade": "B", "knowledge_id": "", "applied": "implementation:card-builder:libx"}
    row.update(changes)
    return {c: row.get(c, "") for c in investigations.ITEM_COLUMNS}


def write(config, rows, items):
    folder = folder_of(config)
    write_csv(folder / investigations.FILE, investigations.COLUMNS, rows)
    write_csv(folder / investigations.ITEMS_FILE, investigations.ITEM_COLUMNS, items)


def advice(config, on=DAY):
    return [f"{k}: {t}" for k, t in investigations.advice(config, on)]


def advice_of(config, on=DAY):
    return [f"{k}: {t}" for k, t in experiments.advice(config, on)]


def test_a_complete_quick_record_has_no_advice(toy):
    write(toy, [record()], [item("i1"), item("i2", applied="not-applied: licence unclear")])
    assert advice(toy) == []


def test_each_missing_minimum_part_is_named(toy):
    write(toy, [record(criteria="", limitations="", refresh_on="")], [item("i1"), item("i2")])
    found = advice(toy)
    assert all(any(f"has no {c}" in line for line in found) for c in ("criteria", "limitations", "refresh_on"))


def test_a_standard_review_states_known_contested_and_unknown(toy):
    write(toy, [record(size="standard")], [item("i1"), item("i2")])
    assert sum("has no synthesis_" in line for line in advice(toy)) == 3
    write(toy, [record(size="standard", synthesis_known="a", synthesis_contested="b", synthesis_unknown="c")], [item("i1"), item("i2")])
    assert advice(toy) == []


def test_counts_must_add_up_and_the_protocol_precedes_the_work(toy):
    write(toy, [record(found="50", protocol_date="2026-11-12")], [item("i1"), item("i2")])
    found = advice(toy)
    assert any("less screened out 38 is not kept 2" in line for line in found)
    assert any("protocol_date is after done_on" in line for line in found)


def test_decisions_and_item_grades_are_checked(toy):
    write(toy, [record(decisions="libx: maybe: later")], [item("i1", grade="E"), item("i2", independent="sometimes", verified="glanced")])
    found = " | ".join(advice(toy))
    assert "decision 'libx: maybe: later'" in found and "item i1 has no grade" in found
    assert "item i2 independent" in found and "item i2 verified" in found


def test_findings_not_applied_after_the_grace_period_are_listed(toy):
    write(toy, [record()], [item("i1", applied=""), item("i2", applied="not-applied:")])
    assert advice(toy, datetime.date(2026, 11, 15)) == ["r-1: item i2 is marked not-applied with no reason"]
    late = advice(toy, DAY)
    assert "r-1: item i1 is neither applied nor marked not-applied after 7 days" in late
    write(toy, [record()], [item("i1", applied="notes:x"), item("i2")])
    assert any("applied entry 'notes:x'" in line for line in advice(toy))


def test_a_review_past_its_refresh_date_is_due(toy):
    write(toy, [record(refresh_on="2026-11-18"), record(investigation_id="r-2", refresh_on="2026-12-01"),
                record(investigation_id="r-3", refresh_on="2026-11-01", status="superseded")], [])
    assert [r["investigation_id"] for r in investigations.due(toy, DAY)] == ["r-1"]


def test_knowledge_citing_an_address_names_its_search(toy):
    folder = folder_of(toy)
    rows = read_csv(folder / knowledge.FILE)
    new = {c: "" for c in knowledge.COLUMNS}
    new.update(knowledge_id="k-new", claim="libx builds cards", kind="evidence", source="url:https://example.org/x grade B",
               solution_ids="card-builder", status="active", recorded="2026-11-12")
    old = dict(new, knowledge_id="k-old", recorded="2026-11-09")
    linked = dict(new, knowledge_id="k-linked", investigation_id="r-1")
    write_csv(folder / knowledge.FILE, knowledge.COLUMNS, rows + [new, old, linked])
    write(toy, [record()], [item("i1"), item("i2")])
    assert investigations.uninvestigated_knowledge(toy) == ["k-new"]
    assert any(line.startswith("k-new:") for line in advice(toy))
    dangling = dict(new, knowledge_id="k-dangling", investigation_id="r-404", recorded="2026-11-01")
    write_csv(folder / knowledge.FILE, knowledge.COLUMNS, rows + [dangling])
    assert any("investigation r-404, which has no row" in line for line in advice(toy))


def test_the_solution_page_lists_its_reviews_and_what_they_changed(toy):
    write(toy, [record()], [item("i1"), item("i2", applied="not-applied: licence unclear")])
    lines = investigations.readme_lines(toy, ["card-builder"], "###")
    assert lines[0] == "### Investigations behind the knowledge" and "i1: implementation:card-builder:libx" in lines[2]
    assert "i2: not-applied: licence unclear" in lines[2]
    assert investigations.readme_lines(toy, ["card-store"]) == []


def experiment(**changes):
    row = {"experiment_id": "x-1", "intent_id": "recall", "name": "Coarse cards", "research_question": "Is the card set too coarse for recall?",
           "status": "running", "starts_on": "2026-11-10", "reevaluate_time": "2026-12-10", "held_fixed": "storage = local",
           "in_scope": "card size and grouping", "outside_scope": "storage"}
    row.update(changes)
    return {c: row.get(c, "") for c in experiments.COLUMNS}


def write_experiments(config, rows):
    write_csv(folder_of(config) / experiments.FILE, experiments.COLUMNS, rows)


def test_a_running_experiment_names_its_research_question_period_and_what_is_held_fixed(toy):
    write_experiments(toy, [experiment()])
    assert advice_of(toy) == []
    write_experiments(toy, [experiment(research_question="", reevaluate_time="", held_fixed="")])
    found = " | ".join(advice_of(toy))
    assert "has no research_question" in found and "names no reevaluate_time or reevaluate_condition" in found and "holds nothing fixed" in found


def test_a_reevaluation_comes_due_and_an_ended_experiment_says_what_was_learned(toy):
    write_experiments(toy, [experiment(), experiment(experiment_id="x-2", status="ended")])
    assert [r["experiment_id"] for r in experiments.due(toy, datetime.date(2026, 12, 10))] == ["x-1"]
    assert any("x-1: reevaluation was due 2026-12-10" in line for line in advice_of(toy, datetime.date(2026, 12, 11)))
    found = " | ".join(advice_of(toy))
    assert "x-2: is ended but has no learned" in found and "has no decision" in found


def test_several_experiments_coexist_unless_one_person_fixes_contradictory_things(toy):
    mine = experiment(owners="a person", held_fixed="storage = local")
    write_experiments(toy, [mine, experiment(experiment_id="x-2", owners="a person", held_fixed="storage = remote"),
                            experiment(experiment_id="x-3", owners="someone else", held_fixed="storage = remote")])
    found = advice_of(toy)
    assert len([line for line in found if "fixes storage" in line]) == 1 and "x-1" in found[0]
    assert [r["experiment_id"] for r in experiments.running(toy, owners="a person")] == ["x-1", "x-2"]
    assert len(experiments.running(toy, intent_id="recall")) == 3


def test_the_intent_page_shows_its_experiments_and_a_missing_file_is_valid(toy):
    assert experiments.readme_lines(toy, "recall") == [] and experiments.advice(toy) == []
    write_experiments(toy, [experiment()])
    lines = experiments.readme_lines(toy, "recall", "###")
    assert lines[0] == "### Experiments" and "Held fixed: storage = local." in lines[2]


def test_a_qualitative_trial_needs_no_number_and_names_its_experiment(toy):
    trial = record(investigation_id="t-1", kind="observation", experiment_id="x-1", size="quick", links="solution:recall", found="", screened_out="", kept="",
                   criteria="", sources="", queries="", decisions="", decision="", observe="what the person does when cards are grouped",
                   change_my_mind="if grouping is never used")
    write_experiments(toy, [experiment()])
    write(toy, [trial], [item("i1", investigation_id="t-1", grade="", independent="", verified="observed", licence="",
                                          applied="knowledge:k-1")])
    assert advice(toy) == []
    write_experiments(toy, [])
    assert any("names experiment x-1, which has no row in experiments.csv" in line for line in advice(toy))


def test_every_investigation_names_a_solution_and_a_comparison_links_to_many(toy):
    write(toy, [record(links="")], [item("i1"), item("i2")])
    assert advice(toy) == ["r-1: names no solution; link it to the solution it informs, or going up, to the solution its intent implements "
                           "(docs/reference/knowledge-search-standard.md)"]
    write(toy, [record(links="ideal:recall-fast")], [item("i1"), item("i2")])
    assert any("names no solution" in line for line in advice(toy))
    write(toy, [record(links="solution:card-builder;solution:card-store;ideal:recall-fast")], [item("i1"), item("i2")])
    assert advice(toy) == []
    assert investigations.linked({"links": "solution:a;ideal:b;solution:c"}, "solution") == ["a", "c"]
    write(toy, [record(links="thing:x")], [item("i1"), item("i2")])
    assert any("link 'thing:x'" in line for line in advice(toy))


def test_the_lookup_reads_a_solution_and_its_ancestors_newest_first(toy):
    assert investigations.ancestors(toy, "card-builder") == ["recall"] and investigations.ancestors(toy, "recall") == []
    write(toy, [record(investigation_id="old", links="solution:recall", done_on="2026-10-01"),
                record(investigation_id="mid", links="solution:card-builder", done_on="2026-11-01"),
                record(investigation_id="new", links="solution:card-builder;solution:card-store", done_on="2026-11-09"),
                record(investigation_id="other", links="solution:card-store", done_on="2026-11-05")], [])
    own = investigations.on_solution(toy, "card-builder", on=DAY)
    assert [r["investigation_id"] for r in own] == ["new", "mid"]
    both = investigations.on_solution(toy, "card-builder", with_ancestors=True, on=DAY)
    assert [(r["investigation_id"], r["via"]) for r in both] == [("new", "card-builder"), ("mid", "card-builder"), ("old", "recall")]
    assert [r["investigation_id"] for r in investigations.on_solution(toy, "recall", with_ancestors=True, on=DAY)] == ["old"]


def test_the_lookup_marks_each_investigation_fresh_or_past_its_refresh_date(toy):
    write(toy, [record(investigation_id="fresh", refresh_on="2027-02-10"), record(investigation_id="stale", refresh_on="2026-11-15"),
                record(investigation_id="gone", refresh_on="2027-02-10", status="superseded")], [])
    marks = {r["investigation_id"]: r["fresh"] for r in investigations.on_solution(toy, "card-builder", on=DAY)}
    assert marks == {"fresh": "yes", "stale": "no", "gone": "no"}


def test_many_investigations_on_a_top_level_solution_suggest_a_missing_solution(toy):
    top = [record(investigation_id=f"t-{n}", links="solution:recall") for n in range(investigations.PILE_UP)]
    write(toy, top, [])
    assert investigations.pile_ups(toy) == [("recall", investigations.PILE_UP)]
    assert any("top-level solution recall" in line and "a solution may be missing" in line for line in advice(toy))
    write(toy, top[:-1], [])
    assert investigations.pile_ups(toy) == []
    write(toy, top[:-1] + [record(investigation_id="t-n", links="solution:recall;solution:card-builder")], [])
    assert investigations.pile_ups(toy) == []


def test_running_experiments_are_ordered_and_shown_first_on_the_intent_page(toy):
    write_experiments(toy, [experiment(experiment_id="x-b", name="Second", priority="2"), experiment(experiment_id="x-a", name="First", priority="1"),
                            experiment(experiment_id="x-z", status="planned", priority="1")])
    assert [r["experiment_id"] for r in experiments.running(toy, "recall")] == ["x-a", "x-b"]
    lines = experiments.running_lines(toy, "recall")
    assert lines[0] == "## Running experiments" and lines[2].startswith("1. `x-a` First") and "(reevaluate 2026-12-10)" in lines[2]
    assert experiments.running_lines(toy, "another-intent") == []


def test_two_running_experiments_of_an_intent_sharing_a_priority_are_advised(toy):
    write_experiments(toy, [experiment(experiment_id="x-a", priority="1"), experiment(experiment_id="x-b", priority="1", name="Other")])
    assert any("shares priority 1 with running experiment(s) x-b" in line for line in advice_of(toy))
    write_experiments(toy, [experiment(experiment_id="x-a", priority="0")])
    assert any("priority is a whole number from 1" in line for line in advice_of(toy))


def test_files_and_columns_named_before_the_rename_are_still_read(toy):
    old_columns = ["research_id"] + investigations.COLUMNS[1:]
    write_csv(folder_of(toy) / investigations.LEGACY_FILE, old_columns, [dict(record(), research_id="r-old")])
    write_csv(folder_of(toy) / investigations.LEGACY_ITEMS_FILE, ["research_id"] + investigations.ITEM_COLUMNS[1:],
              [dict(item("i1"), research_id="r-old")])
    assert [r["investigation_id"] for r in investigations.rows(toy)] == ["r-old"]
    assert [r["investigation_id"] for r in investigations.item_rows(toy)] == ["r-old"]


def test_the_top_page_lists_every_intents_running_experiments_in_priority_order(toy, monkeypatch):
    """The repository's top page is where its research directions are in order: the top intent's, then each sub-intent's, each in its own priority order."""
    from types import SimpleNamespace
    write_experiments(toy, [experiment(experiment_id="x-b", name="Second", priority="2"), experiment(experiment_id="x-a", name="First", priority="1")])
    sub = [experiment(experiment_id="y-1", intent_id="sub", name="Below", priority="1")]
    real = experiments.running
    monkeypatch.setattr(experiments, "running", lambda config, intent_id="", owners="": sub if intent_id == "sub" else real(config, intent_id, owners))
    monkeypatch.setattr(experiments.intents, "discover", lambda config: [SimpleNamespace(intent_id="recall"), SimpleNamespace(intent_id="sub")])
    lines = experiments.running_lines(toy, "recall", whole_tree=True)
    assert [line.split(" ")[:2] for line in lines[2:5]] == [["1.", "`x-a`"], ["2.", "`x-b`"], ["3.", "`y-1`"]]
    assert "(intent `sub`)" in lines[4] and "(intent `sub`)" not in lines[2]
    assert experiments.running_lines(toy, "recall") == experiments.running_lines(toy, "recall", whole_tree=False) and len(experiments.running_lines(toy, "recall")) == 5
