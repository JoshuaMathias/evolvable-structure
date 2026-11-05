"""An adopted solution is a solution the adopter attaches its own arms, metrics, ports and components to: its id resolves wherever a solution id
resolves, while the words the library holds (description, purpose, problems, ideals, role) are not asked of the adopter."""
from conftest import fill_top_intent  # noqa: F401  (the repo fixture fills the top intent)
from esoi.runtime.implementation_selection import select
from esoi.structure.intent_registry import registry, tables
from esoi.structure.structure_check import check
from test_adoption import adopt

OWN = {"S7", "S11", "S21", "S26", "S29"}


def add_row(repo, name, row):
    path = repo / "esoi" / name
    cols, rows = tables.read_header(path), tables.read_csv(path)
    rows.append({**{col: "" for col in cols}, **row})
    tables.write_csv(path, cols, rows)


def attach_own_parts(repo):
    """The adopter's own arm, metric, port and component under the adopted ``greet-people``, and an arm elsewhere that builds on it."""
    cfg = adopt(repo)
    path = repo / "esoi" / "solutions.csv"
    cols, rows = tables.read_header(path), tables.read_csv(path)
    for row in rows:
        if row["solution_id"] == "greet-people":
            row.update(metric_ids="greeting-polite", implementations="demo/arm.py::Warm", selected="warm", interface_name="GreetingPort")
    tables.write_csv(path, cols, rows)
    add_row(repo, "metrics.csv", {"metric_id": "greeting-polite", "name": "Greeting polite", "solution_ids": "greet-people",
                                  "purpose": "Ensure each greeting is polite.", "record": "Reviewed by hand; no run measures it yet."})
    add_row(repo, "implementations.csv", {"implementation_id": "greet-people:warm", "solution_id": "greet-people", "filepath": "demo/arm.py::Warm", "name": "Warm",
                                          "description": "Greets with a warm opening.", "advantages": "Friendly.", "disadvantages": "Longer."})
    add_row(repo, "components.csv", {"component_id": "greeter", "layer": "core", "path": "demo/arm.py", "role": "Greets warmly.", "solutions": "greet-people"})
    (repo / "demo" / "arm.py").write_text('from esoi import implementation\n\n\nclass GreetingPort:\n    pass\n\n\n@implementation("greet-a-person", "warm")\nclass Warm(GreetingPort):\n    pass\n')
    return cfg


def test_an_adopted_solution_is_in_the_solutions_and_still_listed_as_adopted(repo):
    loaded = registry.load(attach_own_parts(repo))
    assert "greet-people" in [r["solution_id"] for r in loaded.every_solution()]
    assert [r["solution_id"] for r in loaded.adopted] == ["greet-people"]
    assert "greet-people" not in [r["solution_id"] for r in loaded.authored()]


def test_an_adopted_solutions_own_arm_metric_port_and_component_raise_no_dangling_id(repo):
    cfg = attach_own_parts(repo)
    problems = check.check_all(cfg)[0]
    assert [p for p in problems if p.split(" ", 1)[0] in OWN] == []


def test_an_arm_elsewhere_that_builds_on_an_adopted_solution_resolves(repo):
    cfg = attach_own_parts(repo)
    path = repo / "esoi" / "implementations.csv"
    cols, rows = tables.read_header(path), tables.read_csv(path)
    for row in rows:
        if row["solution_id"] == "project-purpose":
            row["uses_solution_ids"] = "greet-people"
    tables.write_csv(path, cols if "uses_solution_ids" in cols else cols + ["uses_solution_ids"], rows)
    assert [p for p in check.check_all(cfg)[0] if p.startswith("S29")] == []


def test_a_name_that_is_no_solution_in_a_component_is_still_dangling(repo):
    cfg = attach_own_parts(repo)
    path = repo / "esoi" / "components.csv"
    cols, rows = tables.read_header(path), tables.read_csv(path)
    for row in rows:
        if row["component_id"] == "greeter":
            row["solutions"] = "greet-people;nobody"
    tables.write_csv(path, cols, rows)
    assert any(p.startswith("S11 greeter") and "nobody" in p for p in check.check_all(cfg)[0])


def test_the_adopters_selection_reads_the_adopted_solutions_chosen_arm(repo):
    loaded = registry.load(attach_own_parts(repo))
    row = next(r for r in loaded.every_solution() if r["solution_id"] == "greet-people")
    assert select.default_name(row, loaded.implementations) == "warm"
