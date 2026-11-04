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


# ---- evidence is attributed per solution in a module several solutions share ---------------------------------------------------

def shared_code(tmp_path: Path, shared_source: str, extra: dict = None):
    """A package `pk` whose module `shared.py` holds the arms of three solutions a, b and c (interfaces A, B and C); `extra` adds
    modules (name -> source) that are no solution's."""
    pkg = tmp_path / "pk"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "shared.py").write_text(shared_source, encoding="utf-8")
    for name, source in (extra or {}).items():
        (pkg / f"{name}.py").write_text(source, encoding="utf-8")
    cfg = SimpleNamespace(root=tmp_path, package="pk", package_dir="pk")
    solutions = {s: {"solution_id": s, "interface_name": s.upper()} for s in "abc"}
    impls = [{"solution_id": s, "implementation_id": f"{s}1", "filepath": "pk/shared.py"} for s in "abc"]
    return coherence.Code(cfg, solutions, impls, {s: impls[i] for i, s in enumerate("abc")})


SHARED = '''
from .runtime import implementation, solution


@solution("a")
class A:
    pass


@solution("b")
class B:
    pass


@solution("c")
class C:
    pass


@implementation("a", "a1")
class AArm:
    def __init__(self, other: B):
        self.other = other


@implementation("b", "b1")
class BArm:
    def go(self):
        return 1


@implementation("c", "c1")
class CArm:
    def go(self):
        return 2
'''


def test_two_arms_in_one_module_are_evidence_only_for_the_pair_their_own_class_shows(tmp_path):
    code = shared_code(tmp_path, SHARED)
    assert code.evidence("a", "b") == "E2"                 # a's own class is typed with b's interface
    assert code.evidence("a", "c") == ""                   # the same file names c, but not through a's class
    assert code.evidence("b", "a") == ""
    assert code.evidence("c", "b") == ""


def test_a_shared_module_that_names_every_interface_no_longer_gives_every_pair_evidence(tmp_path):
    code = shared_code(tmp_path, SHARED)
    pairs = [(x, y) for x in "abc" for y in "abc" if x != y]
    strong = [p for p in pairs if code.evidence(*p) in coherence.STRONG]
    assert strong == [("a", "b")]                          # per module it was all six


def test_a_lazy_import_inside_an_arm_is_evidence_for_that_arm_only(tmp_path):
    source = SHARED.replace("    def go(self):\n        return 1\n", "    def go(self):\n        from . import helper\n        return helper.x\n", 1)
    code = shared_code(tmp_path, source, {"helper": "x = 1\n"})
    code.modules["helper_sol"] = {"pk.helper"}
    assert code.evidence("b", "helper_sol") == "E1"
    assert code.evidence("c", "helper_sol") == ""


def test_importing_a_shared_file_without_the_used_class_is_not_evidence(tmp_path):
    user = "from . import shared\n\n\ndef go():\n    return shared\n"
    code = shared_code(tmp_path, SHARED, {"user": user})
    code.modules["u"] = {"pk.user"}
    code.interface["u"] = "U"
    assert code.evidence("u", "b") == ""
    user_named = "from .shared import BArm\n\n\ndef go():\n    return BArm\n"
    again = shared_code(tmp_path / "again", SHARED, {"user": user_named})
    again.modules["u"] = {"pk.user"}
    again.interface["u"] = "U"
    assert again.evidence("u", "b") == "E1"


def test_a_module_with_no_declared_classes_is_scored_whole(tmp_path):
    plain = "\n".join(line for line in SHARED.splitlines() if not line.startswith("@"))
    code = shared_code(tmp_path, plain)
    assert code.evidence("a", "b") == "E2"                 # a declares no class here, so the file counts for it as before


# Per-intent limits: [rules.S38.floors.<intent>] min_lift, max_fan_out, max_names_per_sentence over the repository-wide values.

def cfg_with(**s38):
    return SimpleNamespace(option=lambda rule, key, default=None: s38.get(key, default) if rule == "S38" else default)


def test_a_per_intent_limit_beats_the_repository_wide_value():
    cfg = cfg_with(min_lift=1.0, max_fan_out=9, floors={"a": {"min_lift": 0.4, "max_fan_out": 14, "max_names_per_sentence": 20}})
    lim = coherence.limits(cfg, "a")
    assert (lim["min_lift"], lim["max_fan_out"], lim["max_names_per_sentence"]) == (0.4, 14, 20)


def test_the_repository_wide_value_applies_when_the_intent_writes_none():
    cfg = cfg_with(min_lift=1.5, max_fan_out=7, floors={"a": {"min_lift": 0.4}})
    lim = coherence.limits(cfg, "b")
    assert (lim["min_lift"], lim["max_fan_out"], lim["max_names_per_sentence"]) == (1.5, 7, 8)
    other = coherence.limits(cfg, "a")   # only the key written differs; fan-out and names follow the repository
    assert (other["min_lift"], other["max_fan_out"], other["max_names_per_sentence"]) == (0.4, 7, 8)
    assert coherence.limits(cfg_with(), "x")["min_lift"] == coherence.DEFAULTS["min_lift"]


