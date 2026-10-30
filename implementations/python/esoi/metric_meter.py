"""Meters: how a program reads the value of a metric itself, so a piece of work's before and after are not left to the worker's word.

A meter turns a ``SpecSlice`` (the solution a task serves and its authoritative metric) into one number, or ``None`` when it
cannot. Two meters ship, and ``meters_from_names`` builds them in the order a list names (``recorded_row`` then ``offline_arm``
by convention); the first number wins:

  ``recorded_row``   the latest row of the repository's results log for the metric's arm, read as ``esoi leaderboard`` reads
                     it. It is cheap, runs nothing, and answers only while the row is current: a row recorded before the
                     measured code changed says nothing about the code now, so a stale row gives ``None``. It answers the
                     reading BEFORE the work only (``serves``): the row's own staleness check sees the files the repository
                     lists as measured code, so a change it does not list (prose, say) leaves a row looking current that no
                     longer describes the tree, and a reading after the work must not rest on it.
  ``offline_arm``    runs the metric's declared command (``esoi run <component> --impl <arm>``) and reads the score. It does
                     so ONLY for an arm that cannot spend money (the metric run policy: offline arms are run on every change,
                     live arms only by decision): its latest row must exist, show no model call (or a simulated one), and the
                     arm must not be listed or declared as paid (``esoi.harness.paid_reason``). The run is also given a budget
                     of zero model calls, a scrubbed environment, its own process group and a time limit, so even a wrong
                     reading of the record cannot spend anything. Any failure, a refusal or a timeout gives ``None``.

A meter never raises and never calls a model. What it returns is what ``esoi leaderboard`` ranks by: the balanced score when
the component records one, else the share of cases passed.

A reading is taken at one of two moments, ``BEFORE`` the work or ``AFTER`` it, and a meter declares the moments it can answer
(``serves``; both when it says nothing). After the work the tree is no longer the one the reading before described, and the
caller does not decide that from its own records of what the worker touched (a shell command changes files unseen), so the
meters that read the tree as it is now answer, and a metric none of them can read (no offline arm) gets no reading after.

A reading is never a wait without a bound. ``read_value`` gives the whole reading one budget, tries the meters in order,
says so (``announce``) before a meter that takes time runs, runs every meter on its own thread, and gives up on one that has not
answered when the budget is spent: the reading is then ``None`` with a note that says why, and the work goes on without it.

No setting comes from the environment. The environment the offline arm starts from is the ``environ`` argument.
"""
from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Protocol, Sequence, Tuple

from .spec_slice import SpecSlice

log = logging.getLogger("esoi.metric_meter")

BALANCED_LINE = re.compile(r"balanced score\s+([0-9]*\.?[0-9]+)")
PASSED_LINE = re.compile(r":\s*(\d+)/(\d+) passed")
# A variable that looks like a credential never reaches an arm, whatever the repository's own scrub lists.
SECRETISH = re.compile(r"API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", re.IGNORECASE)
# Where a repository's own virtual environment keeps its esoi command, tried before the running interpreter's.
REPO_ESOI_COMMANDS = (".venv/bin/esoi", "venv/bin/esoi")
# How long a whole reading may take, and how long past it a meter's thread is waited for (enough for an arm stopped at its
# limit to be reaped and answer).
DEFAULT_BUDGET_SECONDS = 15.0
JOIN_GRACE_SECONDS = 1.0
# The two moments a metric is read: before the worker starts, and after the last attempt.
BEFORE, AFTER = "before", "after"
EVERY_MOMENT = (BEFORE, AFTER)


class Reading(NamedTuple):
    """One reading of a metric: ``value`` from the meter named ``meter``, or no value and a ``note`` saying why."""
    value: Optional[float] = None
    meter: str = ""
    note: str = ""


class MetricMeter(Protocol):
    """Reads one metric's current value.

    Three optional attributes: ``cheap`` (default True) says the reading takes no noticeable time, so nothing is announced
    before it; ``within(seconds)`` returns a meter of the same kind that stops at that limit, for one that can be stopped;
    ``serves`` (default ``EVERY_MOMENT``) names the moments, ``BEFORE`` and ``AFTER`` the work, it can answer."""
    name: str

    def measure(self, spec_slice: SpecSlice, working_dir: Optional[str] = None) -> Optional[float]:
        ...


