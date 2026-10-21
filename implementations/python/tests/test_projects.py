"""The local ESOI index: a folder named by ESOI_HOME, never the real home folder."""
from pathlib import Path

import pytest

from esoi import cli, projects, tables


@pytest.fixture
def home(tmp_path, monkeypatch):
    folder = tmp_path / "index"
    monkeypatch.setenv("ESOI_HOME", str(folder))
    return folder


def make_project(root: Path, name="Greeter", vision="Every person is greeted by name."):
    (root / "docs" / "structure").mkdir(parents=True)
    (root / "esoi.toml").write_text('structure_dir = "docs/structure"\n')
    tables.write_csv(root / "docs" / "structure" / "intent.csv", ["intent_id", "name", "vision_statement", "implements", "opportunities"],
                     [dict(intent_id="greeter", name=name, vision_statement=vision)])
    (root / "CLAUDE.md").write_text("Start here.\n")
    return root


def test_the_index_folder_comes_from_esoi_home_else_the_user_home(tmp_path):
    assert projects.resolve_home({"ESOI_HOME": str(tmp_path / "x")}, tmp_path) == tmp_path / "x"
    assert projects.resolve_home({}, tmp_path) == tmp_path / ".esoi"


def test_init_add_list_check_index_where_through_the_command_line(home, tmp_path, capsys):
    project = make_project(tmp_path / "greeter")
    assert cli.main(["projects", "init"]) == 0 and (home / "projects.csv").exists() and (home / "INDEX.md").exists()
    assert cli.main(["projects", "add", str(project), "--notes", "Records live under docs."]) == 0
    stored = projects.read_projects(home)[0]
    assert stored["name"] == "" and stored["vision_statement"] == ""   # the project's own intent.csv is the source
    row = projects.resolve([stored])[0]
    assert row["project_id"] == "greeter" and row["name"] == "Greeter" and row["vision_statement"].startswith("Every person")
    assert row["specifications"] == "esoi.toml" and row["start_here"] == "CLAUDE.md" and row["kind"] == "folder"
    capsys.readouterr()
    assert cli.main(["projects", "list"]) == 0 and "greeter" in capsys.readouterr().out
    assert cli.main(["projects", "check"]) == 0
    assert cli.main(["projects", "index"]) == 0 and "Greeter" in (home / "INDEX.md").read_text()
    capsys.readouterr()
    assert cli.main(["projects", "where", str(project / "docs")]) == 0
    out = capsys.readouterr().out
    assert "greeter: Greeter" in out and "start here:" in out and "CLAUDE.md" in out
    assert cli.main(["projects", "where", str(tmp_path)]) == 1


def test_a_duplicate_is_refused_unless_replaced(home, tmp_path):
    project = make_project(tmp_path / "greeter")
    projects.add(home, str(project))
    with pytest.raises(ValueError):
        projects.add(home, str(project))
    assert projects.add(home, str(project), notes="new", replace=True)["notes"] == "new" and len(projects.read_projects(home)) == 1


def test_a_url_is_listed_not_fetched(home):
    row = projects.add(home, "https://example.org/board/1", name="Roadmap", vision="The roadmap is shared.", kind="board")
    assert row["location"] == "https://example.org/board/1" and row["kind"] == "board"
    assert projects.check(home) == []


def test_check_finds_missing_places_and_unresolved_relations(home, tmp_path):
    project = make_project(tmp_path / "greeter")
    projects.add(home, str(project), relations="uses:ghost;friend:greeter")
    projects.add(home, str(tmp_path / "nowhere"), name="Gone", project_id="gone", vision="x", kind="folder")
    problems = projects.check(home)
    assert any("'ghost'" in line for line in problems) and any("not one of" in line and "friend" in line for line in problems)
    assert any(line.startswith("gone: location") for line in problems)
    rows = projects.read_projects(home)
    rows[0]["start_here"] = "MISSING.md"
    projects.write_projects(home, rows)
    assert any("start_here 'MISSING.md'" in line for line in projects.check(home))


def test_index_keeps_what_the_user_wrote_outside_the_markers(home, tmp_path):
    project = make_project(tmp_path / "greeter")
    projects.init(home)
    projects.add(home, str(project))
    (home / "INDEX.md").write_text("# Mine\n\nFor billing work read the billing playbook.\n\n" + projects.START + "\nold\n"
                                   + projects.END + "\n\nTail routing.\n")
    projects.index(home)
    text = (home / "INDEX.md").read_text()
    assert "billing playbook" in text and "Tail routing." in text and "old\n" not in text and "Greeter" in text
    projects.index(home)
    assert (home / "INDEX.md").read_text() == text   # idempotent
    (home / "INDEX.md").write_text("Only my words.\n")
    projects.index(home)
    kept = (home / "INDEX.md").read_text()
    assert kept.startswith("Only my words.") and projects.START in kept


def test_where_picks_the_deepest_project(home, tmp_path):
    outer = make_project(tmp_path / "outer")
    inner = make_project(outer / "packages" / "inner", name="Inner")
    projects.add(home, str(outer), project_id="outer")
    projects.add(home, str(inner), project_id="inner")
    assert projects.where(home, inner / "docs")["project_id"] == "inner"
    assert projects.where(home, outer / "docs")["project_id"] == "outer"


