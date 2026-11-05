"""Rule S39: the trend of waivers, enabled rules and floors against a base commit. A report, never a failure."""
import subprocess
from pathlib import Path

import pytest

from esoi.structure.structure_check import check
from esoi.structure.intent_registry import config, tables
from test_entry_rules import RULES, enable, link_up, rewrite

BASELINE = "\n[rules.S38.floors.demo]\nprecision = 0.5\ncoverage = 0.5\n"


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def history(repo, monkeypatch):
    """A git repository whose first commit enables every opt-in rule with floors; returns (root, base commit)."""
    monkeypatch.delenv("ESOI_RATCHET_BASE", raising=False)
    link_up(repo)
    enable(repo, *RULES, extra=BASELINE)
    git(repo, "init", "-q")
    (repo / ".gitignore").write_text((repo / ".gitignore").read_text() + ".pytest_cache/\n")
    base = commit(repo, "baseline")
    monkeypatch.setenv("ESOI_RATCHET_BASE", base)
    return repo, base


def trend(root):
    return [line for line in check.check_all(config.load(root))[1] if line.startswith("S39")]


def add_waiver(root, rule="S37", key="greet-a-person"):
    path = root / "esoi" / "waivers.csv"
    rows = tables.read_csv(path)
    tables.write_csv(path, ["rule", "path", "reason"], rows + [dict(rule=rule, path=key, reason="a stated reason")])


def set_floor(root, precision, coverage=0.5):
    toml = root / "esoi.toml"
    import re
    toml.write_text(re.sub(r"coverage = [\d.]+", f"coverage = {coverage}", re.sub(r"precision = [\d.]+", f"precision = {precision}", toml.read_text())))


def test_an_unchanged_tree_reports_no_move(history):
    root, base = history
    assert trend(root) == []


def test_a_new_waiver_is_reported_as_grown_and_never_fails_the_check(history):
    root, base = history
    add_waiver(root)
    lines = trend(root)
    assert any("waivers of S37 (new: greet-a-person): 0 -> 1 (grew)" in line and "next:" in line for line in lines)
    problems, advisory = check.check_all(config.load(root))
    assert not any(line.startswith("S39") for line in problems)
    assert check.run_cli(config.load(root), False, False, say=lambda text: None) in (0, 1)


def test_a_removed_waiver_is_reported_as_shrunk(history):
    root, base = history
    add_waiver(root)
    base = commit(root, "a waiver")
    monkey = pytest.MonkeyPatch()
    monkey.setenv("ESOI_RATCHET_BASE", base)
    try:
        (root / "esoi" / "waivers.csv").write_text("rule,path,reason\n")
        assert any("waivers of S37: 1 -> 0 (shrank)" in line for line in trend(root))
    finally:
        monkey.undo()


def test_a_lowered_floor_is_reported_as_fell_and_a_raised_one_as_rose(history):
    root, base = history
    set_floor(root, 0.4)
    assert any("floor precision of demo: 0.5 -> 0.4 (fell)" in line and "next:" in line for line in trend(root))
    set_floor(root, 0.6)
    assert any("floor precision of demo: 0.5 -> 0.6 (rose)" in line and "next:" not in line for line in trend(root))


def test_a_raised_ceiling_is_reported(history):
    root, base = history
    toml = root / "esoi.toml"
    toml.write_text(toml.read_text() + "\n[rules.S38]\nmax_fan_out = 12\n") if "[rules.S38]\n" not in toml.read_text() else \
        toml.write_text(toml.read_text().replace("[rules.S38]\nenabled = true\n", "[rules.S38]\nenabled = true\nmax_fan_out = 12\n"))
    assert any("ceiling max_fan_out: 9 -> 12 (rose)" in line for line in trend(root))


def test_a_per_intent_limit_that_loosens_is_reported(history):
    root, base = history
    toml = root / "esoi.toml"
    toml.write_text(toml.read_text().replace("precision = 0.5\n", "precision = 0.5\nmin_lift = 0.2\nmax_fan_out = 14\n"))
    lines = trend(root)
    assert any("floor min_lift of demo: 1.0 -> 0.2 (fell)" in line and "next:" in line for line in lines)
    assert any("ceiling max_fan_out of demo: 9 -> 14 (rose)" in line and "next:" in line for line in lines)


