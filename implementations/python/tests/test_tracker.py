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


def test_one_metric_serving_several_solutions_is_one_tracker_row_and_passes_s18(cfg):
    from esoi import check
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows.append(dict(rows[0], solution_id="second-greeting"))
    tables.write_csv(path, cols, rows)
    metrics_path = cfg.structure / "metrics.csv"
    metrics = tables.read_csv(metrics_path)
    metrics[0]["solution_ids"] += ";second-greeting"
    tables.write_csv(metrics_path, tables.read_header(metrics_path), metrics)
    built = tracker.build(cfg, registry.load(cfg))
    assert [m["metric_id"] for m in built["metrics"]].count("greeting-pass-rate") == 1
    assert "second-greeting" in built["metrics"][0]["solution_ids"]
    assert not [line for line in check.check(cfg) if line.startswith("S18")]


def test_several_implementations_in_one_module_get_distinct_tracker_rows(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows[0]["implementations"] += ";demo/greet.py::alpha;demo/greet.py::beta"
    tables.write_csv(path, cols, rows)
    impls = cfg.structure / "implementations.csv"
    records = tables.read_csv(impls)
    records += [dict(records[0], implementation_id=f"custom-{name}", filepath=f"demo/greet.py::{name}") for name in ("alpha", "beta")]
    tables.write_csv(impls, tables.read_header(impls), records)
    ids = [r["implementation_id"] for r in tracker.build(cfg, registry.load(cfg))["implementations"]]
    assert "custom-alpha" in ids and "custom-beta" in ids and len(ids) == len(set(ids))
