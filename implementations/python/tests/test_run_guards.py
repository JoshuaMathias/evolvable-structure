"""The ceiling and public-first guards of ``esoi run``: each refusal, each override, the balanced exception, the stale skip."""
import csv
import importlib

import pytest

from esoi.optimization.measurement_harness import component_folder
from esoi.optimization.measurement_harness import record_result
from esoi.optimization.measurement_harness import rerun_stale, stale_reasons
from esoi.optimization.measurement_harness import run_command
from esoi.optimization.when_metrics_are_run import run_guards
from esoi.structure.intent_registry.config import Config
from test_harness import BUILD, git, make

EVIDENCE = ("evidence_id,candidate,dimension,measure,value,unit,better,comparator,source_url,source_kind,run_by_independent,"
            "method_disclosed,n,benchmark_status,date_published,date_checked,confounds,note\n"
            "E1,big-model,quality,pass_rate,0.9,fraction,higher,Public-Bench,https://example.org/e1,independent_benchmark,yes,yes,500,live,"
            "2026-09-01,2026-10-30,,\n"
            "E2,small-model,quality,pass_rate,0.8,fraction,higher,Public-Bench,https://example.org/e2,vendor_reported,no,yes,500,live,"
            "2026-09-01,2026-10-30,,\n")


def project(tmp_path, name, balance=None):
    """A committed toy project: arms ``cheap`` and ``big`` (both paid), ``free`` (offline), cases A and B."""
    cfg = make(tmp_path, name)
    impls = tmp_path / "evaluation" / "components" / name / "impls"
    for arm in ("cheap", "big"):
        (impls / f"{arm}.py").write_text("PAID = True\n" + BUILD)
    (impls / "free.py").write_text(BUILD)
    if balance:
        cfg.balance = {name: balance}
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    component_folder.prepare_path(cfg)
    return cfg


def record(cfg, name, impl, cost, seconds=1.0, passed=2, sample=""):
    record_result.record_result(dict(component=name, impl=impl, cases=2, passed=passed, model_calls=2, cost_usd=cost, seconds=seconds,
                               model="m", sample=sample), cfg, date="2026-10-30")


def run(cfg, name, *flags):
    lines = []
    code = run_command.run_cli([name, "--impl", *flags], cfg, lines.append)
    return code, lines


def last_details(cfg):
    return list(csv.DictReader(cfg.results_path.open()))[-1]["details"]


def test_ceiling_refuses_a_costlier_arm_when_a_cheaper_one_passed_every_case(tmp_path):
    cfg = project(tmp_path, "c1")
    record(cfg, "c1", "cheap", 0.01)
    code, lines = run(cfg, "c1", "big")
    assert code == 2 and "esoi run: big is not run" in lines[-1] and "cheap already passed 2/2" in lines[-1]
    assert "--force" in lines[-1] and "\n" not in lines[-1]
    assert "big" not in {r["impl"] for r in csv.DictReader(cfg.results_path.open())}


def test_pass_or_fail_metric_refuses_even_an_arm_with_no_record_but_lets_a_known_cheaper_one_run(tmp_path):
    cfg = project(tmp_path, "c2")
    record(cfg, "c2", "big", 0.10)
    record(cfg, "c2", "cheap", 0.02, passed=1)   # recorded cheaper than the perfect arm: it may win the cost tie-break
    assert run(cfg, "c2", "cheap")[0] == 0
    (tmp_path / "other").mkdir()
    cfg2 = project(tmp_path / "other", "c2b")
    record(cfg2, "c2b", "cheap", 0.01)
    assert run(cfg2, "c2b", "big")[0] == 2   # no record for big, pass or fail only: it cannot exceed a perfect arm


def test_force_runs_it_and_records_the_reason(tmp_path):
    cfg = project(tmp_path, "c3")
    record(cfg, "c3", "cheap", 0.01)
    code, _ = run(cfg, "c3", "big", "--record", "--force", "checking a new model version")
    assert code == 0 and "forced past ceiling: checking a new model version" in last_details(cfg)
    assert run(cfg, "c3", "big", "--force", "  ")[0] == 2   # an override needs a reason


def test_balanced_metric_lets_a_cheaper_or_faster_arm_run_and_refuses_a_provably_worse_one(tmp_path):
    cfg = project(tmp_path, "c4", balance={"cost_per_case_usd": 1.0, "seconds_per_case": 60})
    record(cfg, "c4", "cheap", 0.10, seconds=10)
    record(cfg, "c4", "big", 0.50, seconds=20, passed=1)   # costlier and slower: cannot beat a perfect cheap arm
    assert run(cfg, "c4", "big")[0] == 2
    record(cfg, "c4", "big", 0.05, seconds=30, passed=1)   # cheaper, though slower: the balanced score may favour it
    assert run(cfg, "c4", "big")[0] == 0
    record(cfg, "c4", "big", 0.50, seconds=5, passed=1)    # faster, though costlier
    assert run(cfg, "c4", "big")[0] == 0


def test_balanced_metric_does_not_read_an_unknown_cost_as_a_loss(tmp_path):
    cfg = project(tmp_path, "c5", balance={"cost_per_case_usd": 1.0, "seconds_per_case": 60})
    record(cfg, "c5", "cheap", 0.10, seconds=10)
    assert run(cfg, "c5", "big")[0] == 0   # never recorded: nothing proves it is no cheaper


def test_an_arm_that_cannot_spend_money_is_never_refused(tmp_path):
    cfg = project(tmp_path, "c6")
    record(cfg, "c6", "cheap", 0.01)
    assert run(cfg, "c6", "free")[0] == 0


