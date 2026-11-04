from pathlib import Path

from esoi import standards_measure as sm

STANDARD = """# Thin routes

**Tags:** route-logic
**Paths:** app/api/**/*.py
**Rule:** Keep route files to handlers only.
**Check:** regex:def helper => Move the helper into a service.
"""
TAGS = "tag,mitigates,meaning,keywords\nroute-logic,prob-x,Risk of logic in routes because it cannot be reused.,route;endpoint\n"


def world(tmp_path: Path) -> Path:
    folder = tmp_path / "docs" / "standards"
    folder.mkdir(parents=True)
    (folder / "thin.md").write_text(STANDARD)
    (folder / "tags.csv").write_text(TAGS)
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_violation_label_and_task_match(tmp_path):
    root = world(tmp_path)
    cases = [{"id": "a", "task": "add a route for search", "commit": "c1", "files": ["app/api/search.py"]},
             {"id": "b", "task": "tidy the readme", "commit": "c2", "files": ["README.md"]}]
    diffs = {"c1": "+++ b/app/api/search.py\n@@ -0,0 +1 @@\n+def helper(x):\n", "c2": ""}
    result = sm.measure(root, cases, lambda commit, path: "", sm.ranked_by_task, lambda commit: diffs[commit])
    assert [r.applied for r in result.results] == [["thin"], []]
    assert result.recall == 1.0 and result.precision == 1.0 and result.quiet == 1.0


def test_baseline_is_not_quiet(tmp_path):
    root = world(tmp_path)
    cases = [{"id": "b", "task": "tidy the readme", "commit": "c2", "files": ["README.md"]}]
    result = sm.measure(root, cases, lambda commit, path: "", sm.everything, lambda commit: "")
    assert result.quiet == 0.0
