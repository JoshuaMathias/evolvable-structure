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


# ---- code evidence (M2): E2 counts executable code only, never prose -------------------------------------------------------

from types import SimpleNamespace


def code_for(tmp_path: Path, user_source: str, used_source: str = "class Finder:\n    pass\n", user_row=None):
    """A package `pk` with one module per solution `user` and `used` (used's interface class is Finder)."""
    pkg = tmp_path / "pk"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "user.py").write_text(user_source, encoding="utf-8")
    (pkg / "used.py").write_text(used_source, encoding="utf-8")
    cfg = SimpleNamespace(root=tmp_path, package="pk", package_dir="pk")
    solutions = {"user": {"solution_id": "user", "interface_name": "Runner"},
                 "used": {"solution_id": "used", "interface_name": "Finder"}}
    impls = [{"solution_id": "user", "implementation_id": "u1", "filepath": "pk/user.py"},
             {"solution_id": "used", "implementation_id": "c1", "filepath": "pk/used.py"}]
    selected = {"user": dict(impls[0], **(user_row or {})), "used": impls[1]}
    return coherence.Code(cfg, solutions, impls, selected)


def test_a_docstring_naming_the_used_id_or_interface_is_no_evidence(tmp_path):
    code = code_for(tmp_path, '"""Module doc: this relies on used and the Finder class."""\n\n\n'
                              'class Runner:\n    """Runs it with used (a Finder) behind it."""\n\n'
                              '    def go(self):\n        """Calls used."""\n        return 1\n')
    assert code.evidence("user", "used") == ""


def test_a_comment_naming_the_used_is_no_evidence(tmp_path):
    code = code_for(tmp_path, "# uses used through Finder\nvalue = 1  # used, Finder\n")
    assert code.evidence("user", "used") == ""


def test_a_bare_string_statement_is_no_evidence(tmp_path):
    code = code_for(tmp_path, 'value = 1\n"used and Finder are mentioned here"\n')
    assert code.evidence("user", "used") == ""


def test_the_same_id_as_a_string_value_in_a_call_is_strong(tmp_path):
    code = code_for(tmp_path, '"""Doc."""\n\n\ndef go(resolve):\n    return resolve("used")\n')
    assert code.evidence("user", "used") == "E2"


def test_the_interface_class_as_an_identifier_attribute_or_annotation_is_strong(tmp_path):
    assert code_for(tmp_path / "a", "def go(x):\n    return Finder(x)\n").evidence("user", "used") == "E2"
    assert code_for(tmp_path / "b", "def go(x):\n    return x.Finder\n").evidence("user", "used") == "E2"
    assert code_for(tmp_path / "c", "def go(x: 'Finder'):\n    return x\n").evidence("user", "used") == "E2"


def test_a_declared_uses_string_is_strong(tmp_path):
    code = code_for(tmp_path, 'ARM = dict(uses=["used"])\n')
    assert code.evidence("user", "used") == "E2"


def test_an_import_is_strong_evidence_e1(tmp_path):
    assert code_for(tmp_path, '"""Doc."""\nfrom pk import used\n').evidence("user", "used") == "E1"


def test_a_typed_need_is_strong_evidence_e3(tmp_path):
    source = "class Runner:\n    def __init__(self, finder: Finder):\n        self.finder = finder\n"
    code = code_for(tmp_path, source)
    assert code.typed_need("user", "used")                 # the need the Assembler injects
    assert code.evidence("user", "used") in coherence.STRONG


def test_a_module_that_does_not_parse_ignores_comment_lines(tmp_path):
    code = code_for(tmp_path, "# used Finder\ndef broken(:\n")
    assert code.evidence("user", "used") == ""
    assert code_for(tmp_path / "d", "def broken(:\n    run('used')\n").evidence("user", "used") == "E2"


def test_weak_evidence_is_unchanged_by_docstrings(tmp_path):
    code = code_for(tmp_path, '"""used."""\nfrom pk import hub\n')
    (tmp_path / "pk" / "hub.py").write_text("from pk import used\n", encoding="utf-8")
    code = coherence.Code(SimpleNamespace(root=tmp_path, package="pk", package_dir="pk"), {
        "user": {"solution_id": "user", "interface_name": "Runner"}, "used": {"solution_id": "used", "interface_name": "Finder"}},
        [{"solution_id": "user", "implementation_id": "u1", "filepath": "pk/user.py"},
         {"solution_id": "used", "implementation_id": "c1", "filepath": "pk/used.py"}], {})
    assert code.evidence("user", "used") == "W1"
