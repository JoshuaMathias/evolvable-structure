"""Variants, circumstances, derived slice rows and the per-case log (esoi.variants, esoi.circumstances, esoi.harness)."""
import csv
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from esoi import check, circumstances, harness, leaderboard, runtime, variants
from esoi import config as config_module
from esoi.runtime import SelectionError

GUIDE = Path(__file__).resolve().parents[3] / "docs" / "guides" / "measure-per-circumstance.md"
QUIET = lambda text: None
HEADER = "circumstance_id,case_filter,run_filter,problem_ids,solution_ids\n"
BIG_SMALL = "big,size>5,,greeting-by-hand,greet-a-person\nsmall,size<=5,,greeting-by-hand,greet-a-person\n"


def test_a_variant_has_one_spelling_and_a_typo_fails_loudly():
    assert variants.canonical("fast_edit@lines=400,edit_format=auto") == "fast_edit@edit_format=auto,lines=400"
    assert variants.split("fast_edit@edit_format=auto,lines=400") == ("fast_edit", {"edit_format": "auto", "lines": 400})
    assert variants.split("plain") == ("plain", {}) and variants.base_of("a@b=c") == "a"
    for bad in ("a@", "a@b", "a@b=C", "a@b=1,b=2", "a@1=2"):
        with pytest.raises(ValueError):
            variants.split(bad)


def test_booleans_numbers_and_leading_zeros_read_as_what_they_are():
    assert variants.split("a@on=false,off=true,n=01,x=1.50,s=nan,u=1_0") == (
        "a", {"on": False, "off": True, "n": 1, "x": 1.5, "s": "nan", "u": "1_0"})
    assert variants.canonical("a@k=01") == variants.canonical("a@k=1") == "a@k=1"   # one arm, not two with one behaviour
    assert variants.canonical("a@on=false,n=-007,x=1.50") == "a@n=-7,on=false,x=1.5"


def test_conditions_compare_numbers_as_numbers_and_a_missing_fact_never_matches():
    facts = {"lines": 612, "model": "Claude-Haiku-5-5", "files": "2"}
    assert circumstances.matches("lines>400 and files>=2", facts) and circumstances.matches("lines>400 AND files>=2", facts)
    assert circumstances.matches("lines>400 And files>=2 and model != gpt", facts)
    assert not circumstances.matches("lines<=400", facts) and not circumstances.matches("tools>50", facts)
    assert circumstances.matches("", facts)
    # the example of the module docstring: an exact model id, any case
    assert circumstances.matches("model in claude-haiku-5-5|claude-mini-5", facts)
    assert not circumstances.matches("model in haiku|mini", facts)   # a fragment is not a model id: it never matches, by design
    assert circumstances.parse("a>1 AND b<2") == [("a", ">", ["1"]), ("b", "<", ["2"])]


def test_a_condition_that_cannot_be_read_is_rejected_not_a_term_that_never_matches():
    for bad in ("lines is big", "a>1 or b<2", "a>1 && b<2", "a>1 and", "a > 1 2", "model in a | b"):
        with pytest.raises(ValueError, match="not `field op value`"):
            circumstances.parse(bad)


def write_circumstances(repo, rows):
    (repo / "esoi" / "circumstances.csv").write_text(HEADER + rows)
    return config_module.load(repo)


@pytest.mark.parametrize("bad", ["files/large", "a;b", "Big", "slice:x", ""])
def test_a_circumstance_id_must_be_a_name_so_it_cannot_be_read_as_a_whole_run(repo, bad):
    """Hazard: `slice:files/large` is read by leaderboard.is_partial as the slice `large`'s tail, i.e. as a whole run."""
    assert leaderboard.is_partial({"sample": "slice:files/large"}) is False   # why the id must never carry a '/'
    cfg = write_circumstances(repo, f'"{bad}",size>5,,greeting-by-hand,greet-a-person\n')
    with pytest.raises(ValueError, match="circumstances.csv row 2"):
        circumstances.load(cfg)


def test_an_empty_duplicate_or_unreadable_row_fails_at_load_and_a_good_one_loads(repo):
    for rows, why in ((f"a,size>,,x,y\n", "not `field op value`"), ("a,,,x,y\n", "neither a case_filter nor a run_filter"),
                      ("a,size>1,,x,y\na,size>2,,x,y\n", "used twice")):
        with pytest.raises(ValueError, match=why):
            circumstances.load(write_circumstances(repo, rows))
    assert [c.circumstance_id for c in circumstances.load(write_circumstances(repo, BIG_SMALL))] == ["big", "small"]


