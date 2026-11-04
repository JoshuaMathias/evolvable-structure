"""CallMeter keeps a provider's bound methods bound and reads its counters as numbers, whatever the counters are."""
import pytest

from esoi.harness import BudgetExceeded, CallMeter


class Counter:
    """Stands in for a scoped counter: an object that reads like a number only through ``float`` (no arithmetic)."""

    def __init__(self, value=0):
        self.value = value

    def __float__(self):
        return float(self.value)


class ScopedProvider:
    def __init__(self):
        self.tokens_in, self.tokens_out, self.cost_usd = Counter(), Counter(), Counter()

    def answer(self, messages, *, model, system=None):
        self.tokens_in = Counter(self.tokens_in.value + 10)
        self.tokens_out = Counter(self.tokens_out.value + 4)
        self.cost_usd = Counter(self.cost_usd.value + 0.5)
        return f"{model}:{len(messages)}:{system}"


class IntProvider:
    tokens_in = tokens_out = 0
    cost_usd = 0.0

    def answer(self, messages, *, model, system=None):
        self.tokens_in += 7
        self.tokens_out += 3
        self.cost_usd += 0.25
        return "ok"


class BareProvider:
    def answer(self, messages, *, model, system=None):
        return "bare"


def test_bound_method_with_scoped_counters_returns_and_counts():
    meter, provider = CallMeter(), ScopedProvider()
    meter.wrap(provider, ("answer",))
    assert provider.answer([{"role": "user", "content": "hi"}], model="m", system="s") == "m:1:s"
    assert meter.calls == 1
    assert (meter.tokens_in, meter.tokens_out, meter.cost_usd) == (10, 4, 0.5)
    provider.answer([{"role": "user", "content": "again"}], model="m")
    assert (meter.calls, meter.tokens_in, meter.tokens_out, meter.cost_usd) == (2, 20, 8, 1.0)


def test_plain_number_counters_are_added_up():
    meter, provider = CallMeter(), IntProvider()
    meter.wrap(provider, ("answer",))
    assert provider.answer([], model="m") == "ok"
    assert (meter.tokens_in, meter.tokens_out, meter.cost_usd) == (7, 3, 0.25)


def test_missing_counters_are_tolerated():
    meter, provider = CallMeter(), BareProvider()
    meter.wrap(provider, ("answer",))
    assert provider.answer([], model="m") == "bare"
    assert (meter.calls, meter.tokens_in, meter.tokens_out, meter.cost_usd) == (1, 0, 0, 0.0)


def test_unreadable_counters_never_change_the_result_or_the_error():
    class Opaque:
        def __float__(self):
            raise RuntimeError("no")

    class Odd:
        tokens_in = Opaque()
        tokens_out = object()
        cost_usd = None

        def answer(self, messages, *, model):
            if model == "boom":
                raise ValueError("provider failed")
            return "fine"

    meter, provider = CallMeter(), Odd()
    meter.wrap(provider, ("answer",))
    assert provider.answer([], model="m") == "fine"
    with pytest.raises(ValueError, match="provider failed"):
        provider.answer([], model="boom")
    assert meter.calls == 2


def test_budget_still_raises():
    meter, provider = CallMeter(max_calls=1), IntProvider()
    meter.wrap(provider, ("answer",))
    provider.answer([], model="m")
    with pytest.raises(BudgetExceeded):
        provider.answer([], model="m")


def test_wrapping_a_class_is_refused_clearly():
    with pytest.raises(TypeError, match="instance"):
        CallMeter().wrap(IntProvider, ("answer",))
