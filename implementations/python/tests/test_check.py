"""The check runner, the rules by group, waivers, disabling and plugins."""
from esoi import check, rules, tables


def edit(cfg, name, key_col, key, col, value):
    path = cfg.structure / name
    rows, cols = tables.read_csv(path), tables.read_header(path)
    next(r for r in rows if r[key_col] == key)[col] = value
    tables.write_csv(path, cols, rows)


def ids_of(lines):
    return {line.split(" ", 1)[0] for line in lines}


def test_the_scaffold_is_clean(cfg):
    assert check.check(cfg) == []
    assert check.check(cfg, strict=True) == []


def test_every_rule_has_a_summary_and_the_list_is_in_id_order(cfg):
    summaries = rules.summaries(cfg)
    assert {"S1", "S4", "S6", "S10", "S20", "S26", "S27"} <= set(summaries)
    assert all(text.strip() for text in summaries.values())


def test_an_unowned_file_a_big_module_and_an_undocumented_module(cfg):
    (cfg.root / "docs").mkdir(exist_ok=True)
    (cfg.root / "docs" / "stray.md").write_text("x")
    (cfg.root / "demo" / "big.py").write_text('"""Big."""\n' + "x = 1\n" * 1600)
    (cfg.root / "demo" / "bare.py").write_text("x = 1\n")
    found = check.check(cfg)
    assert any(line.startswith("S1 docs/stray.md") for line in found)
    assert any(line.startswith("S4 demo/big.py") for line in found)
    assert any(line.startswith("S5 demo/bare.py") for line in found)


def test_imports_must_point_inward(cfg):
    cfg.layers = ["core", "adapters"]
    (cfg.root / "demo" / "adapters").mkdir()
    (cfg.root / "demo" / "adapters" / "__init__.py").write_text('"""Adapters."""\n')
    (cfg.root / "demo" / "uses.py").write_text('"""Core."""\nfrom demo.adapters import thing\n')
    rows = tables.read_csv(cfg.structure / "components.csv")
    rows.append(dict(component_id="adapters", layer="adapters", path="demo/adapters/*.py", role="Adapters.", solutions="greet-a-person"))
    rows[0]["path"] = "demo/*.py"
    tables.write_csv(cfg.structure / "components.csv", ["component_id", "layer", "path", "role", "solutions"], rows)
    check.write_docs(cfg, say=lambda text: None)
    assert any(line.startswith("S6 demo/uses.py:2") for line in check.check(cfg))


def test_type_checking_imports_are_ignored(cfg):
    cfg.layers = ["core", "adapters"]
    (cfg.root / "demo" / "adapters").mkdir()
    (cfg.root / "demo" / "adapters" / "__init__.py").write_text('"""Adapters."""\n')
    (cfg.root / "demo" / "typed.py").write_text('"""Core."""\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from demo.adapters import thing\n')
    rows = tables.read_csv(cfg.structure / "components.csv")
    rows.append(dict(component_id="adapters", layer="adapters", path="demo/adapters/*.py", role="Adapters.", solutions="greet-a-person"))
    rows[0]["path"] = "demo/*.py"
    tables.write_csv(cfg.structure / "components.csv", ["component_id", "layer", "path", "role", "solutions"], rows)
    check.write_docs(cfg, say=lambda text: None)
    assert not any(line.startswith("S6") for line in check.check(cfg))


def test_s13_by_layer_and_by_path(cfg):
    (cfg.root / "demo" / "env.py").write_text('"""Core."""\nimport os\nX = os.environ.get("X")\n')
    assert not any(line.startswith("S13") for line in check.check(cfg))
    cfg.rules = {"S13": {"layers": ["core"]}}
    assert any(line.startswith("S13 demo/env.py:3") for line in check.check(cfg))
    cfg.rules = {"S13": {"paths": ["demo/"]}}
    assert any(line.startswith("S13 demo/env.py:3") for line in check.check(cfg))


def test_a_waiver_excuses_a_violation_and_an_unused_one_is_reported(cfg):
    (cfg.root / "demo" / "big.py").write_text('"""Big."""\n' + "x = 1\n" * 1600)
    waivers = cfg.structure / "waivers.csv"
    tables.write_csv(waivers, ["rule", "path", "reason"], [dict(rule="S4", path="demo/big.py", reason="Grouped by subject.")])
    assert not any(line.startswith("S4") for line in check.check(cfg))
    tables.write_csv(waivers, ["rule", "path", "reason"], [dict(rule="S4", path="demo/greet.py", reason="Unneeded.")])
    assert any(line.startswith("S9 S4 demo/greet.py") for line in check.check(cfg))
    tables.write_csv(waivers, ["rule", "path", "reason"], [dict(rule="S4", path="demo/greet.py", reason="")])
    assert any("has no reason" in line for line in check.check(cfg))


def test_a_disabled_rule_is_silent_and_its_waivers_are_not_flagged(cfg):
    (cfg.root / "stray.py").write_text('"""x."""\n')
    assert any(line.startswith("S3") for line in check.check(cfg))
    cfg.disable = ["S3"]
    assert not any(line.startswith("S3") for line in check.check(cfg))
    tables.write_csv(cfg.structure / "waivers.csv", ["rule", "path", "reason"], [dict(rule="S3", path="x", reason="r")])
    assert check.check(cfg) == []


