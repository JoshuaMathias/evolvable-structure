"""The evidence table: one row per arm with an interval, cost, seconds, verdict and rule; written between markers."""
import pytest

from esoi import evidence_table as et
from esoi.config import Config
from esoi.registry import Registry

HEAD = "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,seconds,cases_sha,sample\n"
LOG = "component,impl,cases_sha,circumstances_sha,sample,case_id,heldout,ok,calls,tokens_in,tokens_out,seconds,circumstances\n"


def project(tmp_path, per_case=True):
    cfg = Config(root=tmp_path)
    folder = tmp_path / "evaluation" / "components"
    folder.mkdir(parents=True)
    (folder / "results.csv").write_text(
        HEAD + "2026-01-01,mini,a,40,20,0/0,0,0,0,1.0,80,x,\n2026-01-01,mini,b,40,32,0/0,0,0,0,1.2,100,x,\n")
    if per_case:
        lines = []
        for impl, ok in (("a", [1] * 20 + [0] * 20), ("b", [1] * 20 + [0] * 8 + [1] * 12)):
            lines += [f"mini,{impl},x,,,k{i},,{v},0,0,0,{1 + i % 3},\n" for i, v in enumerate(ok)]
        (folder / "per_case.csv").write_text(LOG + "".join(lines))
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "metric_command": "esoi run mini --impl a"}],
                        implementations=[{"implementation_id": "s:a", "solution_id": "s", "name": "a", "uses_solution_ids": ""},
                                         {"implementation_id": "s:b", "solution_id": "s", "name": "b", "uses_solution_ids": ""}])
    return cfg, registry


def test_every_arm_gets_a_row_with_wilson_interval_cost_median_seconds_and_the_deciding_rule(tmp_path):
    cfg, registry = project(tmp_path)
    table = et.evidence_table(cfg, registry)
    a_row = next(line for line in table.splitlines() if "| a (selected) |" in line)
    b_row = next(line for line in table.splitlines() if "| b |" in line)
    assert "50.0% (35.2% to 64.8%), 20/40" in a_row and "$0.05" in a_row and "(median)" in a_row and "| selected |" in a_row
    assert "beats the selected arm: two-sided paired test, Holm-adjusted p = 0.000488, 12 of 40 cases disagree" in b_row and "none recorded" in b_row


def test_without_per_case_rows_the_table_still_renders_and_names_the_best_guess(tmp_path):
    cfg, registry = project(tmp_path, per_case=False)
    table = et.evidence_table(cfg, registry)
    assert "(mean)" in table and "best guess" in table and "20/40" in table


def test_an_empty_project_says_so(tmp_path):
    cfg = Config(root=tmp_path)
    assert et.evidence_table(cfg, Registry(solutions=[])) == "No evaluated solution has a recorded run yet."


def test_the_table_is_written_between_the_markers_and_nowhere_else(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"intro\n{et.BEGIN}\nold\n{et.END}\noutro\n")
    et.write_between(readme, et.BEGIN, et.END, "| new |")
    assert readme.read_text() == f"intro\n{et.BEGIN}\n| new |\n{et.END}\noutro\n"
    et.write_between(readme, et.BEGIN, et.END, "| again |")
    assert readme.read_text().count("| again |") == 1 and readme.read_text().startswith("intro") and readme.read_text().endswith("outro\n")
    bare = tmp_path / "bare.md"
    bare.write_text("no markers")
    with pytest.raises(ValueError):
        et.write_between(bare, et.BEGIN, et.END, "x")
    assert bare.read_text() == "no markers"
