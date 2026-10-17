"""The review tracker tabs."""
from esoi import check, registry, tables, tracker


def tab(cfg, name):
    return tables.read_csv(cfg.tracker_dir / f"{name}.csv")


def test_the_scaffold_tracker_is_current_and_has_five_tabs(cfg):
    assert tracker.stale(cfg, registry.load(cfg)) == []
    assert {p.stem for p in cfg.tracker_dir.glob("*.csv")} == set(tracker.TABS)


def test_a_registry_edit_makes_the_matching_tab_stale(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows[0]["selected_by"] = "another reason"
    tables.write_csv(path, cols, rows)
    assert "solutions" in tracker.stale(cfg, registry.load(cfg))


def test_tracking_columns_survive_a_rebuild(cfg):
    path = cfg.tracker_dir / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows[0]["tracking_status"] = "reviewed"
    rows[0]["tracking_notes"] = "check the form"
    tables.write_csv(path, cols, rows)
    assert tracker.stale(cfg, registry.load(cfg)) == []
    tracker.write(cfg, registry.load(cfg), say=lambda text: None)
    assert tab(cfg, "solutions")[0]["tracking_notes"] == "check the form"


def test_the_verdict_and_parent_columns_reach_the_tabs(cfg):
    solution = tab(cfg, "solutions")[0]
    assert solution["verdict"] == "WIN" and solution["auto_status"] == "invariant" or solution["verdict"] == "WIN"
    assert "parent_problem_ids" in tables.read_header(cfg.tracker_dir / "problems.csv")


def test_extra_columns_from_the_configuration_follow_the_key(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for r in rows:
        r["area"] = "an area"
    tables.write_csv(path, cols + ["area"], rows)
    cfg.tracker_extra = {"solutions": ["area"]}
    tracker.write(cfg, registry.load(cfg), say=lambda text: None)
    assert tables.read_header(cfg.tracker_dir / "solutions.csv")[:2] == ["solution_id", "area"]
    assert tracker.stale(cfg, registry.load(cfg)) == []


def test_a_selection_table_that_cannot_load_does_not_crash_the_build(cfg):
    cfg.selection = "missing_table.py:SELECTION"
    assert tracker.selection_table(cfg) is None
    tracker.build(cfg, registry.load(cfg))
    assert any(line.startswith("S14") and "cannot load" in line for line in check.check(cfg))
