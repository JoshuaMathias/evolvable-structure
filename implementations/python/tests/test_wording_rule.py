"""S51: a problem says what is true. An absolute in a problem's text is informed, never failed; ideals are not read."""
from esoi import check, config, tables


def edit_first(path, change):
    rows, cols = tables.read_csv(path), tables.read_header(path)
    keep = [dict(r) for r in rows]
    change(rows[0])
    tables.write_csv(path, cols, rows)
    return cols, keep


def test_an_absolute_in_a_problem_is_informed_and_never_fails(repo):
    path = config.load(repo).structure / "problems.csv"
    edit_first(path, lambda row: row.update(why_hard="Parts that are best alone can fail when assembled, and nobody tests the whole."))
    problems, advisory = check.check_all(config.load(repo))
    found = [line for line in advisory if line.startswith("S51 ")]
    assert len(found) == 1 and "why_hard" in found[0] and "nobody" in found[0]
    assert "literally true" in found[0] and "what is missing, for whom, how often and at what cost" in found[0]
    assert not [p for p in problems if p.startswith("S51")]


def test_a_problem_without_absolutes_is_not_informed(repo):
    path = config.load(repo).structure / "problems.csv"
    edit_first(path, lambda row: row.update(why_hard="Parts are usually measured alone; few projects share a measured way to judge "
                                                      "what each part adds to the whole."))
    problems, advisory = check.check_all(config.load(repo))
    assert not [line for line in advisory if line.startswith("S51 ")]


def test_an_ideal_may_state_an_absolute(repo):
    path = config.load(repo).structure / "ideals.csv"
    edit_first(path, lambda row: row.update(principle="Every part is always justified by what it adds to the whole, and nothing is kept that adds none."))
    problems, advisory = check.check_all(config.load(repo))
    assert not [line for line in advisory if line.startswith("S51 ")]


def test_a_true_absolute_is_waived_at_its_field(repo):
    cfg = config.load(repo)
    path = cfg.structure / "problems.csv"
    pid = tables.read_csv(path)[0]["problem_id"]
    edit_first(path, lambda row: row.update(problem="The service never stores a password; a person cannot recover one."))
    waivers = cfg.structure / "waivers.csv"
    rows = tables.read_csv(waivers) if waivers.exists() else []
    cols = tables.read_header(waivers) if waivers.exists() else ["rule", "path", "reason"]
    rows.append({k: "" for k in cols} | {"rule": "S51", "path": f"{pid}:problem", "reason": "true: the service holds no passwords"})
    tables.write_csv(waivers, cols, rows)
    problems, advisory = check.check_all(config.load(repo))
    assert not [line for line in advisory if line.startswith("S51 ")]


def test_an_ideal_written_as_a_solution_is_informed(repo):
    path = config.load(repo).structure / "ideals.csv"
    edit_first(path, lambda row: row.update(principle="Use one router for every model call."))
    problems, advisory = check.check_all(config.load(repo))
    found = [line for line in advisory if line.startswith("S52 ")]
    assert len(found) == 1 and "principle" in found[0] and "reads like a solution" in found[0] and "state that is wanted" in found[0]
    assert not [p for p in problems if p.startswith("S52")]


def test_an_ideal_written_as_a_state_is_not_informed(repo):
    path = config.load(repo).structure / "ideals.csv"
    edit_first(path, lambda row: row.update(principle="Every request reaches a model that is up and within its budget."))
    problems, advisory = check.check_all(config.load(repo))
    assert not [line for line in advisory if line.startswith("S52 ")]


def test_a_declarative_ideal_that_names_its_mechanism_is_informed(repo):
    path = config.load(repo).structure / "ideals.csv"
    edit_first(path, lambda row: row.update(principle="Any part can be replaced by configuration when another measures better."))
    problems, advisory = check.check_all(config.load(repo))
    assert any(line.startswith("S52 ") and "by configuration" in line for line in advisory)