def test_an_intent_with_no_recorded_edges_reports_lift_as_not_applicable_and_passes(project, monkeypatch):
    path = project / "esoi" / "implementations.csv"
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    for row in rows:
        row["uses_solution_ids"] = ""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(coherence.Code, "evidence", lambda self, a, b: "E2")   # evidence on every pair: base rate above 0
    intent = coherence.check(project, pairs=True)["intents"][0]
    assert intent["uses_edges"] == 0
    assert intent["code_lift"] is None and intent["code_lift_note"] == "n/a (no recorded edges)"
    assert not any("lift" in line for line in intent["problems"].get("code", []))


def lift_zero_project(project, monkeypatch):
    """The scaffold records edges; evidence fires on pairs that are not edges and never on the recorded edges: precision 0, base rate above 0."""
    recorded = {("project-purpose", "greet-a-person"), ("project-purpose", "project-structure")}
    monkeypatch.setattr(coherence.Code, "evidence", lambda self, a, b: "" if (a, b) in recorded else "E2")
    return coherence.check(project, pairs=True)["intents"][0]


def test_an_intent_with_edges_and_lift_zero_still_fails(project, monkeypatch):
    intent = lift_zero_project(project, monkeypatch)
    assert intent["uses_edges"] > 0 and intent["code_lift"] == 0.0 and intent["code_lift_note"] == ""
    assert any("lift 0.0 below 1.0" in line for line in intent["problems"]["code"])


def test_a_per_intent_min_lift_lets_that_intent_pass_with_the_reason_written(project, monkeypatch):
    toml = project / "esoi.toml"
    toml.write_text(toml.read_text() + "\n[rules.S38]\nenabled = true\n[rules.S38.floors.demo]\nmin_lift = 0.0\nprecision = 0.0\n", encoding="utf-8")
    name = coherence.check(project, pairs=False)["intents"][0]["intent"]
    toml.write_text(toml.read_text().replace("floors.demo", f"floors.{name}"), encoding="utf-8")
    intent = lift_zero_project(project, monkeypatch)
    assert not any("lift" in line for line in intent["problems"].get("code", []))


# ---- E4: through a module the ownership map gives the user, to one it gives only the used --------------------------------------

def owned_code(tmp_path: Path, mid_owners: str = "user", leaf_owners: str = "used", mid_source: str = "from . import leaf\n"):
    """Package `pk`: the user's implementation file imports `mid`, which imports `leaf`; components.csv says who owns `mid` and `leaf`.
    The used solution's implementation file is `used.py`, which nothing imports."""
    pkg = tmp_path / "pk"
    pkg.mkdir(parents=True)
    for name, source in {"__init__": "", "user": "from . import mid\n", "mid": mid_source, "leaf": "value = 1\n", "used": "class Finder:\n    pass\n"}.items():
        (pkg / f"{name}.py").write_text(source, encoding="utf-8")
    cfg = SimpleNamespace(root=tmp_path, package="pk", package_dir="pk")
    solutions = {"user": {"solution_id": "user", "interface_name": "Runner"}, "used": {"solution_id": "used", "interface_name": "Finder"}}
    impls = [{"solution_id": "user", "implementation_id": "u1", "filepath": "pk/user.py"},
             {"solution_id": "used", "implementation_id": "c1", "filepath": "pk/used.py"}]
    components = [{"component_id": "m", "path": "pk/mid.py", "solutions": mid_owners},
                  {"component_id": "l", "path": "pk/leaf.py", "solutions": leaf_owners}]
    return coherence.Code(cfg, solutions, impls, {"user": impls[0], "used": impls[1]}, components)


def test_an_import_through_the_users_own_module_to_the_used_ones_is_strong_evidence_e4(tmp_path):
    code = owned_code(tmp_path)
    assert code.evidence("user", "used") == "E4"
    assert "E4" in coherence.STRONG


def test_a_module_owned_with_other_solutions_is_not_evidence_on_the_used_side(tmp_path):
    assert owned_code(tmp_path, leaf_owners="used;other").evidence("user", "used") != "E4"


def test_a_middle_module_the_user_does_not_own_is_not_evidence(tmp_path):
    assert owned_code(tmp_path, mid_owners="other").evidence("user", "used") != "E4"
    assert owned_code(tmp_path / "b", mid_owners="user;other").evidence("user", "used") == "E4"   # shared by the user is still the user's


def test_a_docstring_or_comment_naming_the_owned_module_is_not_evidence(tmp_path):
    code = owned_code(tmp_path, mid_source='"""Uses leaf and used."""\n# from . import leaf\nvalue = "leaf"\n')
    assert code.evidence("user", "used") == ""


def test_a_chain_the_ownership_map_does_not_give_the_user_is_not_evidence(tmp_path):
    code = owned_code(tmp_path)
    code.owned.clear()                                   # no record says whose any module is
    assert code.evidence("user", "used") != "E4"
