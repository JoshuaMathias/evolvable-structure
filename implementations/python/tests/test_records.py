"""The intent records check: R1 to R5, over the scaffolded repository."""
from esoi import records, tables, template


def check(cfg, **kw):
    return records.check_records(cfg.structure, template.load_for(cfg), **kw)


def edit(cfg, name, key_col, key, col, value):
    path = cfg.structure / name
    rows, cols = tables.read_csv(path), tables.read_header(path)
    next(r for r in rows if r[key_col] == key)[col] = value
    tables.write_csv(path, cols, rows)


def tree_ids(cfg):
    """The ids of every record in the (single-folder) intent, as the parent links of a tree resolve against."""
    return records.overall_ids(cfg.structure)


def test_the_scaffold_is_clean(cfg):
    assert check(cfg) == []
    assert check(cfg, overall=tree_ids(cfg)) == []


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
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "knowledge", "")
    assert any(p.startswith("R2") for p in check(cfg))
    assert not any(p.startswith("R2 greet-a-person") for p in check(cfg, waived={"greet-a-person"}))


def test_an_empty_milestones_cell_is_an_honest_gap_not_a_finding(cfg):
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "milestones", "")
    assert not any(p.startswith("R2 greet-a-person") for p in check(cfg))
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "measures_of_success", "")
    assert any(p.startswith("R2 greet-a-person") and "measures_of_success" in p and "milestones" not in p for p in check(cfg))


def test_parent_links_resolve_in_the_tree(cfg):
    overall = tree_ids(cfg)
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "parent_ideal_ids", "ghost")
    edit(cfg, "problems.csv", "problem_id", "greeting-by-hand", "parent_problem_ids", "nope")
    problems = check(cfg, overall=overall)
    assert any(p.startswith("R5 greet-a-person") and "'ghost'" in p for p in problems)
    assert not any("ghost" in p for p in check(cfg, overall=overall, retired=set()) if "overall_solution_ids" in p)
    assert any(p.startswith("R5 greeting-by-hand") and "'nope'" in p for p in problems)


def test_a_parent_link_with_no_overall_network_is_reported(cfg):
    edit(cfg, "problems.csv", "problem_id", "greeting-by-hand", "parent_problem_ids", "purpose-unrecorded")
    assert any(p.startswith("R5") and "no overall network is configured" in p for p in check(cfg))


def test_require_parent_demands_a_parent_on_every_solution(cfg):
    overall = tree_ids(cfg)
    for col in ("parent_problem_ids", "parent_ideal_ids"):
        edit(cfg, "solutions.csv", "solution_id", "greet-a-person", col, "")
    assert not any(p.startswith("R5") for p in check(cfg, overall=overall))
    assert any(p.startswith("R5 greet-a-person") for p in check(cfg, overall=overall, require_parent=True))


def test_a_detailed_solution_may_take_its_problem_and_ideal_from_the_parents(cfg):
    overall = tree_ids(cfg)
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "problem_ids", "")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "ideal_ids", "")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "parent_problem_ids", "purpose-unrecorded")
    edit(cfg, "solutions.csv", "solution_id", "greet-a-person", "parent_ideal_ids", "explicit-purpose")
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
    problems = check(cfg, overall=tree_ids(cfg))
    assert any("lists run policy greet-a-person but greet-a-person does not list it in governs_metric_ids" in p for p in problems)
    srows[0]["governs_metric_ids"] = metric_id
    tables.write_csv(cfg.structure / "solutions.csv", scols + ["governs_metric_ids"], srows)
    assert check(cfg, overall=tree_ids(cfg)) == []
    srows[0]["governs_metric_ids"] = "ghost"
    tables.write_csv(cfg.structure / "solutions.csv", scols + ["governs_metric_ids"], srows)
    assert any("governs_metric_ids names 'ghost'" in p for p in check(cfg, overall=tree_ids(cfg)))


def test_implementation_records_are_matched_by_path_or_name_not_only_by_a_fixed_id(cfg):
    path = cfg.structure / "implementations.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    first = rows[0]
    extra = [dict(first, implementation_id="any-id-one", filepath="demo/providers.py::one"),
             dict(first, implementation_id="greet-a-person:two", filepath="demo/providers.py")]
    tables.write_csv(path, cols, rows + extra)
    solutions = cfg.structure / "solutions.csv"
    cells, scols = tables.read_csv(solutions), tables.read_header(solutions)
    cells[0]["implementations"] += ";demo/providers.py::one;demo/providers.py::two"
    tables.write_csv(solutions, scols, cells)
    overall = tree_ids(cfg)
    assert check(cfg, overall=overall) == []   # one by path, one by `solution:name`
    cells[0]["implementations"] += ";demo/providers.py::three"
    tables.write_csv(solutions, scols, cells)
    assert any("providers.py::three has no record" in p for p in check(cfg, overall=overall))


