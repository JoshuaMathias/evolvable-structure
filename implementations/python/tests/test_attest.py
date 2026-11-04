"""``esoi attest``: a recorded, reasoned attestation that the arm's own code changed but not what its result measures."""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

from esoi import attest, config as config_module, harness, leaderboard  # noqa: E402
import staleness_fixture  # noqa: E402


def project(tmp_path, step="touch-the-measured-file", component="alpha"):
    """A copy of the fixture repository at ``step`` (alpha's own file changed in a later commit) whose results log holds alpha's row."""
    built = staleness_fixture.build(step)
    root = tmp_path / "repo"
    shutil.copytree(built.root, root)
    cfg = config_module.load(root / "esoi.toml")
    cfg.staleness_rule = "import_closure"
    row = dict(built.rows[component], component=f"{component}_eval", impl="live", passed="1", cases="1", heldout="", dev="")
    cfg.results_path.parent.mkdir(parents=True, exist_ok=True)
    with cfg.results_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return cfg, row, f"{component}_eval"


def why(cfg, component, row):
    return harness.stale_reason(cfg, component, row)


def commit(cfg, message="more"):
    subprocess.run(["git", "add", "-A", "--", "pkg"], cwd=cfg.root, check=True)
    subprocess.run(["git", "-c", "user.email=a@b.c", "-c", "user.name=A", "commit", "-q", "-m", message], cwd=cfg.root, check=True)


def test_an_attestation_makes_the_result_current_for_its_range_and_says_why(tmp_path):
    cfg, row, comp = project(tmp_path)
    assert "pkg/alpha.py" in why(cfg, comp, row)
    said = []
    entry = attest.attest(cfg, comp, "live", "renamed a local variable", author="Ada <a@b.c>", say=said.append)
    assert entry["author"] == "Ada <a@b.c>" and entry["from_sha"] == row["git_sha"] and entry["files"] == "pkg/alpha.py"
    assert why(cfg, comp, row) == ""                                            # current for that range
    assert attest.note(cfg, comp, "live", row["git_sha"]) == "current by attestation (renamed a local variable)"
    assert any("commit " in line for line in said)
    assert (cfg.results_path.parent / "attestations.csv").read_text().startswith("date,component,impl,from_sha,through_sha,author,reason,files")


def test_a_later_change_to_the_arms_own_code_makes_it_stale_again(tmp_path):
    cfg, row, comp = project(tmp_path)
    attest.attest(cfg, comp, "live", "comment only")
    (cfg.root / "pkg" / "alpha.py").write_text("def run():\n    return 99\n")
    commit(cfg)
    assert "pkg/alpha.py" in why(cfg, comp, row)
    attest.attest(cfg, comp, "live", "second look: still the same measure")      # chains from where the first ended
    assert why(cfg, comp, row) == ""
    assert attest.note(cfg, comp, "live", row["git_sha"]).count(";") == 1


def test_an_empty_reason_is_refused_and_nothing_is_written(tmp_path):
    cfg, row, comp = project(tmp_path)
    for reason in ("", "   "):
        with pytest.raises(attest.AttestError, match="reason is required"):
            attest.attest(cfg, comp, "live", reason)
    assert not (cfg.results_path.parent / "attestations.csv").exists()
    assert attest.run_cli(cfg, comp, "live", "", say=lambda text: None) == 2


def test_it_refuses_when_the_own_code_changed_outside_the_range(tmp_path):
    cfg, row, comp = project(tmp_path)
    (cfg.root / "pkg" / "alpha.py").write_text("def run():\n    return 7\n")        # uncommitted edit after the range
    with pytest.raises(attest.AttestError, match="outside the range"):
        attest.attest(cfg, comp, "live", "whitespace")
    first = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=cfg.root, capture_output=True, text=True).stdout.strip()
    commit(cfg)
    with pytest.raises(attest.AttestError, match="outside the range"):
        attest.attest(cfg, comp, "live", "whitespace", through=first)             # a commit after --through
    assert not (cfg.results_path.parent / "attestations.csv").exists()


def test_it_refuses_when_nothing_in_the_own_code_changed(tmp_path):
    cfg, row, comp = project(tmp_path, step="touch-a-doc")
    with pytest.raises(attest.AttestError, match="already current"):
        attest.attest(cfg, comp, "live", "docs only")


def test_a_test_or_another_arms_file_is_not_the_arms_code_so_there_is_nothing_to_attest(tmp_path):
    cfg, row, comp = project(tmp_path, step="touch-the-shared-utility")
    with pytest.raises(attest.AttestError, match="already current"):
        attest.attest(cfg, comp, "live", "util is another solution's")


def test_a_row_recorded_on_uncommitted_code_or_missing_is_refused(tmp_path):
    cfg, row, comp = project(tmp_path)
    with pytest.raises(attest.AttestError, match="no recorded"):
        attest.attest(cfg, "beta_eval", "live", "x")
    text = cfg.results_path.read_text().replace(row["git_sha"], row["git_sha"] + "-dirty")
    cfg.results_path.write_text(text)
    with pytest.raises(attest.AttestError, match="uncommitted code"):
        attest.attest(cfg, comp, "live", "x")


def test_the_leaderboard_shows_current_by_attestation_and_staleness_never_blocks_it(tmp_path):
    cfg, row, comp = project(tmp_path)
    attest.attest(cfg, comp, "live", "refactor that keeps behaviour")
    lines = []
    leaderboard.board(cfg, __import__("esoi.registry", fromlist=["load"]).load(cfg), say=lines.append, stale=harness.stale_reason, attested=attest.note)
    assert any("live: current by attestation (refactor that keeps behaviour)" in line for line in lines)