def repository(spec_slice: SpecSlice) -> Tuple[Any, str, str]:
    """``(esoi config, component, arm)`` of the slice's metric command; the last two are empty when it names no arm."""
    from . import config as config_module
    from .registry import first_arm
    config = config_module.load(Path(spec_slice.root))
    component, arm = first_arm(config, spec_slice.metric_command)
    return config, component, arm


def latest_row(config: Any, component: str, arm: str) -> Optional[Dict[str, str]]:
    from . import leaderboard
    return leaderboard.latest_results(config.results_path).get(component, {}).get(arm)


class RecordedRowMeter:
    """The metric's value from the latest row of the results log, while that row is current."""
    name = "recorded_row"
    cheap = True
    serves = (BEFORE,)   # a row describes the tree it was recorded on, which only the reading before the work can rely on

    def measure(self, spec_slice: SpecSlice, working_dir: Optional[str] = None) -> Optional[float]:
        try:
            from . import harness, leaderboard
            config, component, arm = repository(spec_slice)
            row = latest_row(config, component, arm) if component else None
            if row is None or harness.stale_reason(config, component, row, strict=True):
                return None
            return float(leaderboard.pass_rate(row))
        except Exception:  # noqa: BLE001  a meter that cannot read says so with None
            log.debug("recorded row not read", exc_info=True)
            return None


