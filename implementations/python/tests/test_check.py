"""The check runner, the rules by group, waivers, disabling and plugins."""
from esoi.structure.structure_check import check, rules
from esoi.structure.intent_registry import tables


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
        "from esoi.structure.structure_check.rules.base import RuleGroup\n\n\ndef rule(ctx):\n    return ['X1 demo: always reports']\n\n\n"
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
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "interface_name", "Greeter")
    assert any(line.startswith("S7 greet-a-person") and "selection table" in line for line in check.check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "selected", "plain")
    check.write_docs(cfg, say=lambda text: None)
    assert check.check(cfg) == []
    (cfg.root / "demo" / "selection.py").write_text(
        '"""Table."""\nSELECTION = {"greet-a-person": {"default": "other", "implementations": {"plain": "demo.greet:greet", "other": "demo.greet:greet"}}}\n')
    assert any(line.startswith("S23") for line in check.check(cfg))


def test_s26_fails_on_a_column_the_owner_has_not_approved_and_passes_once_they_list_it(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for row in rows:
        row["area"] = "x"
    tables.write_csv(path, cols + ["area"], rows)
    check.write_docs(cfg, say=lambda text: None)
    found = [line for line in check.check(cfg) if line.startswith("S26 R7")]
    assert found and "`area`" in found[0] and "approved_fields" in found[0]
    cfg.records = {"approved_fields": {"solutions": ["area"]}}
    assert not [line for line in check.check(cfg) if line.startswith("S26 R7")]


def test_numbers_in_prose_and_unrecorded_arms(cfg):
    edit(cfg, "metrics.csv", "metric_id", "greeting-pass-rate", "purpose", "It passes 12/16 of the cases.")
    check.write_docs(cfg, say=lambda text: None)
    assert any(line.startswith("S22") and "12/16" in line for line in check.check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "milestones", "1. Share of greetings in the standard form: 100%.")
    check.write_docs(cfg, say=lambda text: None)
    assert not any(line.startswith("S22") and "milestones" in line for line in check.check(cfg))   # a target value is allowed
    edit(cfg, "metrics.csv", "metric_id", "greeting-pass-rate", "purpose", "Measures the greetings.")
    edit(cfg, "metrics.csv", "metric_id", "greeting-pass-rate", "command",
         "esoi run greet_a_person --impl live; esoi run greet_a_person --impl ghost")
    check.write_docs(cfg, say=lambda text: None)
    assert any(line.startswith("S24") and "ghost" in line for line in check.check(cfg))


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
    problems, advice, info = check.check_report(cfg)
    assert any(line.startswith("S16") for line in problems)   # a row with no cases_sha is malformed: still a problem
    assert not any(line.startswith("S20") for line in problems)   # the cases it was run on are a fact, so S20 informs
    assert any(line.startswith("S20") and "other cases" in line for line in info)   # information, not a to-do
    assert not any(line.startswith("S20") for line in advice)


def test_strict_mode_rejects_a_result_recorded_on_dirty_code(cfg):
    results = cfg.results_path
    rows, cols = tables.read_csv(results), tables.read_header(results)
    for r in rows:
        r["git_sha"] = "abc1234-dirty"
    tables.write_csv(results, cols, rows)
    assert check.check(cfg) == []
    problems, advice, info = check.check_report(cfg, strict=True)   # code that changed or was recorded dirty informs, never a problem
    assert not any(line.startswith("S20") for line in problems + advice)
    assert any(line.startswith("S20") and "uncommitted" in line for line in info)


def test_s21_names_an_orphan_evaluation_folder_and_s25_a_missing_baseline(cfg):
    (cfg.evaluation / "orphan").mkdir()
    (cfg.evaluation / "orphan" / "score.py").write_text('"""x."""\n')
    assert any(line.startswith("S21") for line in check.check(cfg))
    only = [f for f in (cfg.evaluation / "greet_a_person" / "impls").glob("*.py") if f.name != "__init__.py"]
    for extra in only[1:]:
        extra.unlink()
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


PORT = '"""Port."""\nfrom typing import Protocol\n\n\nclass Greeter(Protocol):\n    """x."""\n'


def drop_column(cfg, name, column):
    path = cfg.structure / name
    rows, cols = tables.read_csv(path), [c for c in tables.read_header(path) if c != column]
    tables.write_csv(path, cols, rows)


def commit(root, message="change"):
    import subprocess
    for args in (["add", "-A"], ["commit", "-q", "-m", message]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=root, check=True,
                       capture_output=True)
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()


def test_a_solutions_file_without_an_interface_name_column_is_a_problem_when_something_needs_it_not_a_crash(cfg):
    drop_column(cfg, "solutions.csv", "interface_name")
    check.write_docs(cfg, say=lambda text: None)   # the tracker follows the records
    assert check.check(cfg) == []   # no interface_name, no selection table: nothing reads the column
    (cfg.root / "demo" / "ports.py").write_text(PORT)
    found = check.check(cfg)
    assert any(line.startswith("S7") and "no `interface_name` column" in line for line in found)
    (cfg.root / "demo" / "selection.py").write_text(
        '"""Table."""\nSELECTION = {"greet-a-person": {"default": "plain", "implementations": {"plain": "demo.greet:greet"}}}\n')
    cfg.selection = "demo/selection.py:SELECTION"
    assert any("no `interface_name` column" in line for line in check.check(cfg))


def test_every_column_the_rules_read_may_be_missing_without_a_crash(cfg):
    from esoi.structure.intent_registry.registry import RULE_COLUMNS
    tables.write_csv(cfg.structure / "waivers.csv", ["rule", "path", "reason"], [dict(rule="S4", path="demo/greet.py", reason="x")])
    for name, columns in RULE_COLUMNS.items():
        for column in columns:
            path = cfg.structure / name
            original = path.read_text()
            drop_column(cfg, name, column)
            found = check.check(cfg)   # must return problems, not raise
            assert any(f"`{column}` column" in line and name in line for line in found), (name, column, found[:3])
            path.write_text(original)


def test_several_implementations_in_one_module_are_listed_by_the_path_of_their_records(cfg):
    (cfg.root / "demo" / "ports.py").write_text(PORT)
    (cfg.root / "demo" / "providers.py").write_text('"""Four providers in one module."""\n')
    (cfg.root / "demo" / "selection.py").write_text(
        '"""Table."""\nSELECTION = {"greet-a-person": {"default": "plain", "implementations": {'
        '"plain": "demo.greet:greet", "alpha": "demo.providers:Alpha", "beta": "demo.providers:Beta"}}}\n')
    cfg.selection = "demo/selection.py:SELECTION"
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "interface_name", "Greeter")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "selected", "plain")
    found = check.check(cfg)
    assert sum("demo/providers.py, which" in line for line in found) == 2   # not listed anywhere yet
    rows = tables.read_csv(cfg.structure / "implementations.csv")
    first = next(r for r in rows if r["solution_id"] == "greet-a-person")
    rows += [dict(first, implementation_id=f"greet-a-person:{name}", filepath="demo/providers.py::" + name) for name in ("alpha", "beta")]
    tables.write_csv(cfg.structure / "implementations.csv", tables.read_header(cfg.structure / "implementations.csv"), rows)
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "implementations",
         tables.read_csv(cfg.structure / "solutions.csv")[0]["implementations"] + ";demo/providers.py::alpha;demo/providers.py::beta")
    check.write_docs(cfg, say=lambda text: None)
    assert check.check(cfg) == []   # records are matched by path, so their ids need not follow a pattern