def test_a_rule_enabled_at_the_base_and_off_now_is_reported(history):
    root, base = history
    toml = root / "esoi.toml"
    toml.write_text(toml.read_text().replace("[rules.S38]\nenabled = true\n", "[rules.S38]\nenabled = false\n"))
    assert any("rule S38 enabled: yes -> no (disabled)" in line for line in trend(root))
    toml.write_text(toml.read_text().replace("[rules.S38]\nenabled = false\n", "[rules.S38]\nenabled = true\n") .replace("package =", 'disable = ["S38"]\npackage =', 1))
    assert any("rule S38 enabled: yes -> no (disabled)" in line for line in trend(root))


def test_the_commit_that_first_enables_a_rule_sets_its_baseline_even_with_waivers(repo, monkeypatch):
    monkeypatch.delenv("ESOI_RATCHET_BASE", raising=False)
    link_up(repo)
    git(repo, "init", "-q")
    base = commit(repo, "nothing enabled")
    monkeypatch.setenv("ESOI_RATCHET_BASE", base)
    enable(repo, *RULES)
    add_waiver(repo, "S37", "greet-a-person")
    add_waiver(repo, "S38", "demo")
    assert not any("waivers of" in line for line in trend(repo))


def test_the_base_is_the_first_parent_when_nothing_else_names_one(history, monkeypatch):
    root, base = history
    monkeypatch.delenv("ESOI_RATCHET_BASE")
    add_waiver(root)
    commit(root, "a waiver")
    assert any("(grew)" in line for line in trend(root))           # HEAD~1 is the baseline commit


def test_the_base_is_the_merge_base_with_the_default_branch_when_that_is_not_head(history, monkeypatch):
    root, base = history
    monkeypatch.delenv("ESOI_RATCHET_BASE")
    default = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    git(root, "checkout", "-q", "-b", "work")
    add_waiver(root)
    commit(root, "waiver one")
    set_floor(root, 0.45)
    commit(root, "floor lowered")
    from esoi.structure.structure_budget import ratchet
    found, note = ratchet.resolve_base(root)
    assert found == base and note == ""
    lines = trend(root)
    assert any("(grew)" in line for line in lines) and any("(fell)" in line for line in lines)
    assert default in git(root, "branch")


def test_the_configured_base_is_used_before_the_default(history, monkeypatch):
    root, base = history
    monkeypatch.delenv("ESOI_RATCHET_BASE")
    add_waiver(root)
    second = commit(root, "a waiver")
    toml = root / "esoi.toml"
    toml.write_text(toml.read_text().replace("[rules.S39]\nenabled = true\n", f"[rules.S39]\nenabled = true\nbase = \"{second}\"\n"))
    assert not any("waivers of" in line for line in trend(root))   # against the commit that already holds the waiver


def test_a_root_commit_has_no_base_and_reports_nothing(history, monkeypatch):
    root, base = history
    monkeypatch.delenv("ESOI_RATCHET_BASE")
    assert trend(root) == []


def test_not_a_git_repository_is_a_no_base_note_not_a_failure(repo, monkeypatch):
    monkeypatch.delenv("ESOI_RATCHET_BASE", raising=False)
    link_up(repo)
    enable(repo, *RULES)
    problems, advisory = check.check_all(config.load(repo))
    assert problems == [] and any(line.startswith("S39 no base: trend not computed") and "git" in line for line in advisory)


def test_a_shallow_clone_that_misses_the_base_names_the_history_needed(history, tmp_path, monkeypatch):
    root, base = history
    monkeypatch.delenv("ESOI_RATCHET_BASE")
    add_waiver(root)
    commit(root, "a waiver")
    clone = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}", str(clone)], check=True, capture_output=True)
    lines = trend(clone)
    assert len(lines) == 1 and "no base: trend not computed" in lines[0] and "fetch-depth" in lines[0]


def test_a_named_base_missing_from_the_clone_says_so(history, monkeypatch):
    root, base = history
    monkeypatch.setenv("ESOI_RATCHET_BASE", "0" * 40)
    lines = trend(root)
    assert len(lines) == 1 and "no base" in lines[0] and "fetch-depth" in lines[0]
