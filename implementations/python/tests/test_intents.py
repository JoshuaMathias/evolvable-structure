"""Intents as containers: discovery, the rules S28 and S29, the legacy layout and the migration helper."""
import shutil

from conftest import fill_top_intent
from esoi import check, config, intents, migrate, registry, tables, tracker


def rewrite(path, edit):
    rows, cols = tables.read_csv(path), tables.read_header(path)
    edit(rows, cols)
    tables.write_csv(path, cols, rows)


def add_sub_intent(cfg, opportunity="A creative space the parent solution does not cover."):
    """A sub-intent folder that arises from the scaffold's greet-a-person:live implementation."""
    sub = cfg.structure / "voices"
    sub.mkdir()
    tables.write_csv(sub / "intent.csv", ["intent_id", "name", "vision_statement", "implements", "opportunity"],
                     [dict(intent_id="voices", name="Greeting voices", vision_statement="Every greeting is spoken warmly.",
                           implements="greet-a-person:live", opportunity=opportunity)])
    rewrite(cfg.structure / "implementations.csv",
            lambda rows, cols: [r.update(sub_intent="voices" if r["implementation_id"] == "greet-a-person:live" else "")
                                for r in rows])
    return sub


def lines(cfg, rule):
    return [line for line in check.check(cfg) if line.startswith(rule)]


def test_the_scaffold_leaves_the_top_intent_to_the_project(tmp_path):
    from esoi import scaffold
    scaffold.init(tmp_path, "mine", say=lambda text: None)
    problems = check.check(config.load(tmp_path))
    assert len(problems) == 1 and problems[0].startswith("S28") and "name, vision_statement" in problems[0]
    assert "ESOI" not in (tmp_path / "docs" / "structure" / "intent.csv").read_text()
    fill_top_intent(tmp_path)
    assert check.check(config.load(tmp_path)) == []


def test_the_scaffold_has_a_structure_solution_that_uses_esoi(cfg):
    row = next(r for r in tables.read_csv(cfg.structure / "implementations.csv") if r["solution_id"] == "project-structure")
    assert "@esoi/structure-check" in row["uses_solution_ids"] and "greet-a-person" in row["uses_solution_ids"]


def test_a_cross_project_use_must_be_written_with_a_project_id(cfg):
    rewrite(cfg.structure / "implementations.csv",
            lambda rows, cols: [r.update(uses_solution_ids="@esoi") for r in rows if r["solution_id"] == "project-structure"])
    assert any("@project_id/solution_id" in line for line in lines(cfg, "S29"))


def test_the_scaffold_is_one_top_intent_with_no_sub_intent(cfg):
    found = intents.discover(cfg)
    assert [i.intent_id for i in found] == ["demo"] and found[0].is_top and cfg.intent_mode
    assert check.check(cfg) == [] and check.notes(cfg) == []


def test_a_sub_intent_arises_from_an_implementation_of_its_parent(cfg):
    add_sub_intent(cfg)
    found = {i.intent_id: i for i in intents.discover(cfg)}
    assert found["voices"].parent == "demo"
    rows = registry.load(cfg).implementations
    assert {r["implementation_id"] for r in rows} >= {"greet-a-person:live"}
    assert not lines(cfg, "S28") and not lines(cfg, "S29")
    assert "intent_id" in tables.read_header(cfg.tracker_dir / "solutions.csv")


def test_a_sub_intent_needs_an_opportunity(cfg):
    add_sub_intent(cfg, opportunity="")
    assert any("opportunity" in line for line in lines(cfg, "S28"))


def test_a_sub_intent_must_implement_an_implementation_that_names_it_back(cfg):
    sub = add_sub_intent(cfg)
    rewrite(cfg.structure / "implementations.csv", lambda rows, cols: [r.update(sub_intent="") for r in rows])
    assert any("names it in `sub_intent`" in line for line in lines(cfg, "S28"))
    rewrite(sub / "intent.csv", lambda rows, cols: [r.update(implements="greet-a-person:ghost") for r in rows])
    assert any("not an implementation record" in line for line in lines(cfg, "S28"))


def test_the_top_intent_implements_nothing(cfg):
    rewrite(cfg.structure / "intent.csv", lambda rows, cols: [r.update(implements="x:y") for r in rows])
    assert any("top intent" in line for line in lines(cfg, "S28"))


def test_records_of_a_sub_intent_link_anywhere_in_the_tree(cfg):
    sub = add_sub_intent(cfg)
    template_cols = tables.read_header(cfg.structure / "solutions.csv")
    top = next(r for r in tables.read_csv(cfg.structure / "solutions.csv") if r["solution_id"] == "greet-a-person")
    tables.write_csv(sub / "solutions.csv", template_cols, [dict(top, solution_id="speak-it", implementations="", selected="",
                                                                metric_kind="specification", problem_ids="greeting-by-hand",
                                                                ideal_ids="consistent-greeting", metric_ids="greeting-pass-rate")])
    registry_ids = [r["solution_id"] for r in registry.load(cfg).every_solution()]
    assert "speak-it" in registry_ids
    problems = [line for line in check.check(cfg) if "speak-it" in line and line.startswith(("S26", "S29"))]
    assert any("does not list it" in line for line in problems)   # back-links must agree across intents too


