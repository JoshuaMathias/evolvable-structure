import pytest

from esoi import balance

TABLE = {"weights": {"accuracy": 0.7, "cost": 0.15, "time": 0.15}, "cost_per_case_usd": 0.01, "seconds_per_case": 10}


def test_free_instant_arm_scores_its_accuracy_plus_full_marks():
    out = balance.balanced(8, 10, 0.0, 0.0, TABLE)
    assert out["balanced"] == pytest.approx(0.7 * 0.8 + 0.3, abs=1e-4)


def test_an_arm_that_spends_the_budget_gets_nothing_for_it():
    out = balance.balanced(10, 10, 0.1, 100.0, TABLE)
    assert out["balanced"] == pytest.approx(0.7, abs=1e-4)


def test_paid_stage_must_buy_its_price_in_accuracy():
    free = balance.balanced(8, 10, 0.0, 0.0, TABLE)["balanced"]
    paid = balance.balanced(9, 10, 0.1, 50.0, TABLE)["balanced"]
    assert free > paid


def test_unknown_cost_or_no_table_is_not_scored():
    assert balance.balanced(1, 1, "", 1.0, TABLE) == {}
    assert balance.balanced(1, 1, 0.0, 1.0, None) == {}


def test_bad_weights_or_budgets_raise():
    with pytest.raises(ValueError):
        balance.settings({"weights": {"accuracy": 0.9}, "cost_per_case_usd": 1, "seconds_per_case": 1})
    with pytest.raises(ValueError):
        balance.settings({"cost_per_case_usd": 0, "seconds_per_case": 1})
