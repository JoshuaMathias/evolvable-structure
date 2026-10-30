"""The version stamp, the template version a repository records, rule S34 and `esoi version`."""
import datetime
import json
import os
import tomllib
from pathlib import Path

import pytest

from esoi import __version__, check, cli, config, skill, templates, versioning
from esoi.config import Config
from test_skill import TABLE
from test_templates import SKILL, make

TODAY = datetime.date(2026, 10, 30)
HEADER = "entity,field_key,question,group,required\n"
OLD = HEADER + "solution,purpose,Why?,specify,yes\nsolution,tags,Which?,specify,yes\nsolution,gone,Old?,specify,yes\n"
NEW = (HEADER + "solution,purpose,Why exactly?,specify,yes\nsolution,tags,Which?,specify,no\nsolution,approach,How?,specify,yes\n"
       "metric,disadvantages,What is missed?,specify,no\n")
UNCOMMITTED = {"commit": "", "commit_date": "", "committed": False}


def run(repo, *argv):
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        return cli.main(list(argv))
    finally:
        os.chdir(cwd)


def test_field_changes_name_added_removed_optional_required_and_reworded_fields():
    assert versioning.field_changes(OLD, NEW) == [
        "solution.purpose: question reworded", "solution.tags: made optional", "solution.approach: added (required)",
        "metric.disadvantages: added (optional)", "solution.gone: removed"]
    assert versioning.field_changes(NEW, NEW) == []
    assert "solution.tags: made required" in versioning.field_changes(NEW, OLD)


def test_the_first_template_stamp_is_version_one_and_the_same_template_changes_nothing():
    first = versioning.template_stamp({}, "", OLD, UNCOMMITTED, "skill text", TODAY)
    assert first["template"]["version"] == 1 and first["template"]["changes"] == [versioning.BASELINE]
    assert first["template"]["sha256"] == versioning.digest(OLD)[:12] and first["history"] == []
    later = datetime.date(2026, 11, 2)
    assert versioning.template_stamp(first, OLD, OLD, UNCOMMITTED, "skill text", later) == first   # an uncommitted source keeps its first date


def test_a_changed_template_is_the_next_version_with_its_changes_and_the_old_one_kept_in_history():
    first = versioning.template_stamp({}, "", OLD, UNCOMMITTED, "a", TODAY)
    committed = {"commit": "abc1234def", "commit_date": "2026-10-31", "committed": True}
    second = versioning.template_stamp(first, OLD, NEW, committed, "b", TODAY)
    assert second["template"]["version"] == 2 and second["template"]["date"] == "2026-10-31"
    assert second["template"]["skill_commit"] == "abc1234def" and second["template"]["changes"][1] == "solution.tags: made optional"
    assert second["history"] == [first["template"]]
    assert [e["version"] for e in versioning.since(second, 1)] == [2] and [e["version"] for e in versioning.since(second, 0)] == [1, 2]
    assert versioning.since(second, 2) == []
    assert versioning.describe(second["template"]).startswith("template 2 (2026-10-31, skill abc1234): solution.purpose")


def test_committing_the_source_after_a_stamp_refreshes_the_identity_without_a_new_version():
    first = versioning.template_stamp({}, "", OLD, UNCOMMITTED, "a", TODAY)
    committed = {"commit": "abc1234def", "commit_date": "2026-11-01", "committed": True}
    again = versioning.template_stamp(first, OLD, OLD, committed, "a", TODAY)
    assert again["template"]["version"] == 1 and again["template"]["skill_commit"] == "abc1234def"
    assert again["template"]["skill_committed"] is True and again["template"]["date"] == "2026-11-01"


def test_the_skill_section_hashes_the_source_and_the_copy_and_is_reproducible():
    shipped = {"SKILL.md": "x", "steps.md": "y"}
    one = versioning.skill_section({}, UNCOMMITTED, "source", shipped, TODAY)
    assert one["skill_md_sha256"] == versioning.digest("source") and one["date"] == "2026-10-30"
    assert versioning.skill_section({"skill": one}, UNCOMMITTED, "source", shipped, datetime.date(2027, 1, 1)) == one
    assert versioning.skill_section({"skill": one}, UNCOMMITTED, "source", {**shipped, "steps.md": "z"}, TODAY)["copy_sha256"] != one["copy_sha256"]