def test_ids_are_unique_across_the_tree_and_uses_solution_ids_resolve(cfg):
    rewrite(cfg.structure / "implementations.csv",
            lambda rows, cols: ([r.update(uses_solution_ids="ghost") for r in rows if r["implementation_id"] == "greet-a-person:live"]))
    assert any("'ghost'" in line for line in lines(cfg, "S29"))
    rewrite(cfg.structure / "problems.csv", lambda rows, cols: [r.update(problem_id="greet-a-person") for r in rows[:1]])
    assert any("more than one kind" in line for line in lines(cfg, "S29"))


def test_a_folder_without_an_intent_file_is_not_an_intent(cfg):
    assert [i.intent_id for i in intents.discover(cfg)] == ["demo"]   # the tracker folder holds records but no intent.csv
    assert (cfg.tracker_dir).is_dir()


TOP = {"purpose-unrecorded", "explicit-purpose", "project-structure", "structure-coverage"}


def make_legacy(repo):
    """Turn the scaffold into the legacy two-level layout: overall records in structure/overall, parent links in place."""
    structure = repo / "docs" / "structure"
    overall = structure / "overall"
    overall.mkdir()
    (structure / "intent.csv").unlink()
    shutil.rmtree(structure / "tracker")
    for name, key in (("problems.csv", "problem_id"), ("ideals.csv", "ideal_id"), ("solutions.csv", "solution_id"),
                      ("implementations.csv", "implementation_id"), ("metrics.csv", "metric_id")):
        path = structure / name
        rows, cols = tables.read_csv(path), tables.read_header(path)
        def is_top(r):
            return r[key] in TOP or r[key].startswith("project-structure:")
        top = [r for r in rows if is_top(r)]
        rest = [r for r in rows if not is_top(r)]
        for r in top:
            r.pop("metric_kind", None)
        if name == "solutions.csv":
            for r in rest:
                r.update(overall_solution_ids="project-structure", parent_problem_ids="purpose-unrecorded", parent_ideal_ids="explicit-purpose")
            cols = cols + ["overall_solution_ids"]
        if name == "implementations.csv":
            for r in top:
                r["selected"] = "yes"
            top_cols = [c for c in cols if c not in ("path", "sub_intent", "uses_solution_ids")] + ["selected"]
            tables.write_csv(overall / name, top_cols, top)
        else:
            tables.write_csv(overall / name, [c for c in cols if not c.startswith("parent_") and c != "overall_solution_ids"
                                              and c not in ("port", "selected", "selected_by", "invariant_reason", "gap",
                                                            "action", "command")] + (["command"] if False else []), top)
        tables.write_csv(path, cols, rest)
    (repo / "esoi.toml").write_text((repo / "esoi.toml").read_text() + 'overall = "docs/structure/overall"\n')
    return repo


def test_the_legacy_layout_still_loads_and_passes_with_one_note(repo):
    make_legacy(repo)
    cfg = config.load(repo)
    assert not cfg.intent_mode
    tracker.write(cfg, registry.load(cfg), say=lambda text: None)
    assert check.check(cfg) == []
    assert any("legacy two-level layout" in line and "migrate-to-intents" in line for line in check.notes(cfg))


def test_migrate_moves_the_overall_network_into_the_top_intent(repo):
    make_legacy(repo)
    cfg = config.load(repo)
    done, manual = migrate.plan(cfg, apply=False)
    assert not (cfg.structure / "intent.csv").exists() and any("intent.csv" in line for line in done)
    migrate.plan(cfg, apply=True)
    (repo / "esoi.toml").write_text((repo / "esoi.toml").read_text().replace('overall = "docs/structure/overall"\n', ""))
    shutil.rmtree(cfg.structure / "overall")
    after = config.load(repo)
    assert after.intent_mode
    rows = {r["implementation_id"]: r for r in tables.read_csv(after.structure / "implementations.csv")}
    assert rows["project-structure:esoi-records"]["uses_solution_ids"] == "greet-a-person"
    solution = next(r for r in tables.read_csv(after.structure / "solutions.csv") if r["solution_id"] == "project-structure")
    assert solution["metric_kind"] == "specification" and solution["selected"] == "esoi-records"
    assert "overall_solution_ids" not in tables.read_header(after.structure / "solutions.csv")
    check.write_docs(after, say=lambda text: None)
    unfilled = check.check(after)   # the migration leaves the top intent's name and vision to the project
    assert unfilled and all(line.startswith("S28") and "name" in line and "vision_statement" in line for line in unfilled)
    fill_top_intent(repo)
    assert check.check(after) == []


def test_migrate_refuses_where_there_is_nothing_to_migrate(cfg):
    try:
        migrate.plan(cfg)
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected a refusal")