def test_the_retired_overall_column_is_reported_in_the_intent_layout(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows[0]["overall_solution_ids"] = "project-structure"
    tables.write_csv(path, cols + ["overall_solution_ids"], rows)
    problems = check(cfg, overall=tree_ids(cfg), retired={"overall_solution_ids"})
    assert any(p.startswith("R5 greet-a-person") and "retired" in p for p in problems)


def test_a_specification_solution_needs_no_interface_fields_or_metric_command(cfg):
    spec = next(r for r in tables.read_csv(cfg.structure / "solutions.csv") if r["solution_id"] == "project-structure")
    assert spec["parameters"] == ""
    assert check(cfg) == []   # none of its metrics has a command, so it is a specification, derived
    edit(cfg, "metrics.csv", "metric_id", "structure-coverage", "command", "esoi run greet_a_person --impl live")
    assert any(p.startswith("R2 project-structure") for p in check(cfg))


def test_removed_solution_columns_are_reported_with_where_their_content_goes(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for row in rows:
        row.update(metric_kind="eval", invariant_reason="", gap="", action="")
    tables.write_csv(path, cols + ["metric_kind", "invariant_reason", "gap", "action"], rows)
    problems = check(cfg)
    for old, where in (("metric_kind", "specification"), ("invariant_reason", "purpose"), ("gap", "disadvantages"),
                       ("action", "milestones")):
        assert any(p.startswith("R1") and f"removed column `{old}`" in p and where in p for p in problems), old


def test_a_solution_with_two_metrics_names_the_authoritative_one(cfg):
    path = cfg.structure / "metrics.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows.append({**{c: "" for c in cols}, "metric_id": "greeting-tone", "name": "Tone", "purpose": "How warm.",
                 "record": "A reviewer's rating.", "solution_ids": "greet-a-person", "command": "esoi run greet_a_person --impl live"})
    tables.write_csv(path, cols, rows)
    assert any(p.startswith("R6 greet-a-person") and "authoritative_metric_id" in p for p in check(cfg))
    spath = cfg.structure / "solutions.csv"
    srows, scols = tables.read_csv(spath), tables.read_header(spath)
    for row in srows:
        row["authoritative_metric_id"] = "greeting-pass-rate" if row["solution_id"] == "greet-a-person" else ""
    tables.write_csv(spath, scols + ["authoritative_metric_id"], srows)
    assert not any(p.startswith("R6") for p in check(cfg))
    for row in srows:
        row["authoritative_metric_id"] = "elsewhere" if row["solution_id"] == "greet-a-person" else ""
    tables.write_csv(spath, scols + ["authoritative_metric_id"], srows)
    assert any(p.startswith("R6 greet-a-person") and "is not one of the solution's metrics" in p for p in check(cfg))


def add_column(cfg, name, column, value="text"):
    path = cfg.structure / name
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for row in rows:
        row[column] = value
    tables.write_csv(path, cols + [column], rows)


def test_a_human_readable_column_outside_the_template_needs_the_owners_approval(cfg):
    add_column(cfg, "solutions.csv", "selected_by", "measured on the example cases")
    found = [p for p in check(cfg) if p.startswith("R7")]
    assert len(found) == 1 and "`selected_by`" in found[0]
    assert "person who owns the specification" in found[0] and "approved_fields" in found[0] and "SKILL.md" in found[0]
    assert "Joshua" not in found[0]
    # the owner approves it in the project's own configuration
    assert not [p for p in check(cfg, approved={"solutions.csv": {"selected_by"}}) if p.startswith("R7")]
    # approval of one file's column does not approve the same name in another file
    add_column(cfg, "problems.csv", "selected_by", "x")
    assert any(p.startswith("R7 problems.csv") for p in check(cfg, approved={"solutions.csv": {"selected_by"}}))


def test_ids_links_paths_commands_and_tracking_columns_are_technical(cfg):
    add_column(cfg, "solutions.csv", "custom_id", "x")
    add_column(cfg, "solutions.csv", "custom_ids", "x")
    add_column(cfg, "solutions.csv", "tracking_note", "x")
    assert not [p for p in check(cfg) if p.startswith("R7")]   # patterns and the library's own list: filepath, command, ...
    from esoi import records
    assert {"filepath", "command", "interface_name", "implementations", "selected", "sub_intent", "implements"} <= \
        set().union(*records.TECHNICAL_COLUMNS.values())


def test_the_owner_lists_approved_fields_in_esoi_toml(tmp_path):
    from esoi import config
    cfg = config.from_mapping({"records": {"approved_fields": {"solutions": ["area"], "metrics.csv": ["measured_through"]}}}, tmp_path)
    assert cfg.approved_fields == {"solutions.csv": {"area"}, "metrics.csv": {"measured_through"}}
    assert config.from_mapping({}, tmp_path).approved_fields == {}


def rename_header(cfg, name, old, new):
    path = cfg.structure / name
    rows, cols = tables.read_csv(path), tables.read_header(path)
    tables.write_csv(path, [new if c == old else c for c in cols], [{(new if k == old else k): v for k, v in r.items()} for r in rows])


def test_a_repository_with_the_old_column_names_gets_a_finding_not_a_crash(cfg):
    rename_header(cfg, "solutions.csv", "interface_name", "port")
    rename_header(cfg, "implementations.csv", "filepath", "path")
    found = check(cfg)
    assert any("`port`, renamed `interface_name`" in line for line in found)
    assert any("`path`, renamed `filepath`" in line for line in found)
    assert any("`port`" in line for line in records.check_headers(cfg.structure, template.load_for(cfg)))
    assert any("`path`" in line for line in records.check_headers(cfg.structure, template.load_for(cfg)))
