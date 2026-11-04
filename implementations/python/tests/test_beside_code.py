"""Records kept beside the code: folders named by ``[records] beside_code`` are read as part of the same tree."""
import re

from conftest import fill_top_intent  # noqa: F401  (the cfg fixture fills the top intent)
from esoi import besidecode, check, config, implementedby, intents, readme, registry, tables
from test_intents import add_solution, lines, write_intent


def keep_beside(cfg):
    """List ``<package>/*`` as folders whose records are kept beside the code."""
    toml = cfg.root / "esoi.toml"
    text = toml.read_text()
    line = f'beside_code = ["{cfg.package_dir}", "{cfg.package_dir}/*"]\n'
    toml.write_text(text.replace("records.template_version", "records.beside_code = " + line.split("= ", 1)[1] + "records.template_version", 1))


def advice(cfg):
    """The advisory findings of rule S40 (they never fail the check)."""
    problems, advisory = check.check_all(cfg)
    assert not [p for p in problems if p.startswith("S40")]
    return [ln for ln in advisory if ln.startswith("S40")]


def beside(cfg, name="voice", solution="speak-a-greeting", sub_intent=""):
    """A code folder ``demo/<name>`` that holds a solution's records, listed in esoi.toml as kept beside the code."""
    folder = cfg.root / cfg.package_dir / name
    folder.mkdir()
    add_solution(cfg, folder, solution, "by-voice", sub_intent)
    keep_beside(cfg)
    return folder, config.load(cfg.root)


def test_a_folder_beside_the_code_is_read_into_the_same_registry(cfg):
    folder, after = beside(cfg)
    assert [f for _, f in intents.folders(after)][-1] == folder
    loaded = registry.load(after)
    row = next(r for r in loaded.every_solution() if r["solution_id"] == "speak-a-greeting")
    assert row["intent_id"] == intents.discover(after)[0].intent_id
    assert "speak-a-greeting:by-voice" in {r["implementation_id"] for r in loaded.implementations}
    assert "speak-a-greeting-needs-saying" in {r["problem_id"] for r in loaded.problems}


def test_a_repository_without_the_setting_reads_only_its_structure_folder(cfg):
    folder = cfg.root / cfg.package_dir / "voice"
    folder.mkdir()
    add_solution(cfg, folder, "speak-a-greeting", "by-voice")
    assert "speak-a-greeting" not in {r["solution_id"] for r in registry.load(cfg).every_solution()}
    assert intents.beside_folders(cfg) == []


def test_the_merged_tree_passes_the_record_rules(cfg):
    beside(cfg)
    assert [ln for ln in check.check(config.load(cfg.root)) if ln.split(" ")[0] in {"S26", "S28", "S29", "R1"}] == []


def test_a_row_kept_in_two_places_is_a_finding(cfg):
    folder, after = beside(cfg)
    other = cfg.root / cfg.package_dir / "echo"
    other.mkdir()
    tables.write_csv(other / "solutions.csv", tables.read_header(folder / "solutions.csv"), tables.read_csv(folder / "solutions.csv"))
    found = advice(config.load(cfg.root))
    assert any("speak-a-greeting" in ln and "kept in 2 places" in ln and "next: delete" in ln for ln in found), found


def test_a_row_also_left_in_the_structure_folder_is_a_finding(cfg):
    folder, after = beside(cfg)
    rows = tables.read_csv(folder / "solutions.csv")
    tables.write_csv(cfg.structure / "solutions.csv", tables.read_header(cfg.structure / "solutions.csv"),
                     tables.read_csv(cfg.structure / "solutions.csv") + rows)
    assert any("speak-a-greeting" in ln and "kept in 2 places" in ln for ln in advice(config.load(cfg.root)))


def test_a_beside_folder_with_an_intent_csv_is_a_sub_intent_of_the_implementation_it_names(cfg):
    folder = cfg.root / cfg.package_dir / "voices"
    write_intent(folder, "voices", "greet-a-person:live")
    keep_beside(cfg)
    from test_intents import rewrite
    rewrite(cfg.structure / "implementations.csv", lambda rows, cols: [r.update(sub_intent="voices" if r["implementation_id"] == "greet-a-person:live" else "") for r in rows])
    after = config.load(cfg.root)
    found = {i.intent_id: i for i in intents.discover(after)}
    assert found["voices"].parent == next(i.intent_id for i in found.values() if i.is_top)
    assert lines(after, "S28") == []
    page = readme.pages(after, registry.load(after))
    text = next(t for p, t in page if p == folder / "README.md")
    assert "This sub-intent arises as the implementation `greet-a-person:live`" in text and "../../README.md" in text