class OfflineArmMeter:
    """The metric's value from running its offline arm now, in ``environ`` scrubbed of credentials and the repository's own ``[hermetic]`` names."""
    name = "offline_arm"
    cheap = False
    serves = EVERY_MOMENT   # it runs the arm on the tree as it is now

    def __init__(self, environ: Mapping[str, str], timeout_seconds: Optional[float] = None):
        self.environ = dict(environ)
        self.timeout_seconds = timeout_seconds
        self.timed_out = False   # set when the arm was stopped at its limit; read on a meter made for one reading (``within``)

    def within(self, seconds: float) -> "OfflineArmMeter":
        """A meter for one reading that stops the arm at ``seconds`` (the shared meter is left as it is)."""
        return OfflineArmMeter(self.environ, timeout_seconds=max(seconds, 0.001))

    def measure(self, spec_slice: SpecSlice, working_dir: Optional[str] = None) -> Optional[float]:
        try:
            from . import harness
            config, component, arm = repository(spec_slice)
            row = latest_row(config, component, arm) if component else None
            if row is None or harness.paid_reason(config, component, arm, row):
                return None   # no proof it spends nothing, or proof it may
            argv = (esoi_command(config.root) + ["run", component, "--impl", arm, "--max-calls", "0"]
                    + harness.sample_label_args(row))
            return self.run(argv, config)
        except Exception:  # noqa: BLE001
            log.debug("offline arm not measured", exc_info=True)
            return None

    def run(self, argv: Sequence[str], config: Any) -> Optional[float]:
        limit = self.timeout_seconds or DEFAULT_BUDGET_SECONDS
        proc = subprocess.Popen(list(argv), cwd=str(config.root), env=scrubbed_environment(config, self.environ), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            kill_process_group(proc)
            proc.communicate()
            self.timed_out = True
            log.info("offline arm %s ran longer than %.0fs; no value", argv[-1], limit)
            return None
        return score_from_output(out) if proc.returncode == 0 else None


def esoi_command(root: Path) -> List[str]:
    """The command that runs ``esoi`` for a repository: its own virtual environment's, else the running interpreter's."""
    own = next((str(root / rel) for rel in REPO_ESOI_COMMANDS if os.access(root / rel, os.X_OK)), None)
    return [own] if own else [sys.executable, "-m", "esoi"]


def kill_process_group(proc: "subprocess.Popen") -> None:
    """Kill the process and every child it started (it was launched as its own group leader); fall back to the process alone."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        return
    except (ProcessLookupError, PermissionError, OSError, AttributeError):
        pass
    try:
        proc.kill()
    except Exception:  # noqa: BLE001  best-effort cleanup, never raise from a timeout handler
        pass


def scrubbed_environment(config: Any, environ: Mapping[str, str]) -> Dict[str, str]:
    """``environ`` as an arm may see it: the repository's own ``[hermetic]`` scrub, and nothing that looks like a credential."""
    table = config.hermetic if isinstance(config.hermetic, dict) else {}
    prefixes, names = tuple(table.get("prefixes", ())), set(table.get("names", ()))
    env = {k: v for k, v in environ.items() if not (k.startswith(prefixes) or k in names or SECRETISH.search(k))}
    env.update({str(k): str(v) for k, v in dict(table.get("set", {})).items()})
    return env


def score_from_output(out: str) -> Optional[float]:
    """The score ``esoi run`` printed: the balanced score when it prints one, else cases passed over cases."""
    found = BALANCED_LINE.search(out or "")
    if found:
        return float(found.group(1))
    found = PASSED_LINE.search(out or "")
    return int(found.group(1)) / max(int(found.group(2)), 1) if found else None


METER_NAMES = ("recorded_row", "offline_arm")


def meters_from_names(names: str, environ: Mapping[str, str]) -> List[MetricMeter]:
    """The meters a comma-separated list names, in order; an unknown name is logged and left out. ``environ`` is what the offline arm starts from."""
    meters: List[MetricMeter] = []
    for name in (n.strip().lower() for n in (names or "").split(",") if n.strip()):
        if name == "recorded_row":
            meters.append(RecordedRowMeter())
        elif name == "offline_arm":
            meters.append(OfflineArmMeter(environ))
        else:
            log.warning("unknown metric meter %r (known: %s)", name, ", ".join(METER_NAMES))
    return meters


def run_bounded(call: Callable[[], Any], seconds: float) -> Tuple[Any, bool]:
    """``(result, finished)`` of ``call`` run on its own thread for at most ``seconds``; a call that raises gives ``None``.

    A call still running when the time is up is left to finish on its own (the thread is a daemon): the caller moves on."""
    box: Dict[str, Any] = {}

    def go() -> None:
        try:
            box["value"] = call()
        except Exception:  # noqa: BLE001  a meter that fails says so with no value
            log.debug("meter failed", exc_info=True)
            box["value"] = None

    worker = threading.Thread(target=go, name="metric-meter", daemon=True)
    worker.start()
    worker.join(max(seconds, 0.0))
    return box.get("value"), not worker.is_alive()


def read_value(meters: Sequence[MetricMeter], spec_slice: SpecSlice, working_dir: Optional[str] = None, *,
               when: str = BEFORE, budget_seconds: float = DEFAULT_BUDGET_SECONDS,
               announce: Optional[Callable[[], None]] = None, clock: Callable[[], float] = time.monotonic) -> Reading:
    """The first number a meter gives, within one budget, as a ``Reading`` taken ``when`` (``BEFORE`` or ``AFTER`` the work).

    Only the meters that serve that moment are asked; when none can, the reading is empty and carries no note (nothing ran,
    so there is no wait or failure to explain). ``budget_seconds`` bounds the whole reading, whatever the number of meters.
    ``announce`` is called once, just before the first meter that takes time (not ``cheap``) runs, so the person is told about a
    wait before it starts and never about one that does not happen. A meter that has not answered when the budget is spent is
    left behind; the reading is then empty with a note naming the meter and the budget."""
    budget = float(budget_seconds)
    deadline = clock() + budget
    announced, note = False, ""
    for meter in meters:
        if when not in getattr(meter, "serves", EVERY_MOMENT):
            continue
        left = deadline - clock()
        if left <= 0:
            return Reading(note=note or f"the {budget:g}s for the reading were used up before {meter.name} could run")
        if not getattr(meter, "cheap", True) and not announced:
            announced = True
            if announce is not None:
                announce()
        # A meter that can stop itself at the limit gets a moment past it to be reaped and answer; one that cannot is
        # left behind at the limit.
        stoppable = hasattr(meter, "within")
        bounded = meter.within(left) if stoppable else meter
        value, finished = run_bounded(lambda m=bounded: m.measure(spec_slice, working_dir),
                                      left + (JOIN_GRACE_SECONDS if stoppable else 0.0))
        if value is not None:
            return Reading(value, meter.name)
        if not finished or getattr(bounded, "timed_out", False):
            note = f"{meter.name} did not finish within {budget:g}s"
    return Reading(note=note)