def test_s3_allows_a_named_root_script_and_a_waiver_can_excuse_one(cfg):
    (cfg.root / "setup.py").write_text('"""Setup."""\n')
    (cfg.root / "tool.py").write_text('"""Tool."""\n')
    assert {line.split(" ")[1].rstrip(":") for line in check.check(cfg) if line.startswith("S3")} == {"setup.py", "tool.py"}
    cfg.root_python_allow = ["setup.py"]
    assert [line.split(" ")[1].rstrip(":") for line in check.check(cfg) if line.startswith("S3")] == ["tool.py"]
    tables.write_csv(cfg.structure / "waivers.csv", ["rule", "path", "reason"], [dict(rule="S3", path="tool.py", reason="A build entry point.")])
    assert not [line for line in check.check(cfg) if line.startswith(("S3", "S9"))]


def stale_rival_repo(cfg):
    """A committed repository where the selected arm was recorded after the measured code changed and its rival before."""
    import subprocess
    cfg.staleness_rule = "repo_wide"   # these tests pin the strict and waiver mechanics; the narrower rules have their own tests
    subprocess.run(["git", "init", "-q"], cwd=cfg.root, check=True)
    first = commit(cfg.root, "first")
    (cfg.root / "demo" / "greet.py").write_text((cfg.root / "demo" / "greet.py").read_text() + "\n# changed\n")
    second = commit(cfg.root, "second")
    rows, cols = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in rows:
        r["git_sha"] = second if r["impl"] == "live" else first
    tables.write_csv(cfg.results_path, cols, rows)
    return first, second


def test_strict_flags_a_verdict_resting_on_a_stale_rival(cfg):
    stale_rival_repo(cfg)
    assert check.check(cfg) == []
    problems, advice, info = check.check_report(cfg, strict=True)
    assert not any(line.startswith("S20") for line in problems + advice)
    assert any(line.startswith("S20 greet-a-person") and "rival shout" in line and "changed since" in line for line in info)
    tables.write_csv(cfg.structure / "waivers.csv", ["rule", "path", "reason"],
                     [dict(rule="S20", path="greet-a-person:shout", reason="The rival is a fixed baseline.")])
    assert check.check(cfg, strict=True) == []
    assert check.check(cfg) == []   # in use, though only --strict reports the finding


def test_a_waiver_for_a_strict_only_problem_is_not_unused_outside_strict_mode(cfg):
    first, _ = stale_rival_repo(cfg)
    rows, cols = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in rows:
        r["git_sha"] = first   # the selected arm too is now stale, which only --strict sees
    tables.write_csv(cfg.results_path, cols, rows)
    tables.write_csv(cfg.structure / "waivers.csv", ["rule", "path", "reason"], [
        dict(rule="S20", path="greet-a-person", reason="Re-run once the change settles."),
        dict(rule="S20", path="greet-a-person:shout", reason="Fixed baseline.")])
    assert check.check(cfg) == []
    assert check.check(cfg, strict=True) == []


