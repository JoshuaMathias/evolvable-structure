"""Structure Quality: the balanced number, its dimensions on generic incident shapes, the Goodhart bound, stage two from git history, the advisory rules and the command. Offline; no model."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

import structure_fixture
from esoi.structure.structure_check.rules import structure_quality_rules
from esoi.structure.intent_registry import parsed_source
from esoi.structure.structure_quality import assess, balance, compare, expert_review, interface, overlap, project, report as report_module, scope
from esoi.structure.structure_quality.balance import Budgets


def report(shape, stage=1):
    options = structure_fixture.options(shape)
    return assess.assess(str(structure_fixture.project(shape)), stage, Budgets(consumers=options.get("consumers", ())))


def test_weights_are_fixed_sum_to_one_and_no_dimension_can_win():
    assert abs(sum(balance.WEIGHTS.values()) - 1.0) < 1e-9
    assert max(balance.WEIGHTS.values()) <= 0.25
    assert set(balance.WEIGHTS) == {"scope", "size", "coupling", "reuse", "flow", "surface", "behavior"}


def test_a_clean_exemplar_is_at_the_reference_and_flags_nothing():
    found = report("clean_exemplar")
    assert found["verdict"] == "at_reference" and found["flagged"] == [] and found["score"] == 1.0
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


def coupling_of(shape):
    return report(shape)["dimensions"]["coupling"]


def test_front_doors_and_declared_entries_are_clean_coupling():
    found = coupling_of("front_door_and_entries")
    assert found["offenders"] == [] and found["score"] == 1.0
    assert found["parts"]["cross_calls_through_entries_or_kernel"] == 1.0


def test_a_reach_into_another_units_internals_is_an_offender_and_names_the_entry_point():
    found = coupling_of("reach_into_internals")
    assert any("app/ledger/use.py imports app/planner/engine.py inside another unit; its entry point is app/planner/interface.py" == line for line in found["offenders"])
    assert found["parts"]["cross_calls_through_entries_or_kernel"] < 1.0


def test_moving_an_import_behind_a_front_door_re_export_does_not_hide_the_reach_in():
    hidden = coupling_of("reach_in_behind_the_front_door")
    assert any("app/planner/engine.py inside another unit" in line for line in hidden["offenders"])
    assert hidden["score"] < 1.0


def test_a_cycle_between_units_is_still_an_offender():
    assert any(line.startswith("cycle between units") for line in coupling_of("import_cycle")["offenders"])


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
    code = run_structure_quality(None, SimpleNamespace(path=str(structure_fixture.project("stripped_interfaces")), stage=1, compare=None, fast=False))
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


@pytest.mark.parametrize("shape,offender", [("stripped_members", "lacks describe"), ("mismatched_parameters", "parameter 1 is payload"),
                                            ("arms_of_no_solution", "names no solution the project declares")])
def test_an_arm_must_implement_every_member_with_matching_parameters_under_a_real_solution(shape, offender):
    found = report(shape)
    assert offender in " ".join(found["dimensions"]["scope"]["offenders"])
    assert found["dimensions"]["scope"]["parts"]["arms_on_interface"] <= scope.interface_score(0.5)   # stripped_members lacks one of two members; the others lack all
    assert found["score"] < report("clean_exemplar")["score"]


def test_an_arm_that_takes_extra_optional_parameters_or_async_must_still_match(tmp_path):
    (tmp_path / "unit").mkdir()
    (tmp_path / "unit" / "interface.py").write_text(
        "from typing import Protocol\n\n@solution('s', kind='x', entry='run')\nclass S(Protocol):\n    name: str\n    def run(self, data, limit=1): ...\n\n"
        "@implementation('s', 'ok')\nclass Ok:\n    def __init__(self):\n        self.name = 'a'\n    def run(self, data, limit=1, extra=2):\n        return data\n\n"
        "@implementation('s', 'required_extra')\nclass RequiredExtra:\n    name = 'b'\n    def run(self, data, limit, extra):\n        return data\n\n"
        "@implementation('s', 'no_name')\nclass NoName:\n    def run(self, data, limit=1):\n        return data\n\n"
        "@implementation('s', 'async_run')\nclass AsyncRun:\n    name = 'c'\n    async def run(self, data, limit=1):\n        return data\n")
    rows = {name: problems for _, name, _, problems in scope.arms_on_interface(project.load(tmp_path))}
    assert rows["Ok"] == [] and rows["NoName"] == ["name"]
    assert "required parameters" in rows["RequiredExtra"][0] and "async differs" in rows["AsyncRun"][0]


def test_compare_ranks_a_stripped_members_merge_below_the_structure_before_it_and_names_what_changed(tmp_path):
    result = compare.compare(str(structure_fixture.project("clean_exemplar")), str(structure_fixture.project("stripped_members")),
                             lambda folder, stage: assess.assess(str(folder), stage))
    assert not result["holds"] and result["after"]["score"] < result["before"]["score"]
    assert result["introduced"]["scope"] and not result["fixed"]["scope"]
    assert any(after == 0.0 for _, _, after in result["scope_by_solution"])
    text = "\n".join(compare.lines(result))
    assert "the number falls: keep the change only with the reason stated in the commit" in text and "offenders introduced" in text and "scope per solution" in text
    back = compare.compare(str(structure_fixture.project("stripped_members")), str(structure_fixture.project("clean_exemplar")),
                           lambda folder, stage: assess.assess(str(folder), stage))
    assert back["holds"] and back["fixed"]["scope"] and "keep the change: the number holds or rises" in compare.lines(back)[-1]


def test_compare_checks_out_git_references_into_a_temporary_worktree_and_removes_it(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@example.com", *args], check=True, capture_output=True)
    git("init", "-q")
    for shape in ("clean_exemplar", "stripped_members"):
        for rel, text in (getattr(structure_fixture, shape if shape != "clean_exemplar" else "exemplar")()).items():
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / rel).write_text(text, encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", shape)
    result = compare.compare("HEAD~1", "HEAD", lambda folder, stage: assess.assess(str(folder), stage), repo=str(tmp_path))
    assert not result["holds"] and result["before"]["score"] == 1.0
    listing = subprocess.run(["git", "-C", str(tmp_path), "worktree", "list"], capture_output=True, text=True).stdout
    assert len(listing.strip().splitlines()) == 1
    with pytest.raises(ValueError, match="neither a folder nor a git reference"):
        compare.compare("no-such-ref", "HEAD", lambda folder, stage: assess.assess(str(folder), stage), repo=str(tmp_path))


def test_the_second_side_of_a_compare_reads_only_the_files_that_changed(tmp_path):
    first = structure_fixture.project("clean_exemplar")
    assess.assess(str(first))
    parses = parsed_source.STATS["parses"]
    copy = tmp_path / "copy"
    subprocess.run(["cp", "-r", str(first), str(copy)], check=True)
    assess.assess(str(copy))
    assert parsed_source.STATS["parses"] == parses


def test_a_move_alone_does_not_count_as_a_fixed_or_an_introduced_offender():
    assert compare.same_offender("a/b/c.py: function f is 200 lines (budget 100)") == compare.same_offender("x/c.py: function f is 200 lines (budget 100)")


def test_a_project_with_no_arms_shows_behavior_as_not_measured_and_says_which_dimensions_were(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    found = assess.assess(str(tmp_path))
    assert "behavior" in found["not_measured"] and "size" in found["measured"] and found["dimensions"]["behavior"]["score"] is None
    text = "\n".join(report_module.lines(found))
    assert "not measured: " in text and "behavior" in text.split("not measured: ")[1].split("\n")[0] and "shared out" in text
    assert "measured: " in text


def test_the_fast_flag_leaves_the_flow_dimension_unmeasured():
    from esoi.structure.structure_check.rules import structure_quality_rules
    found = structure_quality_rules.assess_path(structure_fixture.project("clean_exemplar"), 1, flow=False)
    assert "flow" in found["not_measured"]


def test_the_reference_line_is_the_lowest_of_the_measured_kept_structures_and_no_floor_is_arbitrary():
    assert balance.REFERENCE_STATES and balance.REFERENCE_LINE <= min(balance.REFERENCE_STATES.values()) < balance.REFERENCE_LINE + 0.01
    assert not hasattr(balance, "SOUND_FLOOR")
    assert balance.balanced([balance.Dimension(name, balance.REFERENCE_LINE) for name in balance.WEIGHTS])["verdict"] == "at_reference"
    assert balance.balanced([balance.Dimension(name, balance.REFERENCE_LINE - 0.01) for name in balance.WEIGHTS])["verdict"] == "below_reference"


def test_the_command_compares_two_folders_and_always_exits_zero(capsys):
    from esoi.structure.commands import run_structure_quality
    args = SimpleNamespace(path=".", stage=1, compare=[str(structure_fixture.project("clean_exemplar")), str(structure_fixture.project("stripped_members"))], fast=True)
    assert run_structure_quality(None, args) == 0
    out = capsys.readouterr().out
    assert out.startswith("structure quality before 1.000 after 0.") and "the number falls" in out
    args.compare = ["no-such-ref", "HEAD"]
    assert run_structure_quality(None, args) == 2


def write(root, files):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


def test_an_arm_of_an_adopted_solution_is_checked_against_the_library_protocol_and_base_classes(tmp_path):
    write(tmp_path / "lib", {"core/interface.py": "from typing import Protocol\n\n@solution('shared', kind='x', entry='go')\nclass Shared(Protocol):\n    def go(self, item): ...\n    def stop(self): ...\n\n"
                                                  "class Base:\n    def stop(self):\n        return None\n"})
    write(tmp_path / "app", {"esoi.toml": "[adopts.lib]\nrepo = \"../lib\"\n",
                             "part/interface.py": "from lib.core.interface import Base\n\n@implementation('shared', 'mine')\nclass Mine(Base):\n    def go(self, item):\n        return item\n\n"
                                                  "@implementation('shared', 'half')\nclass Half:\n    def go(self, item):\n        return item\n"})
    rows = {name: problems for _, name, _, problems in scope.arms_on_interface(project.load(tmp_path / "app"))}
    assert rows["Mine"] == [] and rows["Half"] == ["stop"]
    (tmp_path / "app" / "esoi.toml").write_text("")
    alone = {name: problems for _, name, _, problems in scope.arms_on_interface(project.load(tmp_path / "app"))}
    assert alone["Mine"] == ["its solution id names no solution the project declares"]


def test_a_base_class_from_an_installed_package_supplies_the_members_an_arm_inherits(tmp_path):
    write(tmp_path, {"part/interface.py": "from json.encoder import JSONEncoder\nfrom typing import Protocol\n\n@solution('enc', kind='x', entry='default')\nclass Enc(Protocol):\n    def default(self, o): ...\n\n"
                                          "@implementation('enc', 'inherits')\nclass Inherits(JSONEncoder):\n    pass\n"})
    rows = {name: problems for _, name, _, problems in scope.arms_on_interface(project.load(tmp_path))}
    assert rows["Inherits"] == []


def test_the_reuse_score_is_a_graded_curve_that_never_saturates_at_a_real_share_of_copying():
    from esoi.structure.structure_quality import duplication
    shares = [0.0, 0.05, 0.158, 0.30, 0.5, 0.9, 1.0]
    scores = [duplication.reuse_score(v) for v in shares]
    assert scores[0] == 1.0 and scores[-1] == 0.0 and all(a > b for a, b in zip(scores, scores[1:]))
    assert duplication.reuse_score(0.158) > 0.5 > duplication.reuse_score(0.30) - 0.2   # a restructure that removes a tenth of the copies shows
    assert duplication.reuse_score(0.058) - duplication.reuse_score(0.158) > 0.1


def wrapper(n):
    body = "".join(f"    value_{i} = fetch(client, 'path', {i}, retries=3)\n    if value_{i} is None:\n        raise KeyError({i})\n" for i in range(8))
    return f"def call_{n}(client):\n{body}    return value_0\n"


def test_boilerplate_shared_by_a_family_of_files_is_reported_apart_from_accidental_clones(tmp_path):
    write(tmp_path, {f"wrappers/w{n}.py": wrapper(n) for n in range(5)})
    write(tmp_path, {"distinct/engine.py": structure_fixture.engine("distinct", list(range(12)))})
    write(tmp_path, {f"pair/p{n}.py": "def other_%d(rows):\n%s    return rows\n" % (n, "".join(f"    rows = [r + {i} for r in rows if r % {i + 2}]\n    rows.sort()\n    rows.reverse()\n" for i in range(8))) for n in range(2)})
    parts = assess.assess(str(tmp_path))["dimensions"]["reuse"]["parts"]
    assert parts["of_it_boilerplate_in_families"] > 0 and parts["of_it_accidental_clones"] > 0
    assert abs(parts["of_it_boilerplate_in_families"] + parts["of_it_accidental_clones"] - parts["share_of_code_copied"]) < 1e-3
    table = tmp_path / "wrappers"
    for n in range(1, 5):
        (table / f"w{n}.py").unlink()
    (table / "w0.py").write_text("TABLE = {'a': 1}\n")
    after = assess.assess(str(tmp_path))["dimensions"]["reuse"]
    assert after["parts"]["of_it_boilerplate_in_families"] == 0 and after["score"] > parts["reuse_score"]


def test_a_protocol_used_through_the_front_door_is_not_an_unused_export(tmp_path):
    write(tmp_path, {"lib/interface.py": "from typing import Protocol\n\n__all__ = ['Served', 'Typed', 'Idle']\n\n@solution('served', kind='x', entry='go')\nclass Served(Protocol):\n    def go(self): ...\n\n"
                                         "@solution('typed', kind='x', entry='go')\nclass Typed(Protocol):\n    def go(self): ...\n\n@solution('idle', kind='x', entry='go')\nclass Idle(Protocol):\n    def go(self): ...\n",
                     "lib/solutions.csv": "id,name\nserved,S\ntyped,T\nidle,I\n",
                     "app/main.py": "def front(run, handle: Typed):\n    return run('served')\n"})
    from esoi.structure.structure_quality import surface
    served = surface.served_names(project.load(tmp_path))
    assert served["lib"] == {"Served", "Typed"}
    found = assess.assess(str(tmp_path))["dimensions"]["surface"]
    assert "Idle" in " ".join(found["offenders"]) and "Served" not in " ".join(found["offenders"])


def test_a_shared_kernel_is_clean_and_a_widely_imported_module_that_reaches_into_a_solution_is_not():
    kernel = report("foundation_kernel")
    assert kernel["flagged"] == [] and kernel["score"] == 1.0
    assert "shared kernel: 1 modules" in kernel["dimensions"]["coupling"]["note"] and "config.py" in kernel["dimensions"]["coupling"]["note"]
    reaches_up = report("kernel_reaches_up")
    assert "coupling" in reaches_up["flagged"] and reaches_up["score"] < kernel["score"]
    assert any("app/common/config.py inside another unit" in line for line in reaches_up["dimensions"]["coupling"]["offenders"])


def test_moving_a_units_own_code_into_a_foundation_module_does_not_pass_as_a_kernel():
    found = report("kernel_dump")
    assert "coupling" in found["flagged"] and found["score"] < report("clean_exemplar")["score"]
    assert any("from the shared kernel module app/common/shared.py, and no other unit uses it" in line for line in found["dimensions"]["coupling"]["offenders"])


def test_a_kernel_may_be_tightened_and_never_loosened():
    assert Budgets().tightened(kernel_instability=0.1).kernel_instability == 0.1
    with pytest.raises(ValueError, match="not loosen"):
        Budgets().tightened(kernel_instability=0.5)


def test_arms_that_stub_a_fat_interface_do_not_implement_it():
    found = report("stub_arms")
    assert "scope" in found["flagged"] and found["score"] < report("clean_exemplar")["score"]
    assert "describe (a stub that implements nothing)" in " ".join(found["dimensions"]["scope"]["offenders"])


def test_protocol_members_no_caller_uses_widen_the_surface_even_when_the_arms_implement_them():
    found = report("unused_members")
    assert "surface" in found["flagged"] and found["dimensions"]["scope"]["score"] == 1.0
    assert found["dimensions"]["surface"]["parts"]["protocol_members_used"] < 1.0
    assert "declares 5 members, callers use 1" in " ".join(found["dimensions"]["surface"]["offenders"])


def test_a_star_re_export_is_followed_and_a_named_re_export_is_the_units_declared_interface():
    star = report("star_re_export")
    assert any("app/ledger/use.py imports app/planner/engine.py inside another unit" in line for line in star["dimensions"]["coupling"]["offenders"])
    named = report("explicit_re_exports")
    assert named["dimensions"]["coupling"]["score"] == 1.0 and "surface" in named["flagged"]
    assert "grow" in " ".join(named["dimensions"]["surface"]["offenders"])


def test_one_solution_split_into_a_chain_of_pass_through_solutions_flags_scope():
    found = report("split_into_many")
    assert "scope" in found["flagged"] and found["score"] < report("clean_exemplar")["score"]
    assert found["dimensions"]["scope"]["parts"]["arms_on_interface"] < 1.0 and "arms_doing_work_of_their_own" not in found["dimensions"]["scope"]["parts"]
    assert "passes every call on unchanged (run)" in " ".join(found["dimensions"]["scope"]["offenders"])


def test_a_call_into_the_arms_own_unit_is_its_own_work_not_a_pass_through(tmp_path):
    write(tmp_path, {"unit/solutions.csv": "id,name\ns,S\n", "unit/engine.py": "def own_runner():\n    return None\n",
                     "unit/interface.py": "from typing import Protocol\nfrom unit.engine import own_runner\n\n@solution('s', kind='x', entry='names')\nclass S(Protocol):\n    def names(self, sid): ...\n\n"
                                          "@implementation('s', 'own')\nclass Own:\n    def names(self, sid):\n        return own_runner().assembler.names(sid)\n\n"
                                          "@implementation('s', 'hollow')\nclass Hollow:\n    def __init__(self, other):\n        self.other = other\n    def names(self, sid):\n        return self.other.names(sid)\n"})
    hollow = {name for _, name, _, _ in scope.pass_through_arms(project.load(tmp_path))}
    assert hollow == {"Hollow"}


def test_size_is_graded_by_how_far_over_the_budget_a_part_goes():
    from esoi.structure.structure_quality import size
    assert size.within([5000, 100], 100) < size.within([200, 100], 100) < size.within([100, 100], 100) == 1.0
    assert size.within([], 100) is None
    assert "function_lines_within_budget" in report("real_structure")["dimensions"]["size"]["parts"]


def test_cyclomatic_complexity_counts_the_functions_own_branches():
    import ast
    from esoi.structure.structure_quality import complexity
    tree = ast.parse("def f(a, b):\n    if a and b:\n        return 1\n    for x in a:\n        pass\n    def inner():\n        if a:\n            return 2\n    return [y for y in b if y]\n")
    assert complexity.cyclomatic(tree.body[0]) == 5   # one, the if, its and, the for and the comprehension clause; the nested function's if is its own


def test_a_static_score_cannot_see_deleted_behavior():
    # the limit stated in the explanation: deleting the long routine raises the number, and only running the contract tests can tell
    assert report("deleted_hard_code")["score"] >= report("real_structure")["score"]


def test_a_layered_stack_of_protocols_in_one_folder_stays_clean_and_unrelated_jobs_in_one_folder_are_flagged():
    layered = report("layered_protocols")["dimensions"]["scope"]
    assert layered["offenders"] == [] and layered["parts"]["protocols_within_budget"] == 1.0
    unrelated = report("unrelated_protocols")["dimensions"]["scope"]
    assert unrelated["parts"]["protocols_within_budget"] < 1.0
    assert "app/stack: 3 Protocols (BackendDoing, CacheDoing, StoreDoing) signal more than one job" in unrelated["offenders"]


def test_protocols_the_same_arms_implement_and_layers_that_wrap_one_another_are_one_job_and_a_composition_root_joins_none():
    import ast
    from esoi.structure.structure_quality import protocol_groups
    layer = ast.parse("class Layer:\n    def __init__(self, below: 'BelowDoing'):\n        pass\n").body[0]
    root = ast.parse("class Root:\n    def __init__(self, a: Optional[ADoing], b: BDoing, c: CDoing):\n        pass\n").body[0]
    protocols = {"UpperDoing": ("a.py", "upper"), "BelowDoing": ("a.py", "below"), "ADoing": ("a.py", "a"), "BDoing": ("a.py", "b"), "CDoing": ("a.py", "c"),
                 "FaceOne": ("a.py", "twin"), "FaceTwo": ("a.py", "twin"), "LoneDoing": ("a.py", "lone")}
    arms = [("a.py", layer, "upper"), ("a.py", root, "root-job"), ("a.py", ast.parse("class Twin:\n    pass\n").body[0], "twin")]
    groups = protocol_groups.group_protocols(protocols, arms)
    assert sorted(sorted(g) for g in groups) == [["ADoing"], ["BDoing"], ["BelowDoing", "UpperDoing"], ["CDoing"], ["FaceOne", "FaceTwo"], ["LoneDoing"]]


def test_the_share_of_arms_on_their_interface_is_scored_by_severity_not_linearly():
    parts = [report(shape)["dimensions"]["scope"]["parts"]["arms_on_interface"] for shape in
             ("clean_exemplar", "one_solution_off_its_interface", "two_solutions_off_their_interfaces", "three_solutions_off_their_interfaces", "stripped_interfaces")]
    assert parts == sorted(parts, reverse=True) and len(set(parts)) == len(parts) and parts[0] == 1.0 and parts[-1] == 0.0
    assert parts[1] == scope.interface_score(0.75) < 0.75   # one of four solutions has two arms of eight off the interface
    assert scope.interface_score(0.9) == 0.729 and scope.interface_score(None) is None
    assert balance.WEIGHTS == {"scope": 0.20, "size": 0.15, "coupling": 0.20, "reuse": 0.15, "flow": 0.10, "surface": 0.05, "behavior": 0.15}


def test_an_arm_off_its_interface_is_as_severe_as_the_share_of_members_it_lacks(tmp_path):
    write(tmp_path, {"unit/solutions.csv": "id,name\ns,S\n",
                     "unit/interface.py": "from typing import Protocol\n\n@solution('s', kind='x', entry='a')\nclass S(Protocol):\n    def a(self): ...\n    def b(self): ...\n    def c(self): ...\n    def d(self): ...\n\n"
                                          "@implementation('s', 'most')\nclass Most:\n    def a(self):\n        return 1\n    def b(self):\n        return 2\n    def c(self):\n        return 3\n\n"
                                          "@implementation('s', 'none')\nclass Nothing:\n    pass\n"})
    rows = {row[1]: scope.arm_severity(row) for row in scope.arm_rows(project.load(tmp_path))}
    assert rows == {"Most": 0.25, "Nothing": 1.0}


def test_a_protocol_that_only_extends_another_counts_the_members_it_inherits_and_a_demoted_plain_protocol_beside_the_arm_is_named(tmp_path):
    write(tmp_path, {"unit/solutions.csv": "id,name\ns,S\n",
                     "unit/interface.py": "from typing import Protocol\n\nclass Base(Protocol):\n    def put(self, key): ...\n\n@solution('s', kind='x', entry='put')\nclass S(Base, Protocol):\n    pass\n\n"
                                          "class Cache(Protocol):\n    def load_listing(self): ...\n\n"
                                          "@implementation('s', 'cache')\nclass FileCache:\n    def load_listing(self):\n        return [1]\n"})
    rows = {name: problems for _, name, _, problems in scope.arms_on_interface(project.load(tmp_path))}
    assert rows["FileCache"][0] == "put"
    assert any("implements Cache beside it, a plain Protocol without the solution declaration" in line for line in rows["FileCache"])


def checkouts_left():
    import tempfile
    return sorted(p.name for p in Path(tempfile.gettempdir()).glob("esoi-sq-*"))


def test_a_compare_leaves_no_temporary_checkout_behind_also_when_scoring_raises_or_the_reference_is_bad(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "a.py").write_text("x = 1\n")
    git("add", "a.py")
    git("commit", "-q", "-m", "one")
    before = checkouts_left()
    with compare.checked_out("HEAD", tmp_path) as folder:
        assert (folder / "a.py").is_file()
    assert checkouts_left() == before

    def raising(folder, stage):
        raise RuntimeError("scoring failed")
    with pytest.raises(RuntimeError):
        compare.compare("HEAD", "HEAD", raising, str(tmp_path))
    assert checkouts_left() == before
    with pytest.raises(ValueError):
        compare.compare("no-such-ref", "HEAD", raising, str(tmp_path))
    assert checkouts_left() == before
    listed = subprocess.run(["git", "-C", str(tmp_path), "worktree", "list"], capture_output=True, text=True, check=True).stdout.strip().splitlines()
    assert len(listed) == 1
