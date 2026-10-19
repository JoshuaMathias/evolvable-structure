"""`esoi init` writes a repository that passes every rule and runs."""
import importlib

from esoi import check, config, harness, scaffold, tables


def test_init_passes_every_rule_but_the_top_intent_and_does_not_overwrite(tmp_path):
    lines = []
    written = scaffold.init(tmp_path, "my-demo", say=lines.append)
    assert "esoi.toml" in written and (tmp_path / "my_demo" / "greet.py").exists()
    cfg = config.load(tmp_path)
    assert cfg.package == "my_demo" and [l[:3] for l in check.check(cfg)] == ["S28"]   # only the top intent is left to you
    (tmp_path / "my_demo" / "greet.py").write_text('"""Mine."""\n')
    again = scaffold.init(tmp_path, "my-demo", say=lines.append)
    assert "my_demo/greet.py" not in again and (tmp_path / "my_demo" / "greet.py").read_text() == '"""Mine."""\n'
    assert any("kept existing" in line for line in lines)


def test_the_recorded_numbers_are_what_the_harness_measures(tmp_path):
    scaffold.init(tmp_path, "numbers_demo", say=lambda text: None)
    cfg = config.load(tmp_path)
    harness.prepare_path(cfg)
    score = importlib.import_module("greet_a_person.score")
    live, _ = harness.run_component("greet_a_person", score.score_case, ["--impl", "live"], cfg, lambda text: None)
    shout, _ = harness.run_component("greet_a_person", score.score_case, ["--impl", "shout"], cfg, lambda text: None)
    recorded = {r["impl"]: r["passed"] for r in tables.read_csv(cfg.results_path)}
    assert recorded == {"live": str(live["passed"]), "shout": str(shout["passed"])}


def test_python_name_makes_a_valid_package_name():
    assert scaffold.python_name("My Repo-1") == "my_repo_1" and scaffold.python_name("9lives") == "pkg_9lives"
    assert scaffold.python_name("---") == "mypackage"
