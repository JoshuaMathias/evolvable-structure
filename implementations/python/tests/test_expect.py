"""The declarative case checks."""
import pytest

from esoi import expect


def test_each_check_kind():
    out = {"text": "hello world", "n": 3.0, "items": ["a", "b"]}
    assert expect.check(out, {"eq": {"n": 3.0}, "has": {"items": ["a"]}, "contains": ["hello"], "not_contains": ["bye"],
                              "max_len": 20, "min_len": 5, "approx": {"n": [3.1, 0.2]}, "at_most": {"n": 3.0}}) == []
    problems = expect.check(out, {"eq": {"n": 4}, "has": {"items": ["z"]}, "contains": ["bye"], "not_contains": ["hello"],
                                  "max_len": 3, "min_len": 50, "approx": {"n": [9, 0.1]}})
    assert len(problems) == 7
    assert expect.check({"n": 5}, {"at_most": {"n": 3}}) == ["n: 5 is over the ceiling 3"]


def test_a_non_dict_output_is_treated_as_text():
    assert expect.check("plain", {"contains": ["pla"]}) == []


def test_score_kind_case_reports_exceptions_as_failures_except_a_budget():
    def boom(kind, args):
        raise ValueError("bad")

    result = expect.score_kind_case(boom, {"kind": "k", "args": {}, "expect": {}})
    assert result["ok"] is False and "ValueError" in result["note"]

    class BudgetExceeded(Exception):
        pass

    def over(kind, args):
        raise BudgetExceeded()

    with pytest.raises(BudgetExceeded):
        expect.score_kind_case(over, {"kind": "k", "args": {}, "expect": {}})


def test_aggregate_by_kind():
    rows = [{"got": "a", "ok": True}, {"got": "a", "ok": False}, {"got": "b", "ok": True}]
    assert expect.aggregate_by_kind(rows) == "a 1/2, b 1/1"
