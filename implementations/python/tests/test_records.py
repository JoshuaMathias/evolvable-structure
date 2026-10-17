"""The intent records check: R1 to R5, over the scaffolded repository."""
from esoi import records, tables, template


def check(cfg, **kw):
    return records.check_records(cfg.structure, template.load_for(cfg), **kw)


def edit(cfg, name, key_col, key, col, value):
    path = cfg.structure / name
    rows, cols = tables.read_csv(path), tables.read_header(path)
    next(r for r in rows if r[key_col] == key)[col] = value
    tables.write_csv(path, cols, rows)


def test_the_scaffold_is_clean(cfg):
    overall = records.overall_ids(cfg.root / cfg.overall)
    assert check(cfg, overall=overall) == []
    assert check(cfg, overall=overall) == [] and records.check_records(
        cfg.root / cfg.overall, template.load_for(cfg), interface_required=False, require_command=False) == []


def test_an_empty_required_field_is_reported(cfg):
    edit(cfg, "problems.csv", "problem_id", "greeting-by-hand", "why_hard", "")
    assert any(p.startswith("R2 greeting-by-hand") and "why_hard" in p for p in check(cfg))


def test_a_problem_phrased_as_a_task_is_reported(cfg):
    edit(cfg, "problems.csv", "problem_id", "greeting-by-hand", "problem", "Build a greeting function.")
    assert any(p.startswith("R4") and "reads as a task" in p for p in check(cfg))


def test_a_problem_naming_its_own_solution_is_reported(cfg):
    edit(cfg, "problems.csv", "problem_id", "greeting-by-hand", "problem", "People lack greet-a-person badly.")
    assert any(p.startswith("R4") and "names its own solution" in p for p in check(cfg))


def test_links_must_agree_on_both_sides(cfg):
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "problem_ids", "")
    problems = check(cfg)
    assert any("addresses no problem" in p or "does not list it" in p for p in problems)


def test_an_unknown_link_target_is_reported(cfg):
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "ideal_ids", "ghost")
    assert any("'ghost'" in p and p.startswith("R3") for p in check(cfg))


def test_every_implementation_needs_a_record_and_the_reverse(cfg):
    path = cfg.structure / "implementations.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    tables.write_csv(path, cols, rows[1:])
    assert any("has no record" in p for p in check(cfg))


def test_waiving_a_solution_skips_its_template_fields(cfg):
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "goals", "")
    assert any(p.startswith("R2") for p in check(cfg))
    assert not any(p.startswith("R2 greet-a-person") for p in check(cfg, waived={"greet-a-person"}))


def test_parent_links_resolve_in_the_overall_network(cfg):
    overall = records.overall_ids(cfg.root / cfg.overall)
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "overall_solution_ids", "ghost")
    edit(cfg, "problems.csv", "problem_id", "greeting-by-hand", "parent_problem_ids", "nope")
    problems = check(cfg, overall=overall)
    assert any(p.startswith("R5 greet-a-person") and "'ghost'" in p for p in problems)
    assert any(p.startswith("R5 greeting-by-hand") and "'nope'" in p for p in problems)


def test_a_parent_link_with_no_overall_network_is_reported(cfg):
    assert any(p.startswith("R5") and "no overall network is configured" in p for p in check(cfg))


def test_require_parent_demands_a_parent_on_every_solution(cfg):
    overall = records.overall_ids(cfg.root / cfg.overall)
    for col in ("parent_problem_ids", "parent_ideal_ids", "overall_solution_ids"):
        edit(cfg, "solutions.csv", "solution_id", "greet-a-person", col, "")
    assert not any(p.startswith("R5") for p in check(cfg, overall=overall))
    assert any(p.startswith("R5 greet-a-person") for p in check(cfg, overall=overall, require_parent=True))


def test_a_detailed_solution_may_take_its_problem_and_ideal_from_the_parents(cfg):
    overall = records.overall_ids(cfg.root / cfg.overall)
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "problem_ids", "")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "ideal_ids", "")
    problems = check(cfg, overall=overall)
    assert not any("addresses no problem" in p or "has no ideal" in p for p in problems)


def test_implementation_ids_come_from_the_solution_and_the_file_stem():
    assert records.implementation_id("sol", "pkg/mod.py") == "sol:mod"
    assert records.implementation_id("sol", "plain-name") == "sol:plain-name"


def test_a_policy_solution_and_the_metrics_it_governs_must_agree(cfg):
    mrows, mcols = tables.read_csv(cfg.structure / "metrics.csv"), tables.read_header(cfg.structure / "metrics.csv")
    srows, scols = tables.read_csv(cfg.structure / "solutions.csv"), tables.read_header(cfg.structure / "solutions.csv")
    metric_id = mrows[0]["metric_id"]
    mrows[0]["run_policy_ids"] = "greet-a-person"
    tables.write_csv(cfg.structure / "metrics.csv", mcols + ["run_policy_ids"], mrows)
    problems = check(cfg, overall=records.overall_ids(cfg.root / cfg.overall))
    assert any("lists run policy greet-a-person but greet-a-person does not list it in governs_metric_ids" in p for p in problems)
    srows[0]["governs_metric_ids"] = metric_id
    tables.write_csv(cfg.structure / "solutions.csv", scols + ["governs_metric_ids"], srows)
    assert check(cfg, overall=records.overall_ids(cfg.root / cfg.overall)) == []
    srows[0]["governs_metric_ids"] = "ghost"
    tables.write_csv(cfg.structure / "solutions.csv", scols + ["governs_metric_ids"], srows)
    assert any("governs_metric_ids names 'ghost'" in p for p in check(cfg, overall=records.overall_ids(cfg.root / cfg.overall)))


def test_implementation_records_are_matched_by_path_or_name_not_only_by_a_fixed_id(cfg):
    path = cfg.structure / "implementations.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    first = rows[0]
    extra = [dict(first, implementation_id="any-id-one", path="demo/providers.py::one"),
             dict(first, implementation_id="greet-a-person:two", path="demo/providers.py")]
    tables.write_csv(path, cols, rows + extra)
    solutions = cfg.structure / "solutions.csv"
    cells, scols = tables.read_csv(solutions), tables.read_header(solutions)
    cells[0]["implementations"] += ";demo/providers.py::one;demo/providers.py::two"
    tables.write_csv(solutions, scols, cells)
    overall = records.overall_ids(cfg.root / cfg.overall)
    assert check(cfg, overall=overall) == []   # one by path, one by `solution:name`
    cells[0]["implementations"] += ";demo/providers.py::three"
    tables.write_csv(solutions, scols, cells)
    assert any("providers.py::three has no record" in p for p in check(cfg, overall=overall))