def test_a_solution_folder_gets_a_readme_with_its_solution_implementations_and_links(cfg):
    folder, after = beside(cfg)
    (cfg.root / "README.md").write_text("# project\n")
    text = dict(readme.pages(after, registry.load(after)))[folder / "README.md"]
    assert text.startswith("# ") and "`speak-a-greeting`" in text and "- Selected implementation: `by-voice`" in text
    assert "| `speak-a-greeting:by-voice` |" in text and "## Where to go next" in text
    assert "- Intent: [" in text and "../../README.md" in text
    top = dict(readme.pages(after, registry.load(after)))[after.structure / "README.md"]
    assert "Records beside the code:" in top and f"{cfg.package_dir}/voice/README.md" in top
    assert not re.search(r"/home/|\u2014|unconfirmed", text)


def test_the_check_reports_a_stale_folder_page_and_the_command_writes_it(cfg):
    folder, after = beside(cfg)
    assert readme.run_cli(after, check=True, say=lambda text: None) == 1
    readme.run_cli(after, say=lambda text: None)
    assert (folder / "README.md").is_file()
    assert readme.run_cli(after, check=True, say=lambda text: None) == 0
    (folder / "README.md").write_text("edited by hand\n")
    assert any("voice/README.md: out of date" in ln for ln in lines(after, "S8"))


def code_in(cfg, folder, name, solution):
    """A module in ``folder`` that the records of ``solution`` name as the code of its implementation."""
    (folder / name).write_text("VALUE = 1\n")
    rewrite_implementation(cfg, solution, f"{cfg.package_dir}/{folder.name}/{name}")


def rewrite_implementation(cfg, solution, path):
    for folder in [f for _, f in intents.folders(config.load(cfg.root))]:
        if (folder / "implementations.csv").is_file():
            rows, cols = tables.read_csv(folder / "implementations.csv"), tables.read_header(folder / "implementations.csv")
            if any(r["solution_id"] == solution for r in rows):
                tables.write_csv(folder / "implementations.csv", cols + (["filepath"] if "filepath" not in cols else []),
                                 [dict(r, filepath=path) if r["solution_id"] == solution else r for r in rows])


def test_s40_informs_when_a_solutions_code_is_two_links_from_its_spec_and_never_fails_the_check(cfg):
    folder, after = beside(cfg)
    deep = folder / "inner" / "deeper"
    deep.mkdir(parents=True)
    (deep / "arm.py").write_text("VALUE = 1\n")
    rewrite_implementation(cfg, "speak-a-greeting", f"{cfg.package_dir}/voice/inner/deeper/arm.py")
    found = advice(config.load(cfg.root))
    split = next(ln for ln in found if ln.startswith("S40 speak-a-greeting"))
    assert "more than one link apart" in split and "next: " in split
    assert any("voice/inner/deeper" in ln and "no README.md" in ln and "next: " in ln for ln in found)
    assert check.run_cli(config.load(cfg.root), strict=False, write=False, say=lambda text: None) in (0, 1)


def test_a_code_folder_with_records_and_a_readme_leaves_nothing_for_s40(cfg):
    folder, after = beside(cfg)
    (folder / "arm.py").write_text("VALUE = 1\n")
    rewrite_implementation(cfg, "speak-a-greeting", f"{cfg.package_dir}/voice/arm.py")
    besidecode.apply(after, besidecode.plan(after))
    after = config.load(cfg.root)
    readme.write(after, registry.load(after), say=lambda text: None)
    assert [ln for ln in advice(after) if "speak-a-greeting" in ln or "demo/voice" in ln] == []