def test_a_filter_naming_a_field_no_case_has_is_an_error_before_any_run():
    circs = [circumstances.Circumstance("big", case_filter="size>5 and colour=red")]
    with pytest.raises(ValueError, match="'colour', which no case of the component has"):
        circumstances.check_fields(circs, [{"id": "a", "size": 3}])
    circumstances.check_fields(circs, [{"id": "a", "size": 3, "colour": "red"}, {"id": "b"}])   # one case carrying it is enough


def test_slices_follow_the_case_filter_and_the_run_condition_of_the_run():
    circs = [circumstances.Circumstance("big", case_filter="size>5"), circumstances.Circumstance("native", run_filter="harness=native"),
             circumstances.Circumstance("never", case_filter="size>99"), circumstances.Circumstance("flag", run_filter="verify=true")]
    cases = [{"id": "a", "size": 3}, {"id": "b", "size": 9}]
    assert circumstances.slices(circs, cases, circumstances.run_context("haiku", "guard"))["big"] == [1]
    assert "native" not in circumstances.slices(circs, cases, circumstances.run_context("haiku", "guard"))
    inside = circumstances.slices(circs, cases, circumstances.run_context("haiku", "guard@harness=native,verify=true"))
    assert inside == {"big": [1], "native": [0, 1], "flag": [0, 1]}   # an empty slice ("never") is left out; true reads as a boolean
    assert circumstances.case_circumstances(circs, cases[1]) == ["big"]


LIVE = ('def build(meter, **params):\n    def run(kind, args):\n        n = args["n"]\n'
        '        return {"n": n if n <= params.get("cut", 5) else -1}\n    return run\n')
ALT = LIVE.replace("n <= params", "n > params")
PLAIN = 'def build(meter):\n    def run(kind, args):\n        return {"n": args["n"]}\n    return run\n'


def scenario(repo, circs=BIG_SMALL):
    """The scaffolded repository with eight numbered cases and arms that are right on opposite halves of them."""
    comp = repo / "evaluation" / "components" / "greet_a_person"
    for name, text in (("live", LIVE), ("alt", ALT), ("plain", PLAIN)):
        (comp / "impls" / f"{name}.py").write_text(text)
    (comp / "cases.json").write_text(json.dumps([
        {"id": f"c{n}", "kind": "k", "size": n, "heldout": n in (3, 7), "args": {"n": n}, "expect": {"eq": {"n": n}}}
        for n in range(1, 9)]))
    if circs:
        (repo / "esoi" / "circumstances.csv").write_text(HEADER + circs)
    cfg = config_module.load(repo)
    harness.prepare_path(cfg)
    return cfg, importlib.import_module("greet_a_person.score").score_case


def record(cfg, score, impl, *flags):
    return harness.run_component("greet_a_person", score, ["--impl", impl, "--record", *flags], cfg, QUIET)


