"""Navigating standards by risk tag and checking a commit's added lines against them."""
import subprocess

from esoi import standards_nav as nav

STANDARD = """# Thin routes

**Tags:** logic-in-entry-layer, low-quality-code
**Paths:** app/routes/**/*.py
**Rule:** A route delegates; helpers live in services.
**Check:** undecorated-def => Move this helper out of the route module.
**Check:** regex:\\bexpensive\\( => Costly call on every request.
**Check:** needs-test:tests/** => Ship a test with a route change.
"""

ROUTE = """router = object()


def helper():
    return 1


@router.get("/x")
def handler():
    expensive("q")
    expensive("q")  # standards-waive: thin one query text only
"""


def repo(tmp_path):
    (tmp_path / "docs/standards").mkdir(parents=True)
    (tmp_path / "docs/standards/thin.md").write_text(STANDARD)
    (tmp_path / "docs/standards/untagged.md").write_text("# Old standard\n\nNo header lines.\n")
    (tmp_path / "app/routes").mkdir(parents=True)
    (tmp_path / "app/routes/x.py").write_text(ROUTE)
    for cmd in (["init", "-q"], ["config", "user.email", "a@b.c"], ["config", "user.name", "t"], ["add", "-A"]):
        subprocess.run(["git", "-C", str(tmp_path), *cmd], check=True)
    return tmp_path


def test_only_tagged_standards_whose_paths_match_are_shown(tmp_path):
    root = repo(tmp_path)
    shown = nav.for_file(root / "app/routes/x.py")
    assert "A route delegates" in shown and "Old standard" not in shown
    assert nav.for_file(root / "README.md") == ""


def test_a_commit_is_checked_on_added_lines_and_waivers_need_a_reason(tmp_path):
    root = repo(tmp_path)
    found = {(f.standard, f.line) for f in nav.check_staged(root)}
    assert ("thin", 4) in found            # the undecorated helper
    assert ("thin", 10) in found           # the unwaived costly call
    assert ("thin", 11) not in found       # waived with a reason
    assert any(f.line == 0 for f in nav.check_staged(root))   # no test staged


def test_existing_code_is_not_flagged(tmp_path):
    root = repo(tmp_path)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=a@b.c", "-c", "user.name=t", "commit", "-qm", "base"], check=True)
    (root / "README.md").write_text("changed\n")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
    assert nav.check_staged(root) == []


def test_rules_without_a_check_are_listed_for_the_staged_files(tmp_path):
    root = repo(tmp_path)
    (root / "docs/standards/manual.md").write_text(
        "# Manual\n\n**Tags:** low-quality-code\n**Paths:** app/routes/**/*.py\n**Rule:** Log a warning when you fall back.\n")
    text = nav.advisory(root)
    assert "Log a warning when you fall back" in text and "A route delegates" not in text


def test_the_hook_is_written_where_git_looks_and_never_overwrites_another(tmp_path):
    root = repo(tmp_path)
    path = nav.install_hook(root)
    assert path.name == "pre-commit" and "check-staged" in path.read_text()
    assert nav.install_hook(root) == path
    path.write_text("#!/bin/sh\necho other\n")
    try:
        nav.install_hook(root)
    except FileExistsError:
        return
    raise AssertionError("another hook was overwritten")


def test_a_described_task_finds_standards_by_tag_keywords_and_a_vague_task_finds_none(tmp_path):
    root = repo(tmp_path)
    (root / "docs/standards/tags.csv").write_text(
        "tag,mitigates,meaning,keywords\nlogic-in-entry-layer,p1,Risk of logic in a route because it was written there,route;handler;ranking\n"
        "low-quality-code,p1,Risk of a change that breaks structure because a rule was missed,quality\n")
    assert "A route delegates" in nav.for_task(root, "add a route that does ranking of results")
    assert nav.for_task(root, "fix the typo in an email") == ""


def test_lint_enforces_the_standard_for_writing_standards(tmp_path):
    root = repo(tmp_path)
    assert any("not a row of tags.csv" in p for p in nav.lint(root))
    (root / "docs/standards/tags.csv").write_text(
        "tag,mitigates,meaning,keywords\nlogic-in-entry-layer,p1,A thing,route\nlow-quality-code,p1,Risk of x because y,quality\n")
    assert any("starts 'Risk of" in p for p in nav.lint(root))