def test_adding_the_working_folder_names_the_project_after_it(home, tmp_path, monkeypatch):
    project = tmp_path / "work" / "ledger"
    project.mkdir(parents=True)
    monkeypatch.chdir(project)
    row = projects.add(home, ".")
    assert row["project_id"] == "ledger" and row["name"] == "ledger" and row["location"].endswith("ledger")
    assert projects.check(home) == []


def test_a_legacy_project_gets_no_name_or_vision_guessed_from_its_other_records(home, tmp_path):
    project = tmp_path / "old"
    (project / "docs" / "structure" / "overall").mkdir(parents=True)
    (project / "esoi.toml").write_text('structure_dir = "docs/structure"\noverall = "docs/structure/overall"\n')
    tables.write_csv(project / "docs" / "structure" / "overall" / "solutions.csv", ["solution_id", "name"],
                     [dict(solution_id="whole", name="Some overall solution")])
    tables.write_csv(project / "docs" / "structure" / "overall" / "ideals.csv", ["ideal_id", "principle"],
                     [dict(ideal_id="i", principle="An ideal that is not a vision")])
    assert projects.describe(project) == ("", "")
    row = projects.add(home, str(project), name="Old ledger")
    assert row["name"] == "Old ledger" and row["vision_statement"] == ""
    assert projects.resolve([row])[0]["vision_statement"] == ""


def test_structure_of_reads_the_configuration_in_pyproject(tmp_path):
    project = tmp_path / "lib"
    (project / "specs").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[tool.esoi]\nstructure_dir = "specs"\n')
    tables.write_csv(project / "specs" / "intent.csv", ["intent_id", "name", "vision_statement", "implements", "opportunities"],
                     [dict(intent_id="lib", name="Library", vision_statement="The library is used.")])
    assert projects.structure_of(project) == ("pyproject.toml", project / "specs")
    assert projects.describe(project) == ("Library", "The library is used.")
    inner = project / "docs"   # a parent's configuration is not the project's
    inner.mkdir()
    assert projects.structure_of(inner) == ("", None)


def test_a_location_under_the_home_folder_is_kept_with_a_tilde_and_round_trips(home, tmp_path, monkeypatch):
    user = tmp_path / "user"
    monkeypatch.setenv("HOME", str(user))
    project = make_project(user / "work" / "greeter")
    row = projects.add(home, str(project))
    assert row["location"] == "~/work/greeter"
    assert projects.read_projects(home)[0]["location"] == "~/work/greeter"
    assert projects.check(home) == []
    assert projects.where(home, project / "docs")["project_id"] == "greeter"
    assert projects.local_path("~/work/greeter") == project


def test_name_and_vision_come_from_the_intent_and_a_disagreeing_row_is_reported(home, tmp_path):
    project = make_project(tmp_path / "greeter")
    projects.add(home, str(project))
    assert projects.check(home) == []
    rows = projects.read_projects(home)
    rows[0].update(name="Old name", vision_statement="An old vision.")
    projects.write_projects(home, rows)
    bad = projects.check(home)
    assert any("name 'Old name' disagrees with the top intent.csv" in line for line in bad)
    assert any("vision_statement" in line and "disagrees" in line for line in bad)
    assert projects.resolve(projects.read_projects(home))[0]["name"] == "Greeter"   # the intent wins in every output
    projects.index(home)
    text = (home / "INDEX.md").read_text()
    assert "Greeter" in text and "Old name" not in text


def test_a_project_without_a_top_intent_keeps_its_own_name_and_a_nameless_one_is_reported(home, tmp_path):
    projects.add(home, "https://example.org/board/1", name="Roadmap", vision="The roadmap is shared.", kind="board")
    assert projects.resolve(projects.read_projects(home))[0]["name"] == "Roadmap"
    rows = projects.read_projects(home)
    rows[0]["name"] = ""
    projects.write_projects(home, rows)
    assert any("name is empty" in line for line in projects.check(home))


def test_used_by_follows_from_the_uses_of_other_rows(home, tmp_path):
    library = make_project(tmp_path / "library", name="Library")
    app = make_project(tmp_path / "app", name="App")
    projects.add(home, str(library), project_id="library")
    projects.add(home, str(app), project_id="app", relations="uses:library")
    assert projects.check(home) == []
    projects.index(home)
    text = (home / "INDEX.md").read_text()
    assert "- `app` uses `library`" in text and "- `library` used-by `app`" in text
    assert "used-by:app" in projects.where(home, library)["relations"]
    rows = projects.read_projects(home)
    rows[0]["relations"] = "used-by:app"   # also written by hand: still one line
    projects.write_projects(home, rows)
    projects.index(home)
    assert (home / "INDEX.md").read_text().count("`library` used-by `app`") == 1


def test_a_project_on_a_previous_default_folder_is_found_and_both_folders_are_not_guessed(tmp_path):
    for name, previous in (("a", "docs/structure"), ("b", "structure")):
        folder = tmp_path / name / previous
        folder.mkdir(parents=True)
        (folder / "intent.csv").write_text("intent_id,name,vision_statement,implements,opportunities\nx,X,Y,,\n")
        assert projects.structure_of(tmp_path / name) == (previous + "/", tmp_path / name / previous)
        assert projects.describe(tmp_path / name) == ("X", "Y")
    (tmp_path / "b" / "esoi").mkdir()
    (tmp_path / "b" / "esoi" / "intent.csv").write_text("intent_id,name,vision_statement,implements,opportunities\n")
    assert projects.structure_of(tmp_path / "b") == ("", None)
