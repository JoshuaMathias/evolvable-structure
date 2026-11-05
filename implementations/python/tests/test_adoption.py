"""Rule S53 and the page section for solutions adopted from a library: references resolve, an adopted row restates nothing, an own solution
does not repeat a library solution, an arm declares the library's solution id, and the page links to the library's own words."""
import shutil

from conftest import fill_top_intent  # noqa: F401  (the cfg fixture fills the top intent)
from esoi.structure.intent_registry import config, registry, tables
from esoi.structure.library_adoption import resolve
from esoi.structure.structure_check import check
from esoi.understanding.readable_records import readme

LIBRARY_SOLUTION = "greet-a-person"


def adopt(repo, reference=f"@hub/{LIBRARY_SOLUTION}", **more):
    """Make a copy of the scaffolded repository the library ``hub`` and give ``repo`` an adopted row that references its solution."""
    hub = repo.parent / "hub"
    if not hub.exists():
        shutil.copytree(repo, hub)
        library = hub / "esoi" / "solutions.csv"   # the library says its own job in its own words, unlike the adopter's copy of the scaffold
        rows = tables.read_csv(library)
        for row in rows:
            row.update(purpose=f"Hub only {row['solution_id']}.", description=f"Hub only {row['solution_id']}.")
            if row["solution_id"] == LIBRARY_SOLUTION:
                row.update(purpose="Route each model request to the cheapest provider whose latency and budget fit it.",
                           description="Every request reaches a provider that is up and fits its budget. Providers are ranked by recorded latency, failures and price.")
        tables.write_csv(library, tables.read_header(library), rows)
    with (repo / "esoi.toml").open("a") as handle:
        handle.write('\n[adopts.hub]\nrepo = "../hub"\n')
    path = repo / "esoi" / "solutions.csv"
    cols, rows = tables.read_header(path), tables.read_csv(path)
    if "adopts" not in cols:
        cols = cols + ["adopts", "specializes"]
    blank = {col: "" for col in cols}
    rows = [{**blank, **r} for r in rows]
    rows.append({**blank, "solution_id": "greet-people", "name": "Greet people", "adopts": reference, **more})
    tables.write_csv(path, cols, rows)
    cfg = config.load(repo)
    check.write_docs(cfg, say=lambda text: None)
    return cfg


def s53(cfg):
    return [line for line in check.check_all(cfg)[1] if line.startswith("S53")]


def test_an_adopted_row_is_a_reference_and_the_check_stays_clean(repo):
    cfg = adopt(repo)
    loaded = registry.load(cfg)
    assert [r["solution_id"] for r in loaded.adopted] == ["greet-people"]
    assert "greet-people" in [r["solution_id"] for r in loaded.every_solution()]   # an id of an adopted solution resolves like any solution's
    assert "greet-people" not in [r["solution_id"] for r in loaded.authored()]
    assert check.check(cfg) == [] and s53(cfg) == []
    assert resolve.unresolved(cfg, loaded) == []


def test_a_reference_to_a_solution_the_library_does_not_have_is_informed(repo):
    cfg = adopt(repo, "@hub/no-such-solution")
    assert any("the library hub has no solution no-such-solution" in line for line in s53(cfg))


def test_a_reference_to_a_library_that_is_not_configured_is_informed(repo):
    cfg = adopt(repo, "@other/greet-a-person")
    found = s53(cfg)
    assert any("`[adopts.other] repo" in line for line in found)
    assert any(line.startswith("S53 greet-people:") for line in found)


def test_an_adopted_row_that_restates_the_library_is_informed_and_a_waiver_excuses_it(repo):
    cfg = adopt(repo, purpose="Greet one person by name.", problem_ids="greeting-by-hand")
    found = s53(cfg)
    assert len(found) == 1 and "purpose, problem_ids of its own" in found[0] and "empty those cells" in found[0]
    waivers = repo / "esoi" / "waivers.csv"
    tables.write_csv(waivers, tables.read_header(waivers), tables.read_csv(waivers) + [{"rule": "S53", "path": "greet-people", "reason": "kept while migrating"}])
    assert s53(config.load(repo)) == []


def test_an_own_solution_that_says_the_library_job_is_informed(repo):
    cfg = adopt(repo)
    library = next(r for r in registry.load(config.load(repo.parent / "hub")).every_solution() if r["solution_id"] == LIBRARY_SOLUTION)
    path = repo / "esoi" / "solutions.csv"
    cols, rows = tables.read_header(path), tables.read_csv(path)
    for row in rows:
        if row["solution_id"] == "project-structure":
            row.update(purpose=library["purpose"], description=library["description"])
    tables.write_csv(path, cols, rows)
    found = s53(config.load(repo))
    assert any(line.startswith("S53 project-structure:") and "adopt it" in line and LIBRARY_SOLUTION in line for line in found)


def test_an_arm_under_an_adopted_solution_must_declare_the_librarys_solution_id(repo):
    adopt(repo)
    code = repo / "demo" / "arm.py"
    code.write_text('from esoi import implementation\n\n\n@implementation("greet-people", "warm")\nclass Warm:\n    pass\n')
    path = repo / "esoi" / "implementations.csv"
    cols, rows = tables.read_header(path), tables.read_csv(path)
    rows.append({**{c: "" for c in cols}, "implementation_id": "greet-people:warm", "solution_id": "greet-people", "filepath": "demo/arm.py::Warm", "name": "Warm"})
    tables.write_csv(path, cols, rows)
    found = s53(config.load(repo))
    assert any(line.startswith("S53 greet-people:warm:") and f'@implementation("{LIBRARY_SOLUTION}"' in line for line in found)
    code.write_text(f'from esoi import implementation\n\n\n@implementation("{LIBRARY_SOLUTION}", "warm")\nclass Warm:\n    pass\n')
    assert s53(config.load(repo)) == []


def test_the_page_links_an_adopted_solution_to_the_library_and_shows_its_words_without_copying_them(repo):
    cfg = adopt(repo)
    page = dict(readme.pages(cfg, registry.load(cfg)))[cfg.structure / "README.md"]
    library = next(r for r in registry.load(config.load(repo.parent / "hub")).every_solution() if r["solution_id"] == LIBRARY_SOLUTION)
    assert "## Solutions from a library" in page
    assert f"({'../../hub/esoi/README.md'})" in page and "(`greet-people`)" in page and "Adopted from the library `hub`" in page
    assert library["description"].split(".")[0] in page
    stored = next(r for r in tables.read_csv(repo / "esoi" / "solutions.csv") if r["solution_id"] == "greet-people")
    assert stored["description"] == "" and stored["purpose"] == ""
