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
    tables.write_csv(root / "docs" / "structure" / "intent.csv", ["intent_id", "name", "vision_statement", "implements", "opportunity"],
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
    row = projects.read_projects(home)[0]
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
