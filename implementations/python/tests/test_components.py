"""The evaluation components that ship with this repository: each live implementation passes all of its cases offline,
and each naive baseline in broken/ fails at least one of them, so the cases are proved to tell good from naive."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

from esoi.optimization.measurement_harness import arm_loading
from esoi.optimization.measurement_harness import call_meter
from esoi.optimization.measurement_harness import case_loading
from esoi.optimization.measurement_harness import component_folder
from esoi.structure.intent_registry.config import Config

CONFIG = Config(root=ROOT, package="esoi", evaluation_dir="evaluation/components")
COMPONENTS = component_folder.discover_components(CONFIG)
LIVE = {"check_the_structure": "live_checker", "own_every_file": "live_checker", "record_intent": "live_checker",
        "sync_the_template": "live_parser", "select_an_implementation": "live_selector",
        "measure_implementations": "live_harness", "rank_implementations": "live_leaderboard",
        "review_tracker": "live_tracker", "check_a_consumer": "live_consumer_check", "know_stale_results": "live_checker",
        "sync_the_skill": "live_skill", "index_projects": "live_index", "specify_from_code": "live_declarations",
        "readable_records": "live_readme", "promote_the_winner": "live_promote", "assemble_by_name": "live_assembler", "keep_metric_record": "live_record", "behave_by_esoi": "reference_good", "judge_esoi_behaviour": "regex_only", "spec_search": "gated", "public_evidence": "graded"}
# Graded accuracy metrics: no pass-every-case bar, no broken/ baseline; the selected arm must beat the naive arm instead.
GRADED = {"spec_index": ("weighted_tfidf", "term_overlap")}
# Measured over repositories that are not part of this one (ESOI_GLANCE_ADOPTERS names them): here only the cases this repository can
# read count, and the arm the measurement selected must pass them while the page-less baseline and the record-tables-only arm do not.
LOCAL = {"readme_at_a_glance": ("at_a_glance", ("full_page", "links_page", "readme_at_a_glance.broken.no_readme:build"))}


# Laid out from the records of every repository this one can read (ESOI_GLANCE_ADOPTERS names the others): the arm the measurement selected
# passes more of the cases than the rival layout.
LAYOUTS = {"navigable_records": ("beside_code", "esoi_folder")}

# Judged on false-fresh (a hard fail) and false-stale: see tests/test_staleness.py for what each arm must and must not do.
STALENESS = {"staleness_precision": ("import_closure", "repo_wide", "component_paths")}


def score_all(component, spec):
    score = importlib.import_module(f"{component}.score")
    fn = arm_loading.load_impl(spec, component)(call_meter.CallMeter())
    return [score.score_case(fn, case)["ok"] for case in case_loading.load_cases(component, CONFIG)]


def test_every_component_has_a_live_implementation_listed_here():
    assert set(COMPONENTS) == set(LIVE) | set(GRADED) | set(LOCAL) | set(LAYOUTS) | set(STALENESS)


@pytest.mark.parametrize("component", sorted(LIVE))
def test_the_live_implementation_passes_every_case(component):
    results = score_all(component, LIVE[component])
    assert results and all(results), f"{component}: {results.count(False)} of {len(results)} cases fail"


@pytest.mark.parametrize("component", sorted(LIVE))
def test_a_deliberately_naive_baseline_fails_the_cases(component):
    broken = sorted(p.stem for p in (ROOT / "evaluation" / "components" / component / "broken").glob("*.py") if p.name != "__init__.py")
    assert broken, f"{component} has no broken/ baseline"
    for name in broken:
        assert not all(score_all(component, f"{component}.broken.{name}:build")), f"{component}/{name} passes every case"


@pytest.mark.parametrize("component", sorted(GRADED))
def test_a_graded_metric_ranks_its_selected_arm_above_the_naive_arm(component):
    selected, naive = GRADED[component]
    good, bad = score_all(component, selected), score_all(component, naive)
    assert sum(good) > sum(bad), f"{component}: {selected} {sum(good)} does not beat {naive} {sum(bad)} of {len(good)}"


def score_local(component, spec):
    score = importlib.import_module(f"{component}.score")
    fn = arm_loading.load_impl(spec, component)(call_meter.CallMeter())
    rows = [score.score_case(fn, case) for case in case_loading.load_cases(component, CONFIG)]
    return [r["ok"] for r in rows if r["got"] != "unavailable"]


@pytest.mark.parametrize("component", sorted(LOCAL))
def test_the_selected_arm_passes_the_readable_cases_and_the_rivals_do_not(component):
    selected, rivals = LOCAL[component]
    good = score_local(component, selected)
    assert good and all(good), f"{component}: {good}"
    for rival in rivals:
        assert not all(score_local(component, rival)), f"{component}/{rival} passes every readable case"


@pytest.mark.parametrize("component", sorted(LAYOUTS))
def test_the_selected_layout_passes_more_cases_than_the_rival_layout(component):
    selected, rival = LAYOUTS[component]
    good, bad = score_local(component, selected), score_local(component, rival)
    assert good and sum(good) > sum(bad), f"{component}: {selected} {sum(good)} does not beat {rival} {sum(bad)} of {len(good)}"