def git(root, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_a_recorded_run_adds_a_row_per_circumstance_and_a_per_case_log_and_the_default_verdict_ignores_them(repo):
    cfg, score = scenario(repo)
    record(cfg, score, "live")
    summary, _ = record(cfg, score, "alt@cut=05")
    assert summary["impl"] == "alt@cut=5" and summary["passed"] == 3   # the recorded name is the canonical spelling
    log = [r for r in csv.DictReader(cfg.results_path.open()) if r["impl"] == "alt@cut=5"]
    assert [(r["sample"], r["passed"], r["cases"]) for r in log] == [("", "3", "8"), ("slice:big", "3", "3"), ("slice:small", "0", "5")]
    assert (log[1]["heldout"], log[2]["heldout"]) == ("1/1", "0/1")
    per_case = harness.read_per_case(cfg)
    assert len(per_case) == 16 and {r["impl"] for r in per_case} == {"live", "alt@cut=5"}
    assert next(r for r in per_case if r["impl"] == "live" and r["case_id"] == "c7")["circumstances"] == "big"
    history = leaderboard.all_results(cfg.results_path)["greet_a_person"]
    assert all(not leaderboard.slice_id(r) for rows in history.values() for r in rows)   # slices stay out of the default board
    assert leaderboard.verdict({i: h[-1] for i, h in history.items()}, "live", history=history)[0] == "WIN"
    record(cfg, score, "live", "--only", "c6,c7,c8")   # a named-case run records no slice and cannot decide the verdict
    assert len(harness.read_per_case(cfg)) == 16
    assert [v[:2] for v in leaderboard.slice_verdicts("greet_a_person", "live", leaderboard.slice_results(cfg.results_path))] == [
        ("big", "LOSS"), ("small", "WIN")]   # alt beats live in the big slice: a proposal for a person, nothing is selected


def test_the_per_case_log_merges_by_key_prunes_old_cases_and_never_leaves_a_temporary_file(repo):
    cfg, score = scenario(repo)
    path = repo / cfg.per_case
    record(cfg, score, "live")
    record(cfg, score, "alt@cut=5")
    record(cfg, score, "alt@cut=5")   # a re-record of the same arm replaces its rows: the file does not grow
    assert len(harness.read_per_case(cfg, every=True)) == 16
    other = repo / "evaluation" / "components" / "greet_a_person" / "cases.json"
    other.write_text(other.read_text().replace('"c8"', '"c8b"'))   # other cases: the arm's rows of the old cases are pruned
    record(cfg, score, "alt@cut=5")
    rows = harness.read_per_case(cfg, every=True)
    assert len(rows) == 16 and len({r["cases_sha"] for r in rows if r["impl"] == "alt@cut=5"}) == 1
    assert {r["cases_sha"] for r in rows if r["impl"] == "live"} != {r["cases_sha"] for r in rows if r["impl"] == "alt@cut=5"}
    # another recorder appended while this one worked: its rows survive a later recording by a third arm
    extra = dict(rows[0], impl="other-recorder", case_id="zz")
    with open(path, "a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, harness.PER_CASE_COLUMNS, lineterminator="\n").writerow(extra)
    record(cfg, score, "live")
    assert any(r["impl"] == "other-recorder" for r in harness.read_per_case(cfg))
    assert not list(path.parent.glob("*.tmp")) and path.read_text().count("component,impl") == 1


def test_a_slice_id_that_is_not_a_name_is_refused_when_the_row_is_written(repo):
    cfg, score = scenario(repo)
    bad = circumstances.Circumstance("files/large", case_filter="size>5")
    with pytest.raises(ValueError, match="slice id"):
        harness.record_slices(cfg, "greet_a_person", [bad], dict(component="greet_a_person", impl="live", sample="", tokens_in=0,
                                                                  tokens_out=0, cli_reported_cost_usd=0.0, model="none"),
                              [{"id": "a", "size": 9}], [dict(ok=True, calls=0, tokens_in=0, tokens_out=0, seconds=0.0)])


def test_editing_circumstances_makes_the_derived_rows_stale_until_the_arm_is_run_again(repo):
    cfg, score = scenario(repo)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    record(cfg, score, "live")
    record(cfg, score, "shout")
    latest = leaderboard.latest_results(cfg.results_path, whole=True)["greet_a_person"]
    assert harness.stale_reason(cfg, "greet_a_person", latest["live"], strict=False) == ""
    (repo / "esoi" / "circumstances.csv").write_text(HEADER + BIG_SMALL.replace("size>5", "size>6"))
    assert "circumstances.csv" in harness.stale_reason(cfg, "greet_a_person", latest["live"], strict=False)
    lines = []
    harness.rerun_stale(cfg, lines.append)
    assert any("live: stale, its slice rows and per-case log were not derived from the current circumstances.csv" in x for x in lines)
    lines.clear()
    harness.rerun_stale(cfg, lines.append)
    assert lines == ["greet_a_person/live: current", "greet_a_person/shout: current"]
    (repo / "esoi" / "circumstances.csv").write_text(HEADER + "big,size>,,x,y\n")   # unreadable: stale, and the run fails loudly
    assert "cannot be read" in harness.stale_reason(cfg, "greet_a_person", leaderboard.latest_results(cfg.results_path)["greet_a_person"]["live"])
    with pytest.raises(harness.RunError, match="not `field op value`"):
        record(cfg, score, "live")


def test_run_stale_judges_the_newest_whole_run_not_a_recorded_only_row(repo):
    """Hazard: with an `only:` row newest, `esoi run --stale` re-recorded `only:` rows forever."""
    cfg, score = scenario(repo, circs="")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    record(cfg, score, "live")
    record(cfg, score, "shout")
    record(cfg, score, "live", "--only", "c1,c2")
    size = cfg.results_path.read_text()
    assert harness.rerun_stale(cfg, QUIET) == 0
    assert cfg.results_path.read_text() == size   # nothing was re-recorded, least of all the only: row
    lines = []
    harness.rerun_stale(cfg, lines.append)
    assert lines == ["greet_a_person/live: current", "greet_a_person/shout: current"]
    (cfg.evaluation / "greet_a_person" / "cases.json").write_text((cfg.evaluation / "greet_a_person" / "cases.json").read_text() + " ")
    git(repo, "commit", "-q", "-am", "cases changed")
    harness.rerun_stale(cfg, QUIET)
    rows = [r for r in csv.DictReader(cfg.results_path.open()) if r["impl"] == "live"]
    assert rows[-1]["sample"] == "" and rows[-1]["cases"] == "8"   # re-recorded on the whole set, not on c1,c2
    assert harness.stale_arms(cfg)[0] == ("greet_a_person", "live")


def test_a_repository_without_circumstances_records_exactly_what_it_did_before(repo):
    cfg, score = scenario(repo, circs="")
    old = cfg.results_path.read_text()
    record(cfg, score, "live")
    record(cfg, score, "alt@cut=5")
    assert not (repo / cfg.per_case).exists() and circumstances.load(cfg) == []
    rows = list(csv.DictReader(cfg.results_path.open()))
    assert set(rows[0]) <= set(harness.RESULT_COLUMNS)   # no column of the circumstances feature
    assert len(rows) == len(old.splitlines()) + 1 and not any(r["sample"] for r in rows)   # one row per run, no slice rows
    assert harness.circumstances_stale(cfg, "greet_a_person", rows[-1]) == ""
    assert not [line for line in check.check(cfg) if "circumstance" in line or "per_case" in line]   # esoi check says nothing of it


def test_a_variant_key_the_arm_does_not_take_fails_the_arm_once_loudly_not_every_case(repo):
    cfg, score = scenario(repo)
    with pytest.raises(harness.RunError, match="takes no parameter cut"):
        record(cfg, score, "plain@cut=5")   # a wrapper whose build takes no parameters
    (repo / "demo" / "friendly.py").write_text(
        'from esoi import implementation\n\n\n@implementation("greet-a-person", "friendly")\ndef friendly(name, cheer="!"):\n'
        '    """A friendlier greeting."""\n    return f"Hi {name}{cheer}"\n')
    from esoi import cli
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        assert cli.main(["records", "sync"]) == 0
    finally:
        os.chdir(cwd)
    build = harness.declared_build(cfg, "greet_a_person", "friendly")
    assert build is not None
    with pytest.raises(harness.RunError, match="takes no parameter colour"):
        build(harness.CallMeter(), colour="red")
    assert callable(build(harness.CallMeter(), cheer="?"))
    assert not leaderboard.all_results(cfg.results_path).get("greet_a_person", {}).get("plain@cut=5")   # no 0/N row was recorded


def test_the_runtime_calls_a_variant_with_its_parameters_and_a_malformed_name_fails_loudly(repo, monkeypatch):
    monkeypatch.delenv(runtime.ROOT_ENV, raising=False)
    monkeypatch.syspath_prepend(str(repo))
    runtime.PROJECTS.clear()
    for name in ("demo", "demo.greet"):
        sys.modules.pop(name, None)
    module = importlib.import_module("demo.greet")
    try:
        runtime.register("greet-a-person", "pad", lambda name, fill="": f"{fill}{name}", scope="demo")
        assert module.greet("Ada", using="pad@fill=x") == "xAda"
        assert module.greet.chosen(using="pad@fill=x").name == "pad@fill=x"
        with pytest.raises(SelectionError, match="not key=value"):
            module.greet("Ada", using="pad@fill")
        with pytest.raises(SelectionError, match="unknown implementation"):
            module.greet("Ada", using="ghost@fill=x")
    finally:
        runtime.forget("greet-a-person")
        runtime.PROJECTS.clear()
        for name in ("demo", "demo.greet"):
            sys.modules.pop(name, None)


def test_the_guide_runs_as_written(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    blocks = re.findall(r"```python\n(.*?)```", GUIDE.read_text(encoding="utf-8"), re.S)
    assert len(blocks) == 3
    namespace = {"__name__": "guide"}
    for block in blocks:
        exec(compile(block, str(GUIDE), "exec"), namespace)   # the guide's own examples, run as written
    claimed = re.findall(r"^print\(.*\)\n# (.+)$", "\n".join(blocks), re.M)
    assert claimed and capsys.readouterr().out.splitlines() == claimed
