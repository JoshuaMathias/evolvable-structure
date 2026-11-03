"""esoi.coherence's paragraph check (rule S39): an edge counts only when one clause names the user before the used with words of
its own; lists of names, used-first wording and one template per edge fail. Runs on the scaffold `esoi init` writes."""
import csv
from pathlib import Path

import pytest

from esoi import coherence, scaffold


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    scaffold.init(tmp_path, package="demo", say=lambda text: None)
    return tmp_path


def paragraph_problems(root: Path, text: str):
    path = root / "esoi" / "intent.csv"
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    rows[0]["solution_coherence"] = text
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return coherence.check(root, pairs=False)["intents"][0]["problems"].get("paragraph", [])


def test_user_first_clauses_with_their_own_words_pass(project):
    assert paragraph_problems(project, "project-purpose greets each person through greet-a-person and keeps its intent "
                                       "checked in one place through project-structure.") == []


def test_a_clause_opening_with_it_speaks_of_the_solution_before_it(project):
    assert paragraph_problems(project, "project-purpose greets each person through greet-a-person. It keeps its intent "
                                       "checked in one place through project-structure.") == []


def test_a_list_of_names_states_no_edge(project):
    found = paragraph_problems(project, "This project has project-purpose, greet-a-person and project-structure.")
    assert any("not stated user first" in line for line in found)


def test_naming_the_used_solution_first_does_not_count(project):
    found = paragraph_problems(project, "greet-a-person is what project-purpose relies on to greet. project-structure is "
                                        "what project-purpose relies on for its records.")
    assert any("not stated user first" in line for line in found)


def test_two_words_between_the_names_are_not_enough(project):
    found = paragraph_problems(project, "project-purpose uses greet-a-person. project-purpose uses project-structure.")
    assert any("not stated user first" in line for line in found)