def test_a_stale_perfect_arm_is_no_ceiling(tmp_path):
    cfg = project(tmp_path, "c7")
    record(cfg, "c7", "cheap", 0.01)
    cases = cfg.evaluation / "c7" / "cases.json"
    cases.write_text(cases.read_text() + " ")
    assert run(cfg, "c7", "big")[0] == 0


def test_a_perfect_arm_on_another_sample_is_no_ceiling(tmp_path):
    cfg = project(tmp_path, "c8")
    record_result.record_result(dict(component="c8", impl="cheap", cases=1, passed=1, model_calls=1, cost_usd=0.01, seconds=1, model="m",
                               sample="sample:1"), cfg, date="2026-10-30")
    assert run(cfg, "c8", "big")[0] == 0
    assert run(cfg, "c8", "big", "--sample", "1")[0] == 2


def only_stale(monkeypatch, *arms):
    """Make exactly these ``component/impl`` arms stale and list them as the arms of the run (the toy has no registry)."""
    monkeypatch.setattr(rerun_stale, "stale_arms", lambda config: [tuple(a.split("/")) for a in arms])
    monkeypatch.setattr(stale_reasons, "stale_reason",
                        lambda config, comp, row, strict=True: "because of a test" if row and f"{comp}/{row['impl']}" in stale else "")
    stale = set(arms)


def test_stale_run_skips_a_capped_arm_and_says_so(tmp_path, monkeypatch):
    cfg = project(tmp_path, "c9")
    record(cfg, "c9", "cheap", 0.01)
    record(cfg, "c9", "big", 0.20, passed=1)
    cfg.paid_arms = ["c9/cheap", "c9/big"]
    only_stale(monkeypatch, "c9/big")
    lines = []
    rerun_stale.rerun_stale(cfg, lines.append, include_paid=True, run_all=True)
    assert any("c9/big" in line and "SKIPPED, not worth running" in line and "cheap already passed" in line for line in lines)
    assert not any("c9/big: run" in line for line in lines)


def with_evidence(cfg, name, benchmark=True, aliases=None):
    (cfg.root / "esoi").mkdir(exist_ok=True)
    (cfg.root / "esoi" / "evidence.csv").write_text(EVIDENCE)
    if benchmark:
        (cfg.evaluation / name / "benchmark.txt").write_text("# the public benchmark these cases reproduce\npublic bench\n")
    cfg.evidence = {"aliases": aliases or {}}
    cfg.structure_dir = "esoi"


def test_public_first_refuses_an_arm_with_an_independent_public_row_and_prints_it(tmp_path):
    cfg = project(tmp_path, "p1")
    with_evidence(cfg, "p1", aliases={"big-model": "big"})
    code, lines = run(cfg, "p1", "big")
    assert code == 2 and any(line.startswith("public result: big-model pass_rate = 0.9 fraction on public bench") for line in lines)
    assert "--differs" in lines[-1] and "--force" in lines[-1]


def test_differs_and_force_run_it_and_are_recorded(tmp_path):
    cfg = project(tmp_path, "p2")
    with_evidence(cfg, "p2", aliases={"big-model": "big"})
    assert run(cfg, "p2", "big", "--record", "--differs", "harness: our retrieval tool set")[0] == 0
    assert "differs from public: harness: our retrieval tool set" in last_details(cfg)
    assert run(cfg, "p2", "big", "--record", "--force", "re-checking the source")[0] == 0
    assert "forced past public result: re-checking the source" in last_details(cfg)
    assert run(cfg, "p2", "big", "--differs", "because I want to")[0] == 2   # must name what differs


def test_public_first_ignores_vendor_rows_other_candidates_other_benchmarks_and_undeclared_components(tmp_path):
    cfg = project(tmp_path, "p3")
    with_evidence(cfg, "p3", aliases={"big-model": "big", "small-model": "cheap"})
    assert run(cfg, "p3", "cheap")[0] == 0   # only a vendor-side row: not independent
    assert run(cfg, "p3", "free")[0] == 0    # no row for that candidate
    (cfg.evaluation / "p3" / "benchmark.txt").write_text("another-bench\n")
    assert run(cfg, "p3", "big")[0] == 0     # the row is for a different benchmark
    (cfg.evaluation / "p3" / "benchmark.txt").unlink()
    assert run(cfg, "p3", "big")[0] == 0     # the component declares none


def test_the_benchmark_may_be_declared_in_the_configuration(tmp_path):
    cfg = project(tmp_path, "p4")
    with_evidence(cfg, "p4", benchmark=False, aliases={"big-model": "big"})
    assert run_guards.declared_benchmark(cfg, "p4") == ""
    cfg.evidence["benchmarks"] = {"p4": "Public-Bench"}
    assert run(cfg, "p4", "big")[0] == 2


def test_the_stale_run_does_not_ask_again_about_a_public_result(tmp_path, monkeypatch):
    cfg = project(tmp_path, "p5")
    with_evidence(cfg, "p5", aliases={"big-model": "big"})
    record(cfg, "p5", "big", 0.2)
    cfg.paid_arms = ["p5/big"]
    only_stale(monkeypatch, "p5/big")
    lines = []
    rerun_stale.rerun_stale(cfg, lines.append, include=["p5/big"])
    assert any("p5/big: run and recorded" in line for line in lines)


def test_note_details_keeps_the_notes_whole_and_clips_the_headline():
    out = run_guards.note_details("x" * 400, ["forced past ceiling: why"])
    assert len(out) <= 300 and out.endswith("| forced past ceiling: why")
    assert run_guards.note_details("agg", []) == "agg"
