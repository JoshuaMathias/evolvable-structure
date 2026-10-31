"""The evaluation components that ship with this repository: each live implementation passes all of its cases offline,
and each naive baseline in broken/ fails at least one of them, so the cases are proved to tell good from naive."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

from esoi import harness  # noqa: E402
from esoi.config import Config  # noqa: E402

CONFIG = Config(root=ROOT, package="esoi", evaluation_dir="evaluation/components")
COMPONENTS = harness.discover_components(CONFIG)
LIVE = {"check_the_structure": "live_checker", "own_every_file": "live_checker", "record_intent": "live_checker",
        "sync_the_template": "live_parser", "select_an_implementation": "live_selector",
        "measure_implementations": "live_harness", "rank_implementations": "live_leaderboard",
        "review_tracker": "live_tracker", "check_a_consumer": "live_consumer_check", "know_stale_results": "live_checker",
        "sync_the_skill": "live_skill", "index_projects": "live_index", "specify_from_code": "live_declarations",
        "readable_records": "live_readme", "promote_the_winner": "live_promote", "assemble_by_name": "live_assembler", "keep_metric_record": "live_record", "behave_by_esoi": "reference_good", "judge_esoi_behaviour": "regex_only", "spec_search": "gated"}
# Graded accuracy metrics: no pass-every-case bar, no broken/ baseline; the selected arm must beat the naive arm instead.
GRADED = {"spec_index": ("weighted_tfidf", "term_overlap")}


def score_all(component, spec):
    score = importlib.import_module(f"{component}.score")
    fn = harness.load_impl(spec, component)(harness.CallMeter())
    return [score.score_case(fn, case)["ok"] for case in harness.load_cases(component, CONFIG)]


def test_every_component_has_a_live_implementation_listed_here():
    assert set(COMPONENTS) == set(LIVE) | set(GRADED)


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
