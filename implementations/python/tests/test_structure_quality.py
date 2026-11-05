"""Structure Quality: the balanced number, its dimensions on generic incident shapes, the Goodhart bound, stage two from git history, the advisory rules and the command. Offline; no model."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

import structure_fixture
from esoi.structure.structure_check.rules import structure_quality_rules
from esoi.structure.structure_quality import assess, balance, expert_review, interface, overlap, project, scope
from esoi.structure.structure_quality.balance import Budgets


def report(shape, stage=1):
    options = structure_fixture.options(shape)
    return assess.assess(str(structure_fixture.project(shape)), stage, Budgets(consumers=options.get("consumers", ())))


def test_weights_are_fixed_sum_to_one_and_no_dimension_can_win():
    assert abs(sum(balance.WEIGHTS.values()) - 1.0) < 1e-9
    assert max(balance.WEIGHTS.values()) <= 0.25
    assert set(balance.WEIGHTS) == {"scope", "size", "coupling", "reuse", "flow", "surface", "behavior"}


def test_a_clean_exemplar_is_sound_and_flags_nothing():
    found = report("clean_exemplar")
    assert found["verdict"] == "sound" and found["flagged"] == [] and found["score"] == 1.0
    assert found["dimensions"]["flow"]["score"] is None   # no records of flow to compare: not measured, never perfect


@pytest.mark.parametrize("shape,dimension", [
    ("flat_tree", "size"), ("long_solution_list", "size"), ("stripped_interfaces", "scope"), ("library_names_consumer", "coupling"),
    ("due_arithmetic_copied", "reuse"), ("import_cycle", "coupling"), ("no_contract", "behavior"), ("unused_exports", "surface")])
def test_each_incident_shape_flags_the_dimension_it_damages_and_scores_below_the_exemplar(shape, dimension):
    found = report(shape)
    assert dimension in found["flagged"] and found["dimensions"][dimension]["offenders"]
    assert found["score"] < report("clean_exemplar")["score"]


def test_the_offenders_name_the_worst_parts():
    assert "solution_" in report("long_solution_list")["dimensions"]["size"]["offenders"][0]
    assert "a library names its consumer" in " ".join(report("library_names_consumer")["dimensions"]["coupling"]["offenders"])
    assert "lacks run" in " ".join(report("stripped_interfaces")["dimensions"]["scope"]["offenders"])


def test_splitting_everything_into_tiny_files_scores_worse_than_the_balanced_real_structure():
    real, tiny = report("real_structure"), report("tiny_split")
    assert tiny["score"] < real["score"]
    # the size dimension alone prefers the tiny files: it is the single factor a balanced number must not collapse to (rule S45)
    assert tiny["dimensions"]["size"]["score"] > real["dimensions"]["size"]["score"]
    assert tiny["dimensions"]["coupling"]["score"] < real["dimensions"]["coupling"]["score"]
    assert tiny["dimensions"]["reuse"]["score"] < real["dimensions"]["reuse"]["score"]


def test_the_size_only_arm_is_fooled_and_the_balanced_arm_is_not():
    size_only = interface.FileSizeOnly().assess(str(structure_fixture.project("tiny_split")))
    real_size_only = interface.FileSizeOnly().assess(str(structure_fixture.project("real_structure")))
    assert size_only["score"] > real_size_only["score"]
    balanced_tiny = interface.BalancedStatic().assess(str(structure_fixture.project("tiny_split")))
    balanced_real = interface.BalancedStatic().assess(str(structure_fixture.project("real_structure")))
    assert balanced_tiny["score"] < balanced_real["score"]


def test_one_dimension_failing_outright_pulls_it_down_instead_of_being_averaged_away():
    assert balance.combine([1.0, 1.0, 0.0]) < 0.25
    assert balance.combine([None, None]) is None
    assert balance.combine([0.9, None]) == 0.9


def test_a_dimension_that_cannot_be_measured_is_left_out_of_the_weighted_mean_and_the_weight_is_stated():
    dims = [balance.Dimension(name, 1.0 if name != "surface" else None) for name in balance.WEIGHTS]
    out = balance.balanced(dims)
    assert out["score"] == 1.0 and abs(out["measured_weight"] - 0.95) < 1e-9
    assert balance.balanced([balance.Dimension(name, None) for name in balance.WEIGHTS])["verdict"] == "unmeasured"


def test_stage_two_sees_changes_that_happen_together_without_an_import_and_stage_one_does_not():
    assert "coupling" not in report("cochange_hidden", 1)["flagged"]
    hidden = report("cochange_hidden", 2)
    assert "coupling" in hidden["flagged"] and "changes together without an import" in " ".join(hidden["dimensions"]["coupling"]["offenders"])
    explained = report("cochange_explained", 2)
    assert explained["flagged"] == [] and explained["dimensions"]["coupling"]["parts"]["changes_explained_by_imports"] == 1.0


def test_a_project_with_no_history_is_not_read_at_stage_two(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    found = assess.assess(str(tmp_path), 2)
    assert found["dimensions"]["coupling"]["note"] == ""


def test_a_consumer_may_tighten_a_budget_and_never_loosen_it():
    tight = Budgets().tightened(function_lines=40)
    assert tight.function_lines == 40
    with pytest.raises(ValueError, match="not loosen"):
        Budgets().tightened(function_lines=500)
    assert report("clean_exemplar")["score"] >= assess.assess(str(structure_fixture.project("clean_exemplar")), 1, tight)["score"]


def test_units_follow_the_nearest_interface_or_records_folder():
    assert project.unit_of("pkg/a/b/mod.py", {"pkg/a"}) == "pkg/a"
    assert project.unit_of("pkg/a/b/mod.py", set()) == "pkg/a"
    assert project.unit_of("mod.py", set()) == "."


def test_the_overlap_measure_is_the_one_rules_s48_and_s49_read():
    from esoi.structure.structure_check.rules import intents
    assert intents.content is overlap.content and intents.OVERLAP == overlap.OVERLAP
    assert overlap.mean_overlap(["reads the records and reports balance", "reads the records and reports delivery"]) > overlap.mean_overlap(["reads the records", "zebra quilting"])


def test_the_expert_review_is_specified_not_run():
    reply = json.dumps({"scope": {"score": 0.5, "offenders": ["a/: two jobs"]}, "size": {"score": 0.9, "offenders": []}})
    parsed = expert_review.parse("Here: " + reply)
    assert parsed["dimensions"]["scope"]["offenders"] == ["a/: two jobs"] and parsed["dimensions"]["coupling"]["score"] is None
    assert "em dashes" in expert_review.prompt(project.load(structure_fixture.project("clean_exemplar")))
    with pytest.raises(ValueError, match="needs a provider"):
        interface.ExpertScopingReview().assess(str(structure_fixture.project("clean_exemplar")))
    with pytest.raises(ValueError, match="no JSON"):
        expert_review.parse("no object here")
    module = (ROOT / "evaluation/components/score_structure_quality/impls/expert_review.py").read_text()
    assert "PAID = True" in module


def context(root, enabled=("S54", "S55", "S56", "S57", "S58", "S59"), waived=()):
    return SimpleNamespace(root=root, config=SimpleNamespace(enabled=lambda rule: rule in enabled), waived=lambda rule, key: (rule, key) in waived, advisory=[])


def test_the_advisory_rules_inform_with_a_next_action_and_never_fail():
    ctx = context(structure_fixture.project("stripped_interfaces"))
    assert structure_quality_rules.run(ctx) == []
    assert ctx.advisory and all(line.startswith("S54 ") and "; next: " in line for line in ctx.advisory)


def test_a_rule_that_is_not_enabled_is_silent_and_a_waiver_excuses_one_finding():
    assert structure_quality_rules.findings(context(structure_fixture.project("stripped_interfaces"), enabled=())) == []
    full = structure_quality_rules.findings(context(structure_fixture.project("stripped_interfaces")))
    key = full[0].split(" ", 1)[1].split(":")[0].split(" ")[0]
    waived = structure_quality_rules.findings(context(structure_fixture.project("stripped_interfaces"), waived={("S54", key)}))
    assert len(waived) < len(full)


def test_the_findings_of_a_rule_are_capped_and_the_rest_counted():
    lines = structure_quality_rules.findings(context(structure_fixture.project("flat_tree"), enabled=("S55",)))
    assert len(lines) <= structure_quality_rules.SHOWN + 1


def test_every_rule_has_a_summary_and_a_next_action():
    assert set(structure_quality_rules.SUMMARIES) == set(structure_quality_rules.NEXT) == set(structure_quality_rules.DIMENSION_OF)


def test_the_command_prints_the_number_and_always_exits_zero(capsys):
    from esoi.structure.commands import run_structure_quality
    code = run_structure_quality(None, SimpleNamespace(path=str(structure_fixture.project("stripped_interfaces")), stage=1))
    out = capsys.readouterr().out
    assert code == 0 and out.startswith("structure quality 0.") and "scope" in out and "weak dimensions: scope" in out


def test_the_solution_is_declared_with_its_three_arms():
    assert isinstance(interface.BalancedStatic(), interface.StructureQualityAssessing)
    assert interface.StructureQualityAssessing.assess


def test_an_arm_takes_the_methods_of_its_base_class_into_account(tmp_path):
    (tmp_path / "unit").mkdir()
    (tmp_path / "unit" / "interface.py").write_text(
        "from typing import Protocol\n\n@solution('s', kind='x', entry='run')\nclass S(Protocol):\n    def run(self): ...\n\n"
        "class Base:\n    def run(self):\n        return 1\n\n@implementation('s', 'a')\nclass A(Base):\n    pass\n\n"
        "@implementation('s', 'b')\nclass B:\n    pass\n")
    rows = {name: missing for _, name, _, missing in scope.arms_on_interface(project.load(tmp_path))}
    assert rows["A"] == [] and rows["B"] == ["run"]
