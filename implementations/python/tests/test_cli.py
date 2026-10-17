"""The command line, end to end over a scaffolded repository."""
import os

import pytest

from esoi import cli


def run(repo, *argv):
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        return cli.main(list(argv))
    finally:
        os.chdir(cwd)


def test_check_rules_records_and_tracker(repo, capsys):
    assert run(repo, "check") == 0 and "structure check: ok" in capsys.readouterr().out
    assert run(repo, "rules") == 0 and "S1 " in capsys.readouterr().out
    assert run(repo, "rules", "--markdown") == 0 and "- **S1**" in capsys.readouterr().out
    assert run(repo, "records") == 0
    assert run(repo, "tracker", "check") == 0 and "tracker ok" in capsys.readouterr().out
    assert run(repo, "tracker", "build") == 0


def test_run_and_leaderboard(repo, capsys):
    assert run(repo, "run", "greet_a_person", "--impl", "live") == 0
    assert "2/2 passed" in capsys.readouterr().out
    assert run(repo, "leaderboard") == 0 and "WIN" in capsys.readouterr().out
    assert run(repo, "run", "nothing") == 2


def test_check_fails_with_exit_code_one(repo, capsys):
    (repo / "stray.py").write_text('"""x."""\n')
    assert run(repo, "check") == 1 and "S3 stray.py" in capsys.readouterr().out


def test_a_missing_config_is_reported(tmp_path, capsys):
    assert run(tmp_path, "check") == 2 and "no esoi.toml" in capsys.readouterr().err


def test_template_sync_needs_a_source(repo, capsys):
    assert run(repo, "template", "check") == 2 and "not found" in capsys.readouterr().out


def test_select_needs_a_table(repo, capsys):
    assert run(repo, "select", "x") == 2


def test_init_and_hygiene(tmp_path, capsys):
    target = tmp_path / "fresh"
    target.mkdir()
    assert cli.main(["init", str(target), "--package", "fresh_pkg"]) == 0
    assert (target / "esoi.toml").exists() and "esoi check" in capsys.readouterr().out
    os.system(f"git -C {target} init -q && git -C {target} add -A")
    assert cli.main(["hygiene", "--root", str(target)]) == 0


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 0 and "esoi" in capsys.readouterr().out