def test_place_moves_each_record_beside_its_code_and_gather_moves_it_back(cfg):
    folder, after = beside(cfg)
    code = cfg.root / cfg.package_dir / "greet.py"
    assert code.is_file()
    rows = {n: len(tables.read_csv(cfg.structure / n)) for n in besidecode.KEY_OF}
    moves = besidecode.plan(after, "beside")
    moved = {(m.file, m.ident): m for m in moves}
    assert ("implementations.csv", "greet-a-person:greet") in moved
    assert moved[("implementations.csv", "greet-a-person:greet")].target == cfg.root / cfg.package_dir
    assert besidecode.apply(after, moves) == len(moves)
    after = config.load(cfg.root)
    assert besidecode.plan(after, "beside") == []
    assert sum(len(tables.read_csv(f / n)) for _, f in intents.folders(after) for n in besidecode.KEY_OF) == \
        sum(rows.values()) + len(tables.read_csv(folder / "solutions.csv")) + len(tables.read_csv(folder / "implementations.csv")) + \
        len(tables.read_csv(folder / "problems.csv"))
    assert intents.duplicate_rows(after) == []
    back = besidecode.plan(after, "gather")
    besidecode.apply(after, back)
    assert besidecode.plan(config.load(cfg.root), "gather") == []
    assert [r for r in tables.read_csv(cfg.structure / "solutions.csv") if r["solution_id"] == "speak-a-greeting"]


def test_a_row_never_leaves_the_intent_that_owns_it(cfg):
    sub = cfg.root / cfg.package_dir / "voices"
    write_intent(sub, "voices", "greet-a-person:live")
    keep_beside(cfg)
    inner = sub / "echo"
    inner.mkdir()
    add_solution(cfg, sub, "echo-a-greeting", "by-echo")
    (inner / "arm.py").write_text("VALUE = 1\n")
    rewrite_implementation(cfg, "echo-a-greeting", f"{cfg.package_dir}/voices/echo/arm.py")
    after = config.load(cfg.root)
    for move in besidecode.plan(after, "beside"):
        assert move.ident != "echo-a-greeting" or intents.owner_of(after, move.target, intents.named_folders(
            after, intents.discover_in_structure(after), intents.beside_folders(after))) == "voices"


def typescript_repo(repo):
    """The scaffold turned into a tiny TypeScript tree: no Python package at all, three source files, and records that name them by
    `filepath`. The solution records its own entry call in `usage_notes`."""
    import shutil
    for name in ("demo", "tests", "evaluation"):
        shutil.rmtree(repo / name)
    files = {"src/greet/greet.ts": "export const greet = (name: string) => `Hello, ${name}!`;\n",
             "src/greet/shout.ts": "export const shout = (name: string) => `HELLO, ${name}!`;\n",
             "src/app/main.ts": "import { greet } from '../greet/greet';\nconsole.log(greet('Ada'));\n"}
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    toml = repo / "esoi.toml"
    toml.write_text(toml.read_text().replace('package = "demo"', 'package = ""').replace('code_paths = ["demo"]', 'code_paths = ["src"]'))
    where = {"greet-a-person:greet": "src/greet/greet.ts", "greet-a-person:live": "src/greet/greet.ts",
             "greet-a-person:shout": "src/greet/shout.ts", "project-purpose:the-project": "src/app/main.ts"}
    rewrite_rows(repo / "esoi" / "implementations.csv", lambda r: r.update(filepath=where.get(r["implementation_id"], r["filepath"])))
    rewrite_rows(repo / "esoi" / "solutions.csv", lambda r: r["solution_id"] == "greet-a-person" and r.update(
        usage_notes='Call `greet("Ada")` wherever a greeting is needed instead of building the text inline.'))
    return config.load(repo)


def rewrite_rows(path, edit):
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for row in rows:
        edit(row)
    tables.write_csv(path, cols, rows)


def structure_problems(cfg):
    return [ln for ln in check.check(cfg) if ln.split(" ")[0] in {"S26", "S28", "S29", "R1", "S40"}]


def test_a_repository_with_no_python_uses_the_esoi_folder_layout_from_its_records_alone(repo):
    cfg = typescript_repo(repo)
    assert cfg.package == "" and not cfg.records.get("beside_code")
    assert structure_problems(cfg) == []
    text = dict(readme.pages(cfg, registry.load(cfg)))[cfg.structure / "README.md"]
    assert '`greet("Ada")`' in text and "## Diagram" in text
    assert advice(cfg) == []


