"""The slice of the specification a task serves: found with no model and no guessing.

A clear solution, its next open milestone, the one metric that measures it. A throwaway repository written by
``esoi.scaffold.init`` stands in for a real one, so the records, the results log and the evaluation component are the real
shapes. Offline: no model, no network.
"""
import csv
import time
from pathlib import Path

import pytest

from esoi import scaffold, spec_slice
from esoi.spec_slice import (
    Chosen, RepoSliceSource, SpecSlice, lexical_choice, next_milestone, next_priority_block, parse_milestones, solutions_of,
    target_of)

GREETING = "make the greeting function greet a person by name in the standard form"


@pytest.fixture
def greet_repo(tmp_path):
    """A scaffolded esoi repository whose one measured solution is greet-a-person (arm ``live``, recorded 2 of 2)."""
    root = tmp_path / "repo"
    scaffold.init(root, "demo_pkg", say=lambda *_: None)
    return root


def edit_milestones(root: Path, text: str) -> None:
    path = root / "esoi" / "solutions.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row["solution_id"] == "greet-a-person":
            row["milestones"] = text
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def slice_of(root: Path) -> SpecSlice:
    return SpecSlice(root=str(root), solution_id="greet-a-person", metric_id="greeting-pass-rate",
                     metric_command="esoi run greet_a_person --impl live")


# -- reading the milestones --------------------------------------------------------------------

def test_milestones_are_the_numbered_items_in_order():
    items = parse_milestones("1. First thing: 100%. 2. Second thing. 3. Third thing on 2026-10-19. 4 of them.")
    assert [(m.number, m.text) for m in items] == [
        (1, "First thing: 100%."), (2, "Second thing."), (3, "Third thing on 2026-10-19. 4 of them.")]


def test_an_unnumbered_cell_is_one_milestone_and_an_empty_one_is_none():
    assert [m.text for m in parse_milestones("Reach the target.")] == ["Reach the target."]
    assert parse_milestones("") == [] and next_milestone("   ") is None


def test_the_next_milestone_is_the_first_one_not_archived():
    cell = "1. Archived: an old goal. 2. (archived) another. 3. The real next one at 50%. 4. After that."
    step = next_milestone(cell)
    assert (step.number, step.text) == (3, "The real next one at 50%.")
    assert next_milestone("1. Archived: only one.") is None


def test_a_met_milestone_is_not_the_next_one_and_is_not_shown_in_its_text():
    cell = "1. First one: 100%. [met: 2026-10-26] 2. Second one at 50%. 3. Third."
    assert [(m.number, m.met) for m in parse_milestones(cell)] == [(1, True), (2, False), (3, False)]
    assert next_milestone(cell).text == "Second one at 50%."
    assert next_milestone("1. Only one. [met]") is None


def test_a_target_is_a_number_only_when_the_milestone_holds_exactly_one():
    assert target_of("Share of cases passed: 100%.") == (1.0, "100%")
    assert target_of("Latency under 2.5 seconds") == (2.5, "2.5")
    assert target_of("recorded for 3, then 10, then 30 runs") == (None, "")
    assert target_of("no number here") == (None, "")
    assert target_of("set on 2026-10-19") == (None, "")


# -- finding the slice -------------------------------------------------------------------------

def test_a_clear_request_gets_the_solution_its_next_milestone_and_its_metric(greet_repo):
    found = RepoSliceSource().slice_for(GREETING, str(greet_repo))
    assert (found.solution_id, found.metric_id, found.milestone_number) == ("greet-a-person", "greeting-pass-rate", 1)
    assert found.milestone.startswith("Share of sample names") and (found.target, found.target_text) == (1.0, "100%")
    assert found.metric_name == "Greeting pass rate" and found.metric_command == "esoi run greet_a_person --impl live"
    assert "root" not in found.to_dict()


def test_archived_milestones_are_skipped_in_the_repository_too(greet_repo):
    edit_milestones(greet_repo, "1. Archived: done long ago. 2. Greetings keep the name: 50%.")
    found = RepoSliceSource().slice_for(GREETING, str(greet_repo))
    assert (found.milestone_number, found.target) == (2, 0.5)