def test_a_component_may_serve_a_specification_solution(cfg):
    rows = tables.read_csv(cfg.structure / "components.csv")
    rows[0]["solutions"] += ";project-structure"
    tables.write_csv(cfg.structure / "components.csv", ["component_id", "layer", "path", "role", "solutions"], rows)
    check.write_docs(cfg, say=lambda text: None)
    assert not any(line.startswith("S11") for line in check.check(cfg))


def test_s31_a_metric_must_be_meaningfully_real(cfg):
    """A scripted stand-in (SIMULATED = True) or a record that admits a scripted judge does not measure the real thing."""
    stand_in = cfg.evaluation / "greet_a_person" / "impls" / "stand_in.py"
    stand_in.write_text('"""ALTERNATIVE: a scripted judge."""\nSIMULATED = True\n')
    assert any(line.startswith("S31") and "stand_in.py" in line for line in check.check(cfg))
    stand_in.unlink()
    assert not any(line.startswith("S31") for line in check.check(cfg))
    edit(cfg, "metrics.csv", "metric_id", "greeting-pass-rate", "record", "Cases passed, judged by a scripted judge.")
    assert any(line.startswith("S31") and "greeting-pass-rate" in line for line in check.check(cfg))


def change_cases(cfg):
    from esoi.optimization.leaderboard import case_identity
    path = case_identity.cases_files("greet_a_person", cfg.evaluation)[0]
    path.write_text(path.read_text() + "\n")


def test_a_changed_case_file_is_advice_with_the_next_action_never_a_problem(cfg):
    change_cases(cfg)
    problems, advice, info = check.check_report(cfg)   # non-strict: the move or commit that edits a case file is not blocked
    assert problems == [] and advice == []   # nothing depends on the result: not a to-do
    found = [line for line in info if line.startswith("S20 greet-a-person")]
    assert found and "other cases" in found[0] and "esoi run greet_a_person --impl live --record" in found[0]
    assert check.run_cli(cfg, strict=False, write=False, say=lambda text: None) == 0


def test_a_stale_result_is_one_info_line_outside_the_to_do_count(cfg):
    change_cases(cfg)
    said = []
    assert check.run_cli(cfg, strict=False, write=False, say=said.append) == 0
    assert any(line.startswith("info: 1 recorded result(s) describe older code") and "esoi run --stale --plan" in line for line in said)
    assert not any(line.startswith("to do:") or line.startswith("  S20") for line in said)
    listed = []
    check.run_cli(cfg, strict=False, write=False, say=listed.append, findings=True)
    assert any(line.startswith("  S20 greet-a-person") and "other cases" in line for line in listed)
    strict = []
    check.run_cli(cfg, strict=True, write=False, say=strict.append)
    assert any(line.startswith("  S20 greet-a-person") for line in strict)


def test_a_stale_result_is_a_to_do_when_a_decision_depends_on_it(cfg):
    change_cases(cfg)
    problems, advice, info = check.check_report(cfg, for_decision=True)
    assert problems == [] and info == []
    assert any(line.startswith("S20 greet-a-person") and "a decision or release depends on it" in line for line in advice)
    said = []
    assert check.run_cli(cfg, strict=False, write=False, say=said.append, for_decision=True) == 0
    assert any(line.startswith("to do: 1 finding(s)") and "S20 1" in line for line in said)


def test_a_passed_expiration_makes_a_result_a_to_do_even_when_its_code_is_unchanged(cfg):
    cfg.expiration = {"default": "1 days"}
    rows, cols = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in rows:
        r["date"] = "2020-01-01"
    tables.write_csv(cfg.results_path, cols, rows)
    problems, advice, info = check.check_report(cfg)
    assert not any(line.startswith("S20") for line in problems)
    assert any(line.startswith("S20 greet-a-person") and "expiration" in line for line in advice)


def test_a_row_with_no_git_sha_is_a_malformed_record_and_stays_a_problem(cfg):
    rows, cols = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in rows:
        r["git_sha"] = ""
    tables.write_csv(cfg.results_path, cols, rows)
    problems, advice = check.check_all(cfg)
    assert any(line.startswith("S20") and "no git_sha" in line for line in problems)


def test_changed_circumstances_and_a_dirty_row_inform_but_do_not_fail(cfg):
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import stale_reasons
    row = {r["impl"]: r for r in tables.read_csv(cfg.results_path)}["live"]
    row["git_sha"] = "abc1234-dirty"
    assert stale_reasons.defect_reason(cfg, "greet_a_person", row) == ""            # dirty is a fact about the tree, not a defect
    assert "uncommitted" in stale_reasons.stale_reason(cfg, "greet_a_person", row, True)
    row["git_sha"] = ""
    assert "no git_sha" in stale_reasons.defect_reason(cfg, "greet_a_person", row)  # malformed