def test_a_repository_with_no_python_uses_the_beside_code_layout_from_its_records_alone(repo):
    cfg = typescript_repo(repo)
    toml = cfg.root / "esoi.toml"
    toml.write_text(toml.read_text().replace("records.template_version", 'records.beside_code = ["src", "src/*"]\nrecords.template_version', 1))
    after = config.load(cfg.root)
    assert besidecode.code_hosts(after) == ["src", "src/app", "src/greet"]
    moves = besidecode.plan(after)
    assert {m.ident: m.target.relative_to(cfg.root).as_posix() for m in moves}["greet-a-person:shout"] == "src/greet"
    besidecode.apply(after, moves)
    after = config.load(cfg.root)
    readme.write(after, registry.load(after), say=lambda text: None)
    page = (cfg.root / "src" / "greet" / "README.md").read_text()
    assert '`greet("Ada")`' in page and "[`src/greet/shout.ts`](shout.ts)" in page and "../../esoi/README.md" in page
    assert structure_problems(after) == [] and advice(after) == []
    assert not intents.duplicate_rows(after)


def test_the_layout_needs_no_declaration_in_code_and_the_python_scan_finds_nothing(repo):
    cfg = typescript_repo(repo)
    view = readme.view_of(cfg, registry.load(cfg))
    assert view.declared == {}


def reference_to(cfg, name, text, solution_impl="greet-a-person:shout"):
    """A reference file ``src/greet/<name>`` and the implementation record that points to it."""
    (cfg.root / "src" / "greet" / name).write_text(text)
    rewrite_rows(cfg.structure / "implementations.csv",
                 lambda r: r["implementation_id"] == solution_impl and r.update(filepath=f"src/greet/{name}"))
    return config.load(cfg.root)


def test_a_registry_that_lists_a_path_that_does_not_resolve_is_a_finding_and_a_resolving_one_is_not(repo):
    cfg = typescript_repo(repo)
    cfg = reference_to(cfg, "registry.csv", "name,filepath\nGreeter,src/greet/greet.ts\nGone,src/greet/gone.ts\n")
    toml = cfg.root / "esoi.toml"
    toml.write_text(toml.read_text().replace("records.template_version", "rules.S40.enabled = true\nrecords.template_version", 1))
    found = advice(config.load(cfg.root))
    assert any("src/greet/registry.csv lists src/greet/gone.ts, which does not resolve" in ln and "next: " in ln for ln in found), found
    assert not any("greet.ts, which" in ln for ln in found)
    cfg = reference_to(config.load(cfg.root), "registry.csv", "name,filepath\nGreeter,src/greet/greet.ts\n")
    assert advice(cfg) == []


def test_a_registry_row_must_exist_and_a_markdown_reference_lists_the_files_it_links(repo):
    cfg = typescript_repo(repo)
    toml = cfg.root / "esoi.toml"
    toml.write_text(toml.read_text().replace("records.template_version", "rules.S40.enabled = true\nrecords.template_version", 1))
    cfg = reference_to(config.load(cfg.root), "services.csv", "id,filepath\nstripe,\n")
    rewrite_rows(cfg.structure / "implementations.csv", lambda r: r["implementation_id"] == "greet-a-person:shout" and r.update(filepath="src/greet/services.csv::paypal"))
    assert any("paypal is not a row of src/greet/services.csv" in ln for ln in advice(config.load(cfg.root)))
    rewrite_rows(cfg.structure / "implementations.csv", lambda r: r["implementation_id"] == "greet-a-person:shout" and r.update(filepath="src/greet/services.csv::stripe"))
    assert advice(config.load(cfg.root)) == []
    cfg = reference_to(config.load(cfg.root), "how.md", "The greeter is [here](greet.ts) and [there](missing.ts).\n")
    assert any("src/greet/missing.ts, which does not resolve" in ln for ln in advice(config.load(cfg.root)))
    assert implementedby.form_of(config.load(cfg.root), "src/greet/how.md").listed == ["src/greet/greet.ts", "src/greet/missing.ts"]
    assert implementedby.form_of(config.load(cfg.root), "src/greet/greet.ts").kind == "code"


def test_code_that_declares_a_solution_is_reported_when_the_registry_leaves_it_out(repo):
    cfg = config.load(repo)
    (cfg.root / "demo" / "registry.csv").write_text("filepath\n")
    rewrite_rows(cfg.structure / "implementations.csv", lambda r: r["implementation_id"] == "greet-a-person:shout" and r.update(filepath="demo/registry.csv"))
    toml = cfg.root / "esoi.toml"
    toml.write_text(toml.read_text().replace("records.template_version", "rules.S40.enabled = true\nrecords.template_version", 1))
    assert any(ln.startswith("S40 greet-a-person: demo/greet.py declares it but demo/registry.csv does not list it") and "next: " in ln
               for ln in advice(config.load(cfg.root)))


