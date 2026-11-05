"""Count the model calls, tokens and source reads of a run, and replay calls from a cassette."""
from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable, Dict, Optional, Tuple

from esoi.optimization.measurement_harness import access
from esoi.optimization.measurement_harness import cassette as cassettes
from esoi.optimization.measurement_harness.run_errors import OfflineViolation
from esoi.optimization.when_metrics_are_run.paid_gating import BudgetExceeded


def as_number(value: Any) -> float:
    """A counter's value as a number: a plain number as is, an object that defines ``__float__`` (or a ``value`` attribute)
    through that, anything else (None, missing, unreadable) as 0."""
    for read in (lambda v: v if isinstance(v, (int, float)) else None, lambda v: float(v), lambda v: float(v.value)):
        try:
            got = read(value)
            if got is not None:
                return got
        except Exception:   # noqa: BLE001
            continue
    return 0


def read_counters(provider: Any) -> Tuple[float, float, float]:
    """The provider's ``tokens_in``, ``tokens_out`` and ``cost_usd`` as numbers; a missing or non-numeric one reads as 0."""
    out = []
    for name in ("tokens_in", "tokens_out", "cost_usd"):
        try:
            out.append(as_number(getattr(provider, name, 0)))
        except Exception:   # noqa: BLE001
            out.append(0)
    return out[0], out[1], out[2]


class CallMeter:
    """Counts model calls. ``wrap(provider)`` instruments the named methods in place."""

    def __init__(self, max_calls: Optional[int] = None):
        self.calls = 0
        self.max_calls = max_calls
        self.tokens_in = self.tokens_out = 0
        self.cost_usd = 0.0   # what a provider reports per call (informational on a subscription login)
        self.attempted = 0    # model commands an offline run tried to start and the guard refused (see OfflineGuard)
        self.model: Optional[str] = None   # set by an implementation that pins a model, for the record
        self.cassette: Optional[cassettes.Cassette] = None   # opt-in record and replay of calls (esoi.optimization.measurement_harness.cassette); None: off
        self.offline = False   # set by a run that may not call a model: a cassette miss is then refused
        self.calls_replayed = 0   # calls answered from the cassette: not counted in ``calls``, never spent
        self.replayed_tokens_in = self.replayed_tokens_out = 0
        self.replayed_cost_usd = self.replayed_seconds = 0.0   # what the replayed calls originally cost, reported apart from the real spend
        self.reads = access.Reads()   # what the run read from source systems (``read``); priced and bounded by ``[balance.<c>.source_access]``
        self.access: Optional[Dict[str, Any]] = None   # the component's [balance.<c>] table, set by a run so a read is priced as it is made

    def read(self, records: int = 0, bytes: int = 0, calls: int = 1, scope: str = "", full_scan: bool = False) -> None:
        """Report a read of a source system (``esoi.optimization.measurement_harness.access``): its price, at the constants of ``source_access``, joins the run's cost, and a
        request that breaks a limit (a full scan, a read budget, a scope outside the allowed ones) fails."""
        self.reads.records += records
        self.reads.bytes += bytes
        self.reads.calls += calls
        self.reads.scopes.add(scope)
        self.reads.full_scan = self.reads.full_scan or full_scan
        self.cost_usd += access.price(access.Reads(records, bytes, calls), self.access)

    def record(self, n: int = 1) -> None:
        self.calls += n
        if self.max_calls is not None and self.calls > self.max_calls:
            raise BudgetExceeded(f"model-call budget {self.max_calls} exceeded")

    def model_of(self, kwargs: Dict[str, Any]) -> Optional[str]:
        given = kwargs.get("model")
        return given if isinstance(given, str) else self.model

    def replay_key(self, method: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Optional[str]:
        """The cassette key of this call, or None when there is no cassette or the arguments have no stable key (such a call is
        a plain miss: made, counted and not recorded)."""
        if self.cassette is None:
            return None
        try:
            return cassettes.request_key(self.model_of(kwargs), method, args, kwargs)
        except cassettes.Uncacheable:
            return None

    def replay(self, hit: Dict[str, Any]) -> Any:
        """Answer from a stored entry: counted as replayed, with its original usage reported apart from the real spend."""
        usage = hit.get("usage", {})
        self.calls_replayed += 1
        self.replayed_tokens_in += int(usage.get("tokens_in", 0) or 0)
        self.replayed_tokens_out += int(usage.get("tokens_out", 0) or 0)
        self.replayed_cost_usd += float(usage.get("cost_usd", 0) or 0)
        self.replayed_seconds += float(usage.get("seconds", 0) or 0)
        self.cassette.count("hits")
        return hit.get("response")

    def refuse_miss(self, key: Optional[str]) -> None:
        """A call the cassette cannot answer: refused in a ``--cassette-only`` run (``CassetteMiss``) and in an offline run
        (``OfflineViolation``, counted in ``attempted``)."""
        if self.cassette.only:
            self.cassette.count("misses")
            raise cassettes.CassetteMiss("--cassette-only: the cassette has no stored response for this call" +
                                         ("" if key else " (its arguments have no stable key)"))
        if self.offline:
            self.attempted += 1
            raise OfflineViolation("offline run refused a model call the cassette does not hold: the arm is not declared live "
                                   "(PAID = True, paid_arms, or --max-calls)")

    def wrap(self, provider: Any, methods: Tuple[str, ...] = ("plan", "answer")) -> Any:
        """Count calls to ``methods`` of ``provider``; token and cost counters, when the provider keeps them as
        ``tokens_in``, ``tokens_out`` and ``cost_usd`` attributes, are added up from their per-call change."""
        if getattr(provider, "meter_wrapped", False):
            return provider
        if inspect.isclass(provider):
            raise TypeError(f"CallMeter.wrap needs a provider instance, got the class {provider.__name__}: its methods would be "
                            "called unbound (self missing) and its counters are class descriptors, not numbers")
        for name in methods:
            original = getattr(provider, name, None)
            if original is None:
                continue

            def make(fn: Callable) -> Callable:
                @functools.wraps(fn)   # keeps the signature: callers may inspect it for optional kwargs
                def counted(*args, **kwargs):
                    key = self.replay_key(name, args, kwargs)
                    if key:
                        hit = self.cassette.get(key)
                        if hit is not None:
                            return self.replay(hit)
                    if self.cassette is not None:
                        self.refuse_miss(key)
                    self.record()
                    before, started = read_counters(provider), time.time()
                    result, failed = None, True
                    try:
                        result = fn(*args, **kwargs)
                        failed = False
                        return result
                    finally:
                        try:
                            after = read_counters(provider)
                            spent = (int(after[0] - before[0]), int(after[1] - before[1]), after[2] - before[2])
                            self.tokens_in += spent[0]
                            self.tokens_out += spent[1]
                            self.cost_usd += spent[2]
                            if key and not failed:   # a provider error is never recorded
                                self.cassette.count("misses")
                                self.cassette.put(key, name, self.model_of(kwargs), result,
                                                  {"tokens_in": spent[0], "tokens_out": spent[1], "cost_usd": round(spent[2], 6),
                                                   "seconds": round(time.time() - started, 3)})
                        except Exception:   # noqa: BLE001, metering must never change what the provider returns or raises
                            pass
                return counted
            setattr(provider, name, make(original))
        provider.meter_wrapped = True
        return provider
