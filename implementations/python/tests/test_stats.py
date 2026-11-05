"""Wilson interval, exact McNemar test, Holm correction and the paired helper, against values worked out by hand."""
import pytest

from esoi.optimization.leaderboard import stats


def test_wilson_interval_for_eight_of_ten():
    low, high = stats.wilson_interval(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-4) and high == pytest.approx(0.9433, abs=1e-4)


def test_wilson_stays_inside_zero_and_one_and_knows_nothing_without_cases():
    assert stats.wilson_interval(0, 5)[0] == pytest.approx(0.0, abs=1e-9) and stats.wilson_interval(5, 5)[1] == pytest.approx(1.0)
    assert stats.wilson_interval(0, 0) == (0.0, 1.0)
    assert stats.wilson_interval(8, 10, 0.90)[0] > stats.wilson_interval(8, 10)[0]   # a lower confidence is a narrower interval
    with pytest.raises(ValueError):
        stats.wilson_interval(11, 10)


def test_mcnemar_exact_for_ten_against_two():
    assert stats.mcnemar_exact(10, 2) == pytest.approx(2 * (1 + 12 + 66) / 4096)   # 0.0386
    assert stats.mcnemar_exact(2, 10) == stats.mcnemar_exact(10, 2)


def test_mcnemar_edges():
    assert stats.mcnemar_exact(0, 0) == 1.0 and stats.mcnemar_exact(5, 5) == 1.0
    assert stats.mcnemar_exact(5, 0) == pytest.approx(2 / 32)
    assert stats.mcnemar_exact(400, 300) < 0.001   # large counts do not overflow


def test_holm_correction():
    assert stats.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert stats.holm([0.5]) == [0.5] and stats.holm([]) == []
    assert stats.holm([0.4, 0.6]) == pytest.approx([0.8, 0.8])
    assert max(stats.holm([0.9, 0.8])) <= 1.0


def rows(passes):
    return [{"case_id": f"c{i}", "ok": "1" if ok else "0"} for i, ok in enumerate(passes)]


def test_paired_counts_and_the_sentence():
    a = rows([True] * 20 + [True] * 10 + [False] * 0 + [False] * 3)
    b = rows([True] * 20 + [False] * 10 + [True] * 0 + [False] * 3)
    result = stats.paired_counts(a, b)
    assert (result.both, result.only_a, result.only_b, result.neither) == (20, 10, 0, 3)
    assert result.p_value == pytest.approx(2 / 1024) and result.cases == 33
    text = stats.describe(result, "new", "old")
    assert "new passed 10 that old missed" in text and "larger than chance" in text and "Early" not in text


def test_a_tied_pairing_is_not_called_a_difference_and_a_small_gap_is_chance():
    result = stats.paired_counts(rows([True, True, False, True]), rows([True, False, True, True]))
    assert (result.only_a, result.only_b) == (1, 1) and "no difference" in stats.describe(result)
    three = stats.paired_counts(rows([True] * 3 + [False]), rows([False] * 4))
    assert "common by chance" in stats.describe(three)


def test_the_one_sided_sign_test_is_the_binomial_tail():
    assert stats.sign_test_greater(10, 2) == pytest.approx(79 / 4096)   # P(X >= 10 of 12), half the two-sided value
    assert stats.sign_test_greater(2, 10) > 0.98
    assert stats.sign_test_greater(5, 0) == pytest.approx(1 / 32) and stats.sign_test_greater(0, 5) == 1.0
    assert stats.sign_test_greater(0, 0) == 1.0
    assert stats.sign_test_greater(10, 2) * 2 == pytest.approx(stats.mcnemar_exact(10, 2))


def test_only_shared_cases_count_and_the_rest_are_reported():
    result = stats.paired_counts({"a": True, "b": True, "x": True}, {"a": False, "b": True, "y": False})
    assert result.cases == 2 and result.skipped == 2 and result.only_a == 1


def test_fishers_exact_test_on_two_pass_counts():
    # 3 of 3 against 0 of 3: only one table has the first arm holding all three passes, 1 of C(6,3) = 20
    assert stats.fisher_exact_greater(3, 3, 0, 3) == pytest.approx(1 / 20)
    assert stats.fisher_exact_greater(0, 3, 3, 3) == 1.0 and stats.fisher_exact_greater(5, 10, 5, 10) > 0.5
    assert stats.fisher_exact_greater(8, 10, 2, 10) == pytest.approx(0.0115, abs=1e-4)
    with pytest.raises(ValueError):
        stats.fisher_exact_greater(4, 3, 0, 3)
