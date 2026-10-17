"""Grading an AI agent's reply: the regex check, the judge prompt and verdict, the command provider, and the cases that use
them. The paid arms are never run here; a fake provider stands in for the model."""
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

from esoi import behaviour, harness, skill  # noqa: E402
from esoi.config import Config  # noqa: E402

CONFIG = Config(root=ROOT, package="esoi", evaluation_dir="evaluation/components")
CASES = harness.load_cases("behave_by_esoi", CONFIG)
CASE = {"principle": "P4", "must_have": "metric;still", "must_not": "never", "scenario": "s", "expected_behavior": "e",
        "failure_mode": "f"}


def test_a_reply_passes_when_every_must_have_matches_and_no_must_not_does():
    assert behaviour.regex_problems("The METRIC, and you can still help.", CASE) == []
    assert behaviour.regex_problems("The metric only.", CASE) == ["missing /still/"]
    assert behaviour.regex_problems("Never mind the metric, still.", CASE) == ["must not match /never/"]


def test_a_forbidden_pattern_fails_without_calling_the_judge():
    def judge(case, reply):
        raise AssertionError("the judge must not be called")
    row = behaviour.score_reply("never the metric, still", CASE, judge)
    assert row["ok"] is False and row["judged"] is False and row["note"].startswith("prefilter")


def test_the_judge_decides_when_the_regexes_do_not_forbid():
    row = behaviour.score_reply("nothing matches here", CASE, lambda case, reply: (True, "does the thing"))
    assert row["ok"] is True and row["judged"] is True and row["regex_ok"] is False
    assert "regex-only 0/1; judge passed what regex failed 1" in behaviour.aggregate([row])


def test_the_headline_counts_per_principle_in_numeric_order():
    rows = [dict(got="P10", ok=True), dict(got="P2", ok=False), dict(got="P2", ok=True), dict(got="P0", ok=True)]
    assert behaviour.aggregate(rows) == "P0 1/1, P2 1/2, P10 1/1"


@pytest.mark.parametrize("text,expected", [
    ('{"verdict": "pass", "reason": "ok"}', True),
    ('Sure. {"verdict": "FAIL", "reason": "adds a framework"}', False),
    ("pass", False),
    ('{"verdict": "maybe"}', False),
    (None, False),
])
def test_an_unparseable_verdict_is_a_fail_never_a_pass(text, expected):
    assert behaviour.parse_verdict(text)[0] is expected


def test_the_judge_prompt_carries_the_rubric_and_never_the_regexes_or_references():
    case = dict(CASE, good_reference="GOODREF", bad_reference="BADREF")
    prompt = behaviour.judge_prompt(case, "the reply")
    assert "EXPECTED BEHAVIOR:\ne" in prompt and "FAILURE MODE" in prompt and "the reply" in prompt
    assert "GOODREF" not in prompt and "BADREF" not in prompt and "metric;still" not in prompt


def test_build_judge_makes_one_provider_call_per_reply():
    class Fake:
        calls = []

        def answer(self, messages, model=None, system=None):
            Fake.calls.append((model, system))
            return '{"verdict": "pass", "reason": "fine"}'
    assert behaviour.build_judge(Fake(), "m")(CASE, "reply") == (True, "fine")
    assert Fake.calls == [("m", behaviour.JUDGE_SYSTEM)]


def test_the_command_provider_pipes_the_prompt_and_counts_an_estimate():
    provider = behaviour.CommandProvider("cat")
    out = provider.answer([{"role": "user", "content": "hello"}], system="rules")
    assert out == "rules\n\n---\n\nhello" and provider.tokens_in > 0 and provider.tokens_out > 0


def test_the_command_provider_refuses_an_empty_command_and_reports_a_failing_one():
    with pytest.raises(ValueError):
        behaviour.CommandProvider(" ")
    with pytest.raises(RuntimeError):
        behaviour.CommandProvider("false").answer([{"role": "user", "content": "x"}])


def test_the_bundled_skill_has_a_description_for_the_on_request_arm():
    text = (skill.BUNDLED / "evolvable-structure" / skill.SKILL_FILE).read_text(encoding="utf-8")
    assert "evolvable" in behaviour.skill_description(text).lower() or behaviour.skill_description(text)


def test_every_recorded_good_reply_passes_and_every_bad_reply_fails():
    wrong = [c["id"] for c in CASES if behaviour.regex_problems(c["good_reference"], c)
             or not behaviour.regex_problems(c["bad_reference"], c)]
    assert wrong == []


def test_the_cases_cover_every_principle_and_the_nuance_rules():
    assert {c["principle"].split(";")[0] for c in CASES} == {f"P{n}" for n in range(14)}
    assert len({c["id"] for c in CASES}) == len(CASES)
    kinds = {c["kind"] for c in CASES}
    assert {"build", "restraint", "nuance"} <= kinds
    text = " ".join(c["scenario"] + " " + c["expected_behavior"] for c in CASES).lower()
    for needle in ("not implementations", "pay for itself", "not a problem", "qualifier"):
        assert needle in text, needle


def test_the_keyword_stuffing_baseline_fails_every_restraint_case():
    import importlib
    build = importlib.import_module("behave_by_esoi.broken.keyword_stuffing").build
    reply = build(harness.CallMeter())({})
    passed = [c["id"] for c in CASES if c["kind"] == "restraint" and not behaviour.regex_problems(reply, c)]
    assert passed == []


def test_no_case_names_an_adopter():
    import re
    adopters = ["q" + "ar", "qu" + "est", "spirit" + "ual"]   # spelled in pieces so this file does not name them itself
    names = re.compile(r"\b(?:" + "|".join(adopters) + r")\b", re.I)
    with (ROOT / "evaluation" / "components" / "behave_by_esoi" / "cases.csv").open(encoding="utf-8") as fh:
        assert not names.search(fh.read())


def test_the_judge_cases_follow_the_behaviour_cases():
    from judge_esoi_behaviour import score
    path = ROOT / "evaluation" / "components" / "judge_esoi_behaviour" / "cases.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        on_disk = list(csv.DictReader(fh))
    human = {r["id"]: r["human_verdict"] for r in on_disk}
    assert on_disk == score.rows_for(score.behavior_cases().values(), human), "run judge_esoi_behaviour.score.write_cases()"


def test_a_human_verdict_overrides_the_authors_label():
    from judge_esoi_behaviour import score
    assert score.label({"expected": "pass", "human_verdict": ""}) == "pass"
    assert score.label({"expected": "pass", "human_verdict": "Fail"}) == "fail"


@pytest.mark.parametrize("component,impl,paid", [
    ("behave_by_esoi", "standing_instructions", True), ("behave_by_esoi", "skill_on_request", True),
    ("behave_by_esoi", "no_skill", True), ("behave_by_esoi", "reference_good", False),
    ("behave_by_esoi", "reference_bad", False), ("judge_esoi_behaviour", "model_judge", True),
    ("judge_esoi_behaviour", "regex_only", False)])
def test_exactly_the_arms_that_call_a_model_declare_themselves_paid(component, impl, paid):
    assert harness.declares_paid(ROOT / "evaluation" / "components" / component / "impls" / f"{impl}.py") is paid
    assert bool(harness.paid_reason(CONFIG, component, impl, None)) is paid


def test_a_paid_arm_without_a_model_command_stops_before_any_call(monkeypatch):
    import importlib
    monkeypatch.delenv("ESOI_MODEL_COMMAND", raising=False)
    build = importlib.import_module("behave_by_esoi.impls.standing_instructions").build
    with pytest.raises(ValueError, match="ESOI_MODEL_COMMAND"):
        build(harness.CallMeter())