def test_the_folder_page_lists_the_files_that_implement_each_solution_from_the_records_and_the_ownership_map(repo):
    cfg = typescript_repo(repo)
    toml = cfg.root / "esoi.toml"
    toml.write_text(toml.read_text().replace("records.template_version", 'records.beside_code = ["src", "src/*"]\nrecords.template_version', 1))
    rewrite_rows(cfg.structure / "components.csv", lambda r: r["component_id"] == "esoi-records" and r.update(solutions=r["solutions"]))
    components = tables.read_csv(cfg.structure / "components.csv")
    tables.write_csv(cfg.structure / "components.csv", tables.read_header(cfg.structure / "components.csv"),
                     components + [dict(components[0], component_id="greeter-ts", layer="core", path="src/greet/*.ts", role="Greeters.", solutions="greet-a-person")])
    after = config.load(cfg.root)
    besidecode.apply(after, besidecode.plan(after))
    after = config.load(cfg.root)
    readme.write(after, registry.load(after), say=lambda text: None)
    page = (cfg.root / "src" / "greet" / "README.md").read_text()
    line = next(ln for ln in page.splitlines() if ln.startswith("- Implemented by:"))
    assert "[`src/greet/greet.ts`](greet.ts)" in line and "[`src/greet/shout.ts`](shout.ts)" in line
    assert readme.run_cli(after, check=True, say=lambda text: None) == 0


def test_a_program_handed_the_structure_folder_reads_and_writes_the_whole_tree(cfg):
    folder, after = beside(cfg)
    names = {r["solution_id"] for r in intents.read_tree(cfg.structure, "solutions.csv")}
    assert "speak-a-greeting" in names and "greet-a-person" in names
    assert folder in intents.tree_folders(cfg.structure) and cfg.structure.resolve() in intents.tree_folders(cfg.structure)
    assert intents.tree_folders(folder.parent.parent / "nowhere") == [(folder.parent.parent / "nowhere").resolve()]


# ---- arms whose code lives in an evaluation/impls folder while their record belongs to the owning intent -----------------------

def arm_in(cfg, where):
    """A solution beside the code in demo/voice whose implementation's code is the module ``where`` (a path from the root)."""
    folder, after = beside(cfg)
    code = cfg.root / where
    code.parent.mkdir(parents=True)
    code.write_text("VALUE = 1\n")
    rewrite_implementation(cfg, "speak-a-greeting", where)
    return folder, config.load(cfg.root)


def test_an_impls_folder_of_arms_owned_by_an_intent_is_covered_by_a_generated_readme_and_measured_through_the_owner(cfg):
    where = "evaluation/components/voice/impls/arm.py"
    folder, after = arm_in(cfg, where)
    found = advice(after)
    assert any("evaluation/components/voice/impls" in ln and "arms owned by" in ln and "esoi readmes" in ln for ln in found)
    assert not any("S40 speak-a-greeting" in ln for ln in found)                     # one link past the folder that holds the row
    assert besidecode.plan(after) == [] or all(m.ident != "speak-a-greeting:by-voice" for m in besidecode.plan(after))
    readme.write(after, registry.load(after), say=lambda text: None)
    page = (cfg.root / "evaluation/components/voice/impls/README.md").read_text()
    assert "speak-a-greeting:by-voice" in page and "arm.py" in page and "../../../../demo/voice/README.md" in page
    assert [ln for ln in advice(config.load(cfg.root)) if "evaluation" in ln or "speak-a-greeting" in ln] == []
    assert readme.stale(after, registry.load(after)) == []


def test_a_folder_that_is_not_an_arm_folder_is_still_flagged_until_it_is_listed_as_one(cfg):
    where = "tools/far/arm.py"
    folder, after = arm_in(cfg, where)
    found = advice(after)
    assert any("tools/far" in ln and "no README.md" in ln for ln in found) and any("S40 speak-a-greeting" in ln and "more than one link apart" in ln for ln in found)
    toml = cfg.root / "esoi.toml"
    toml.write_text(toml.read_text().replace("records.template_version", 'records.arm_folders = ["tools/*"]\nrecords.template_version', 1))
    listed = advice(config.load(cfg.root))
    assert any("tools/far" in ln and "arms owned by" in ln for ln in listed) and not any("S40 speak-a-greeting" in ln for ln in listed)