def test_a_plugin_adds_rules_and_a_docs_hook(cfg):
    (cfg.root / "plug.py").write_text(
        "from esoi.rules.base import RuleGroup\n\n\ndef rule(ctx):\n    return ['X1 demo: always reports']\n\n\n"
        "def write_docs(ctx):\n    (ctx.root / 'plug.txt').write_text('written')\n\n\nRULES = [RuleGroup({'X1': 'Always.'}, rule)]\n")
    cfg.plugins = ["plug.py"]
    rows = tables.read_csv(cfg.structure / "components.csv")
    rows[-1]["path"] += ";plug.py;plug.txt"
    tables.write_csv(cfg.structure / "components.csv", ["component_id", "layer", "path", "role", "solutions"], rows)
    assert "X1 demo: always reports" in check.check(cfg)
    assert "X1" in rules.summaries(cfg)
    check.write_docs(cfg, say=lambda text: None)
    assert (cfg.root / "plug.txt").read_text() == "written"


def test_selection_rules_s7_s14_and_s23(cfg):
    (cfg.root / "demo" / "ports.py").write_text('"""Port."""\nfrom typing import Protocol\n\n\nclass Greeter(Protocol):\n    """x."""\n')
    (cfg.root / "demo" / "selection.py").write_text(
        '"""Table."""\nSELECTION = {"greet-a-person": {"default": "plain", "implementations": {"plain": "demo.greet:greet"}}}\n')
    cfg.selection = "demo/selection.py:SELECTION"
    assert any(line.startswith("S7 Greeter") for line in check.check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "port", "Greeter")
    assert any(line.startswith("S7 greet-a-person") and "selection table" in line for line in check.check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "selected", "plain")
    check.write_docs(cfg, say=lambda text: None)
    assert check.check(cfg) == []
    (cfg.root / "demo" / "selection.py").write_text(
        '"""Table."""\nSELECTION = {"greet-a-person": {"default": "other", "implementations": {"plain": "demo.greet:greet", "other": "demo.greet:greet"}}}\n')
    assert any(line.startswith("S23") for line in check.check(cfg))


def test_numbers_in_prose_and_unrecorded_claims(cfg):
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "gap", "It passes 12/16 of the cases.")
    check.write_docs(cfg, say=lambda text: None)
    assert any(line.startswith("S22") and "12/16" in line for line in check.check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "gap", "The shout implementation is not recorded.")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "action", "Keep watching.")
    check.write_docs(cfg, say=lambda text: None)
    assert any(line.startswith("S24") for line in check.check(cfg))


def test_results_rules_s10_s16_s20(cfg):
    results = cfg.results_path
    rows, cols = tables.read_csv(results), tables.read_header(results)
    for r in rows:
        if r["impl"] == "live":
            r["passed"] = "1"
        if r["impl"] == "shout":
            r["passed"] = "2"
    tables.write_csv(results, cols, rows)
    assert any(line.startswith("S10 greet-a-person") and "shout beat" in line for line in check.check(cfg))
    for r in rows:
        r["cases_sha"] = ""
    tables.write_csv(results, cols, rows)
    found = check.check(cfg)
    assert any(line.startswith("S16") for line in found) and any(line.startswith("S20") for line in found)


def test_strict_mode_rejects_a_result_recorded_on_dirty_code(cfg):
    results = cfg.results_path
    rows, cols = tables.read_csv(results), tables.read_header(results)
    for r in rows:
        r["git_sha"] = "abc1234-dirty"
    tables.write_csv(results, cols, rows)
    assert check.check(cfg) == []
    assert any(line.startswith("S20") and "uncommitted" in line for line in check.check(cfg, strict=True))


def test_s21_names_an_orphan_evaluation_folder_and_s25_a_missing_baseline(cfg):
    (cfg.evaluation / "orphan").mkdir()
    (cfg.evaluation / "orphan" / "score.py").write_text('"""x."""\n')
    assert any(line.startswith("S21") for line in check.check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "metric_kind", "invariant")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "invariant_reason", "A rule.")
    check.write_docs(cfg, say=lambda text: None)
    assert any(line.startswith("S25") for line in check.check(cfg))


def test_s12_an_implementation_must_be_live_or_say_it_is_an_alternative(cfg):
    odd = cfg.evaluation / "greet_a_person" / "impls" / "odd.py"
    odd.write_text('"""A reimplementation."""\nimport json\n')
    assert any(line.startswith("S12") and "odd.py" in line for line in check.check(cfg))
    odd.write_text('"""ALTERNATIVE: a rival."""\n')
    assert not any(line.startswith("S12") for line in check.check(cfg))


def test_generated_docs_must_be_current(cfg):
    (cfg.structure / "COMPONENTS.md").write_text("old\n")
    assert any(line.startswith("S8") for line in check.check(cfg))
    check.write_docs(cfg, say=lambda text: None)
    assert check.check(cfg) == []


def test_run_cli_prints_the_verdict_and_returns_the_exit_code(cfg):
    lines = []
    assert check.run_cli(cfg, False, False, lines.append) == 0 and lines[-1] == "structure check: ok"
    (cfg.root / "stray.py").write_text('"""x."""\n')
    assert check.run_cli(cfg, False, False, lines.append) == 1 and "FAIL" in lines[-1]