def test_the_source_identity_outside_git_is_uncommitted(tmp_path):
    (tmp_path / "SKILL.md").write_text("x")
    assert versioning.source_identity(tmp_path, ["SKILL.md"]) == UNCOMMITTED


def test_template_sync_writes_the_stamp_and_a_second_sync_changes_nothing(tmp_path):
    cfg = make(tmp_path)
    cfg.version_stamp = "stamp.json"
    assert templates.sync(cfg, say=lambda text: None) == 0
    first = (tmp_path / "stamp.json").read_text()
    stamp = json.loads(first)
    assert stamp["template"]["version"] == 1 and stamp["format"] == 1 and "skill" not in stamp
    assert str(tmp_path) not in first
    assert templates.sync(cfg, say=lambda text: None) == 0 and (tmp_path / "stamp.json").read_text() == first
    assert templates.sync(cfg, check=True, say=lambda text: None) == 0
    (tmp_path / "SKILL.md").write_text(SKILL.replace("What is the problem?", "What exactly is the problem?"))
    lines = []
    assert templates.sync(cfg, check=True, say=lines.append) == 1 and "stamp.json" in lines[-1]
    assert templates.sync(cfg, say=lambda text: None) == 0
    changed = json.loads((tmp_path / "stamp.json").read_text())
    assert changed["template"]["version"] == 2 and changed["template"]["changes"] == [
        "problem.exactly_problem: added (required)", "problem.problem: removed"]   # a field key comes from its question
    assert changed["history"][0]["version"] == 1


def test_skill_sync_writes_the_skill_part_of_the_stamp_and_check_finds_it_stale(tmp_path):
    root, src = tmp_path / "repo", tmp_path / "src"
    (src / "notes").mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: demo\ndescription: d\n---\n\n# demo\n")
    (src / "notes" / "a.md").write_text("# a\n")
    root.mkdir()
    cfg = Config(root=root, skill={"dir": "copy", "include": ["SKILL.md", "notes/*.md"]}, version_stamp="stamp.json")
    assert skill.sync(cfg, str(src), say=lambda text: None) == 0
    first = (root / "stamp.json").read_text()
    stamp = json.loads(first)
    assert set(stamp["skill"]) == {"commit", "committed", "date", "skill_md_sha256", "copy_sha256"} and str(tmp_path) not in first
    assert skill.sync(cfg, str(src), say=lambda text: None) == 0 and (root / "stamp.json").read_text() == first
    assert skill.sync(cfg, str(src), check=True, say=lambda text: None) == 0
    (root / "stamp.json").unlink()
    lines = []
    assert skill.sync(cfg, str(src), check=True, say=lines.append) == 1 and "version stamp" in lines[0]
    assert skill.check(cfg, str(src), say=lines.append) == 1


def test_the_shipped_stamp_matches_the_shipped_template_and_the_package_version():
    stamp = versioning.bundled_stamp()
    from esoi.records import TEMPLATE_DATA
    assert stamp["template"]["sha256"] == versioning.digest(TEMPLATE_DATA.read_text(encoding="utf-8"))[:12]
    assert versioning.template_version(stamp) == stamp["template"]["version"] >= 1
    pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == __version__


@pytest.mark.parametrize("before, after", [
    ("package = \"x\"\n", "package = \"x\"\n\n[records]\ntemplate_version = 3\n"),
    ("package = \"x\"\n\n[records]\n# why\nfoo = 1\n", "package = \"x\"\n\n[records]\ntemplate_version = 3\n# why\nfoo = 1\n"),
    ("[records]\ntemplate_version = 1\nfoo = 1\n[skill]\ndir = \"d\"\n", "[records]\ntemplate_version = 3\nfoo = 1\n[skill]\ndir = \"d\"\n"),
    ("[records.approved_fields]\nsolutions = [\"a\"]\n", "[records.approved_fields]\nsolutions = [\"a\"]\n\n[records]\ntemplate_version = 3\n"),
    ("records.template_version = 1\npackage = \"x\"\n[records.approved_fields]\nsolutions = [\"a\"]\n",
     "records.template_version = 3\npackage = \"x\"\n[records.approved_fields]\nsolutions = [\"a\"]\n"),
    ("package = \"x\"", "package = \"x\"\n\n[records]\ntemplate_version = 3\n"),
])
def test_recording_edits_only_the_records_table(before, after):
    assert versioning.with_recorded_version(before, 3) == after


