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


def test_run_stale_passes_its_flag_to_the_harness(repo, capsys):
    assert run(repo, "run", "--stale", "--no-record") == 0
    assert "greet_a_person/live: current" in capsys.readouterr().out


def test_hygiene_outside_a_git_checkout_scans_the_folder(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("fine\n")
    assert cli.main(["hygiene", "--root", str(tmp_path)]) == 0 and "clean" in capsys.readouterr().out
    assert cli.main(["hygiene", "--root", str(tmp_path), "--staged"]) == 2 and "not a git checkout" in capsys.readouterr().out


def test_a_bad_hygiene_pattern_in_the_config_is_a_message_not_a_traceback(tmp_path, capsys):
    (tmp_path / "esoi.toml").write_text('[hygiene.patterns]\nbad = "("\n')
    assert cli.main(["hygiene", "--root", str(tmp_path)]) == 2 and "not a regular expression" in capsys.readouterr().err


def test_run_stale_lists_paid_arms_and_accepts_the_opt_in_flags(repo, capsys):
    (repo / "esoi.toml").write_text((repo / "esoi.toml").read_text() + '\npaid_arms = ["greet_a_person/shout"]\n')
    results = repo / "evaluation" / "components" / "greet_a_person" / "cases.json"
    results.write_text(results.read_text() + " ")
    assert run(repo, "run", "--stale", "--no-record") == 0
    out = capsys.readouterr().out
    assert "greet_a_person/shout: stale" in out and "SKIPPED" in out and "--include greet_a_person/shout" in out
    assert run(repo, "run", "--stale", "--no-record", "--include", "greet_a_person/shout") == 0
    assert "greet_a_person/shout: run" in capsys.readouterr().out


def test_run_says_what_is_wrong_instead_of_a_traceback(repo, capsys):
    assert run(repo, "run", "greet_a_person", "--impl", "nope") == 2 and "no implementation 'nope'; known: live, shout" in capsys.readouterr().out
    assert run(repo, "run", "greet_a_person", "--impl", "live", "--only", "ZZ") == 2 and "matches no case" in capsys.readouterr().out
    assert run(repo, "run", "greet_a_person", "--impl", "live", "--sample", "0") == 2 and "at least 1" in capsys.readouterr().out


def test_a_malformed_config_is_a_message_for_every_command(tmp_path, capsys):
    (tmp_path / "esoi.toml").write_text("bad = [\n")
    for argv in (["check"], ["hygiene", "--root", str(tmp_path)]):
        assert cli.main(["--config", str(tmp_path / "esoi.toml"), *argv]) == 2
        assert "not valid TOML" in capsys.readouterr().err


def test_select_and_consumer_report_their_own_mistakes(repo, capsys):
    (repo / "esoi.toml").write_text((repo / "esoi.toml").read_text() + '\nselection = "demo/selection.py:SELECTION"\n')
    (repo / "demo" / "selection.py").write_text('SELECTION = {"greet-a-person": {"default": "plain", "implementations": {"plain": "demo.greet:greet"}}}\n')
    assert run(repo, "select", "greet-a-person") == 0 and "greet-a-person: plain" in capsys.readouterr().out
    assert run(repo, "select", "ghost") == 2 and "no selection table entry" in capsys.readouterr().err
    assert run(repo, "select", "greet-a-person", "--name", "ghost") == 2 and "unknown implementation" in capsys.readouterr().err
    assert run(repo, "consumer", "check", "--registry", "none.csv") == 2 and "no library named" in capsys.readouterr().err
    assert run(repo, "consumer", "check", "--registry", "none.csv", "--library", "demo") == 1
    assert "registry file not found" in capsys.readouterr().out