def test_no_slice_outside_a_repository_with_records_or_without_a_folder(greet_repo, tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    assert RepoSliceSource().slice_for(GREETING, str(bare)) is None
    assert RepoSliceSource().slice_for(GREETING, None) is None   # no folder to look from: no guess about where


def test_an_unclear_or_unrelated_request_gets_no_slice_rather_than_a_wrong_one(greet_repo):
    assert RepoSliceSource().slice_for("write a poem about the sea", str(greet_repo)) is None
    assert RepoSliceSource().slice_for("", str(greet_repo)) is None


def test_the_default_chooser_is_lexical_and_a_failing_lookup_gives_none(greet_repo, monkeypatch):
    assert RepoSliceSource().slice_for(GREETING, str(greet_repo)) is not None
    monkeypatch.setattr(spec_slice.spec_index, "build", lambda config: (_ for _ in ()).throw(RuntimeError("boom")))
    assert RepoSliceSource().slice_for(GREETING, str(greet_repo)) is None


def test_a_cache_folder_keeps_the_index_between_calls(greet_repo, tmp_path):
    cache = tmp_path / "cache"
    source = RepoSliceSource(cache_dir=cache)
    assert source.slice_for(GREETING, str(greet_repo)) is not None
    assert len(list(cache.glob("*.json"))) == 1
    assert source.slice_for(GREETING, str(greet_repo)).solution_id == "greet-a-person"


def test_a_chooser_that_is_sure_settles_on_its_best_solution_and_an_unsure_one_needs_a_single_solution(greet_repo):
    from esoi import config, spec_index
    index = spec_index.build(config.load(greet_repo))
    solutions = [e["id"] for e in index["entries"] if e["kind"] == "solution"]
    assert len(solutions) >= 2
    assert solutions_of(Chosen(tuple(solutions), sure=True), index) == solutions[:1]
    assert solutions_of(Chosen(tuple(solutions)), index) == []
    assert solutions_of(Chosen((solutions[0], solutions[0])), index) == solutions[:1]
    assert solutions_of(Chosen(("no-such-record",)), index) == []
    pinned = RepoSliceSource(choose=lambda request, found: Chosen(("greet-a-person",), sure=True))
    assert pinned.slice_for("anything at all", str(greet_repo)).solution_id == "greet-a-person"
    assert lexical_choice("", index) == Chosen() and lexical_choice("write a poem about the sea", index) == Chosen()


def test_the_folder_to_look_from_is_the_callers_to_name(greet_repo, tmp_path):
    elsewhere = lambda working_dir: greet_repo   # noqa: E731  a consumer that names the repository itself
    source = RepoSliceSource(find_root=elsewhere)
    assert source.slice_for(GREETING, None).solution_id == "greet-a-person"
    assert source.slice_for(GREETING, str(tmp_path)).solution_id == "greet-a-person"


def test_a_slow_lookup_is_given_up_on(greet_repo, monkeypatch):
    monkeypatch.setattr(spec_slice, "slice_from_root", lambda *args: time.sleep(5))
    started = time.monotonic()
    assert RepoSliceSource(timeout_seconds=0.2).slice_for(GREETING, str(greet_repo)) is None
    assert time.monotonic() - started < 2


def test_the_brief_block_names_the_milestone_the_metric_and_the_tool(greet_repo):
    found = RepoSliceSource().slice_for(GREETING, str(greet_repo))
    block = next_priority_block(found)
    assert block.startswith("NEXT PRIORITY") and "Share of sample names" in block
    assert "Greeting pass rate (metric_id greeting-pass-rate)" in block
    assert "Record" not in block and chr(0x2014) not in block   # the closing words are the consumer's
    assert next_priority_block(found, "Record it with the tool.").endswith("\nRecord it with the tool.")
    assert len(block) < 700   # short: it rides in every brief of a repository that has records
    assert "none is set" in next_priority_block(SpecSlice(root="/x", solution_id="s", metric_id="m"))