def test_recording_refuses_an_edit_it_cannot_make_safely():
    with pytest.raises(versioning.VersionError, match="by hand"):
        versioning.with_recorded_version("records = { foo = 1 }\n", 3)


def newer(monkeypatch, versions):
    """Make the library carry template versions 1..versions, version 2 changing a solution field."""
    history = [{"version": v, "sha256": f"h{v}", "date": f"2026-11-0{v}", "skill_commit": f"c{v}abcdef", "changes": [f"solution.f{v}: added (required)"]}
               for v in range(1, versions + 1)]
    stamp = {"template": history[-1], "history": history[:-1]}
    monkeypatch.setattr(versioning, "bundled_stamp", lambda: stamp)


def forget(repo):
    """The scaffold records the template version; take it away to be a repository that has not recorded one."""
    toml = repo / "esoi.toml"
    toml.write_text("".join(line for line in toml.read_text().splitlines(keepends=True) if "template_version" not in line))


def test_a_repository_with_no_recorded_version_passes_with_one_note(repo, monkeypatch):
    newer(monkeypatch, 3)
    forget(repo)
    cfg = config.load(repo)
    assert check.check(cfg) == []
    assert versioning.note(cfg)[0].startswith("note: no template version recorded") and "version 3" in versioning.note(cfg)[0]


def test_s34_names_what_changed_since_the_recorded_version(repo, monkeypatch):
    newer(monkeypatch, 3)
    cfg = config.load(repo)
    cfg.records["template_version"] = 1
    lines = [line for line in check.check(cfg) if line.startswith("S34")]
    assert len(lines) == 3 and "template 2 (2026-11-02, skill c2abcde): solution.f2: added (required)" in lines[0]
    assert "template 3" in lines[1] and "esoi version --record" in lines[2] and "version 3" in lines[2]
    cfg.records["template_version"] = 2
    assert len([line for line in check.check(cfg) if line.startswith("S34")]) == 2
    cfg.records["template_version"] = 3
    assert check.check(cfg) == [] and versioning.note(cfg) == []


def test_s34_says_when_the_records_are_ahead_or_the_value_is_not_a_version(repo, monkeypatch):
    newer(monkeypatch, 2)
    cfg = config.load(repo)
    cfg.records["template_version"] = 5
    assert "upgrade esoi" in check.check(cfg)[0]
    cfg.records["template_version"] = "latest"
    assert "whole number" in check.check(cfg)[0]


def test_s34_offers_the_field_migration_when_old_columns_are_present(repo, monkeypatch):
    newer(monkeypatch, 2)
    path = repo / "esoi" / "solutions.csv"
    from esoi import tables
    rows, cols = tables.read_csv(path), tables.read_header(path)
    tables.write_csv(path, cols + ["scoped_purpose"], [{**r, "scoped_purpose": "Greet people."} for r in rows])
    cfg = config.load(repo)
    cfg.records["template_version"] = 1
    assert "run `esoi fields migrate --apply`, then run `esoi version --record`" in [l for l in check.check(cfg) if l.startswith("S34")][-1]


def test_the_scaffold_records_the_current_template_version(tmp_path):
    from esoi import scaffold
    scaffold.init(tmp_path, "versioned_demo", say=lambda text: None)
    cfg = config.load(tmp_path)
    assert versioning.recorded_version(cfg) == (versioning.template_version(versioning.bundled_stamp()), "")


def test_the_version_command_prints_the_package_skill_and_template_and_records(repo, capsys, monkeypatch):
    newer(monkeypatch, 2)
    forget(repo)
    assert run(repo, "version") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"esoi {__version__}" and out[1].startswith("skill: ") or out[1].startswith("skill: no stamp")
    assert "template: version 2" in out[2] and out[-1] == "records: no template version recorded (run `esoi version --record`)"
    assert run(repo, "version", "--record") == 0 and "template_version = 2" in capsys.readouterr().out
    assert run(repo, "version") == 0 and capsys.readouterr().out.splitlines()[-1] == "records: template version 2"
    assert run(repo, "check") == 0


def test_the_version_command_works_without_a_configuration(tmp_path, capsys):
    assert run(tmp_path, "version") == 0 and capsys.readouterr().out.startswith(f"esoi {__version__}")
    assert run(tmp_path, "version", "--record") == 2