def test_a_readme_nobody_generated_keeps_covering_its_arm_folder(cfg):
    where = "evaluation/components/voice/impls/arm.py"
    folder, after = arm_in(cfg, where)
    (cfg.root / "evaluation/components/voice/impls/README.md").write_text("# Hand written\n")
    readme.write(after, registry.load(after), say=lambda text: None)
    assert (cfg.root / "evaluation/components/voice/impls/README.md").read_text() == "# Hand written\n"
    assert not any("evaluation" in ln for ln in advice(config.load(cfg.root)))


def test_a_missing_arm_page_is_not_a_failed_check_but_a_stale_one_is(cfg):
    where = "evaluation/components/voice/impls/arm.py"
    folder, after = arm_in(cfg, where)
    readme.write(after, registry.load(after), say=lambda text: None)
    assert not [p for p in check.check(config.load(cfg.root)) if "impls/README.md" in p]
    (cfg.root / "evaluation/components/voice/impls/README.md").write_text(
        (cfg.root / "evaluation/components/voice/impls/README.md").read_text() + "\nedited\n")
    assert any("impls/README.md" in p and p.startswith("S8") for p in check.check(config.load(cfg.root)))
    (cfg.root / "evaluation/components/voice/impls/README.md").unlink()
    assert not [p for p in check.check(config.load(cfg.root)) if "impls/README.md" in p]


# ---- code in a shared layer the intent's own code imports is one link from the intent -------------------------------------------

def shared_setup(cfg, layer="core", importer='from demo.core import arm\n'):
    """Solution `speak-a-greeting` kept in demo/voice (an area ranked with `echo` in `layers`), its arm in demo/<layer>/arm.py, and
    a module of the area that holds ``importer``."""
    toml = cfg.root / "esoi.toml"
    text = toml.read_text()
    assert 'layers = ["core"]' in text
    toml.write_text(text.replace('layers = ["core"]', 'layers = ["core", "adapters", ["voice", "echo"], "cli"]', 1))
    folder, after = beside(cfg)
    code = cfg.root / cfg.package_dir / layer
    code.mkdir(exist_ok=True)
    (code / "__init__.py").write_text("")
    (code / "arm.py").write_text("VALUE = 1\n")
    (folder / "__init__.py").write_text("")
    (folder / "use.py").write_text(importer)
    rewrite_implementation(cfg, "speak-a-greeting", f"{cfg.package_dir}/{layer}/arm.py")
    return config.load(cfg.root)


def ours(found):
    return [ln for ln in found if ln.startswith("S40 speak-a-greeting")]


def test_code_in_a_shared_layer_that_the_intents_code_imports_is_one_link_from_it(cfg):
    after = shared_setup(cfg)
    assert "demo/core/arm.py" in besidecode.import_graph(after)["demo/voice/use.py"]
    assert ours(advice(after)) == []


def test_code_in_a_shared_layer_the_intent_never_imports_is_still_flagged(cfg):
    after = shared_setup(cfg, importer="VALUE = 2\n")
    assert any("more than one link apart" in ln for ln in ours(advice(after)))


def test_a_docstring_or_a_string_naming_the_module_is_not_an_import(cfg):
    after = shared_setup(cfg, importer='"""Uses demo.core.arm."""\nNAME = "demo.core.arm"\n')
    assert any("more than one link apart" in ln for ln in ours(advice(after)))


def test_code_in_a_layer_above_the_area_is_not_shared_infrastructure(cfg):
    after = shared_setup(cfg, layer="cli", importer="from demo.cli import arm\n")
    assert any("more than one link apart" in ln for ln in ours(advice(after)))


def test_a_layer_the_configuration_does_not_declare_is_not_shared(cfg):
    after = shared_setup(cfg, layer="stuff", importer="from demo.stuff import arm\n")
    assert any("more than one link apart" in ln for ln in ours(advice(after)))


def test_an_area_that_wires_a_shared_member_by_name_reaches_it_and_a_docstring_does_not(cfg):
    wired = shared_setup(cfg, importer='MEMBERS = ("speak-a-greeting",)\n')
    assert ours(advice(wired)) == []


def test_a_docstring_naming_the_solution_is_not_wiring(cfg):
    after = shared_setup(cfg, importer='"""It uses speak-a-greeting."""\nVALUE = 1\n')
    assert any("more than one link apart" in ln for ln in ours(advice(after)))
