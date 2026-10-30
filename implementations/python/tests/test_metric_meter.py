"""The meters that read a metric's value, and the budget a reading keeps.

The meters give a slice's metric a number from the program's own side: a recorded row while it is current, or an offline arm run
now, and never an arm that could spend money. A throwaway repository written by ``esoi.scaffold.init`` stands in for a real
one. Offline: no model, no network.
"""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from esoi import scaffold
from esoi.metric_meter import (
    AFTER, BEFORE, OfflineArmMeter, Reading, RecordedRowMeter, kill_process_group, meters_from_names, read_value,
    run_bounded, score_from_output, scrubbed_environment)
from esoi.spec_slice import SpecSlice


@pytest.fixture
def greet_repo(tmp_path):
    """A scaffolded esoi repository whose one measured solution is greet-a-person (arm ``live``, recorded 2 of 2)."""
    root = tmp_path / "repo"
    scaffold.init(root, "demo_pkg", say=lambda *_: None)
    return root


def arm_meter(**kw):
    return OfflineArmMeter(os.environ, **kw)


def slice_of(root: Path) -> SpecSlice:
    return SpecSlice(root=str(root), solution_id="greet-a-person", metric_id="greeting-pass-rate",
                     metric_command="esoi run greet_a_person --impl live")


# -- the meters --------------------------------------------------------------------------------

def test_the_recorded_row_meter_reads_the_latest_row_while_it_is_current(greet_repo):
    assert RecordedRowMeter().measure(slice_of(greet_repo)) == 1.0   # 2 of 2 cases passed


def test_a_row_recorded_on_other_cases_is_no_reading(greet_repo):
    cases = greet_repo / "evaluation" / "components" / "greet_a_person" / "cases.json"
    cases.write_text(cases.read_text(encoding="utf-8").replace("Ada", "Grace"), encoding="utf-8")
    assert RecordedRowMeter().measure(slice_of(greet_repo)) is None


def test_a_metric_with_no_row_or_no_command_gives_none_without_raising(greet_repo):
    assert RecordedRowMeter().measure(SpecSlice(root=str(greet_repo), solution_id="s", metric_id="m")) is None
    assert RecordedRowMeter().measure(SpecSlice(root="/no/such/folder", solution_id="s", metric_id="m",
                                                metric_command="esoi run a --impl b")) is None


def test_the_offline_arm_meter_runs_an_arm_that_cannot_spend_and_reads_its_score(greet_repo):
    assert arm_meter().measure(slice_of(greet_repo)) == 1.0


def test_the_offline_arm_is_run_with_no_model_budget_and_no_credentials(greet_repo, monkeypatch):
    environ = {"PATH": "/usr/bin", "OPENAI_API_KEY": "sk-test-not-real", "SOME_SERVICE_TOKEN": "t", "LANG": "C"}
    seen = {}

    class FakeProc:
        returncode = 0

        def communicate(self, timeout=None):
            return "greet_a_person / live: 1/2 passed (dev 1/2, held-out 0/0)\n", None

    def fake_popen(argv, **kwargs):
        seen.update(argv=list(argv), **kwargs)
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    assert OfflineArmMeter(environ).measure(slice_of(greet_repo)) == 0.5
    assert seen["argv"][-4:] == ["--impl", "live", "--max-calls", "0"]
    assert "OPENAI_API_KEY" not in seen["env"] and "SOME_SERVICE_TOKEN" not in seen["env"] and seen["env"]["LANG"] == "C"
    assert seen["cwd"] == str(greet_repo) and seen["start_new_session"] is True


def refuses(greet_repo, monkeypatch):
    def popen_must_not_run(*args, **kwargs):
        raise AssertionError("an arm that may spend money was run")

    monkeypatch.setattr(subprocess, "Popen", popen_must_not_run)
    assert arm_meter().measure(slice_of(greet_repo)) is None


def test_the_offline_arm_meter_refuses_an_arm_listed_as_paid(greet_repo, monkeypatch):
    with open(greet_repo / "esoi.toml", "a", encoding="utf-8") as fh:
        fh.write('paid_arms = ["greet_a_person/live"]\n')
    refuses(greet_repo, monkeypatch)


def test_the_offline_arm_meter_refuses_an_arm_that_declares_itself_paid(greet_repo, monkeypatch):
    impl = greet_repo / "evaluation" / "components" / "greet_a_person" / "impls" / "live.py"
    impl.write_text("PAID = True\n" + impl.read_text(encoding="utf-8"), encoding="utf-8")
    refuses(greet_repo, monkeypatch)


def test_the_offline_arm_meter_refuses_an_arm_whose_last_run_called_a_model(greet_repo, monkeypatch):
    results = greet_repo / "evaluation" / "components" / "results.csv"
    lines = results.read_text(encoding="utf-8").splitlines()
    fields = lines[1].split(",")
    fields[7], fields[14] = "5", "some-model"   # model_calls, model
    results.write_text("\n".join([lines[0], ",".join(fields), *lines[2:]]) + "\n", encoding="utf-8")
    refuses(greet_repo, monkeypatch)


def test_the_offline_arm_meter_refuses_an_arm_with_no_recorded_run(greet_repo, monkeypatch):
    (greet_repo / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,dev,heldout,model_calls,tokens_in,tokens_out,cost_usd,seconds,git_sha,cases_sha,model,details\n",
        encoding="utf-8")
    refuses(greet_repo, monkeypatch)


def test_a_slow_arm_is_stopped_at_the_time_limit(greet_repo):
    impl = greet_repo / "evaluation" / "components" / "greet_a_person" / "impls" / "live.py"
    impl.write_text("import time\ntime.sleep(60)\n" + impl.read_text(encoding="utf-8"), encoding="utf-8")
    started = time.monotonic()
    assert arm_meter(timeout_seconds=1.5).measure(slice_of(greet_repo)) is None
    assert time.monotonic() - started < 15


def test_the_score_is_what_the_leaderboard_ranks_by():
    assert score_from_output("x: 3/4 passed (dev ...)\nbalanced score 0.8123 = accuracy 0.75") == 0.8123
    assert score_from_output("greet / live: 3/4 passed (dev 3/4, held-out 0/0)") == 0.75
    assert score_from_output("") is None and score_from_output("usage: esoi run ...") is None


def test_the_first_meter_with_a_number_wins_and_unknown_names_are_left_out():
    class Fixed:
        def __init__(self, name, value):
            self.name, self.value = name, value

        def measure(self, spec_slice, working_dir=None):
            return self.value

    found = SpecSlice(root="/x", solution_id="s")
    assert read_value([Fixed("a", None), Fixed("b", 0.4), Fixed("c", 0.9)], found) == Reading(0.4, "b")
    assert read_value([Fixed("a", None)], found) == Reading()
    assert [m.name for m in meters_from_names("offline_arm, nonsense ,recorded_row", os.environ)] == ["offline_arm", "recorded_row"]


def test_after_the_work_the_arm_reads_what_a_current_looking_row_cannot_see(greet_repo):
    """A change the row's staleness check does not see (here a non-git folder, in the repository a prose file the
    configuration leaves out of the measured code) leaves the row looking current: only a run of the arm sees it."""
    (greet_repo / "demo_pkg" / "greet.py").write_text(
        (greet_repo / "demo_pkg" / "greet.py").read_text(encoding="utf-8").replace('f"Hello, {name}!"', 'f"Hi {name}"'),
        encoding="utf-8")
    both = [RecordedRowMeter(), arm_meter()]
    assert RecordedRowMeter().measure(slice_of(greet_repo)) == 1.0   # the premise: the row still reads as current
    assert read_value(both, slice_of(greet_repo), when=BEFORE) == Reading(1.0, "recorded_row")
    assert read_value(both, slice_of(greet_repo), when=AFTER) == Reading(0.5, "offline_arm")


def test_each_meter_declares_the_moments_it_can_answer():
    assert RecordedRowMeter.serves == (BEFORE,) and OfflineArmMeter.serves == (BEFORE, AFTER)


def test_a_reading_after_the_work_asks_only_the_meters_that_serve_it_and_a_missing_one_is_not_a_failure():
    class Row(Stub):
        serves = (BEFORE,)

    found = SpecSlice(root="/x", solution_id="s")
    row, arm = Row("row", 1.0), Stub("arm", 0.4, cheap=False)
    told = []
    assert read_value([row, arm], found, when=AFTER, announce=lambda: told.append(1)) == Reading(0.4, "arm")
    assert row.calls == 0 and told == [1]   # the row was never asked, and the wait is announced for the meter that runs
    assert read_value([row, arm], found, when=BEFORE).value == 1.0 and arm.calls == 1
    alone = Row("row", 1.0)
    assert read_value([alone], found, when=AFTER) == Reading() and alone.calls == 0   # no note: nothing ran, nothing failed


# -- a reading is bounded -------------------------------------------------------------------------

class Stub:
    """A meter that answers at once, or after ``seconds`` on the fake clock, or never (``stuck``)."""

    def __init__(self, name, value=None, *, cheap=True, advance=0.0, clock=None, stuck=None):
        self.name, self.value, self.cheap = name, value, cheap
        self.advance, self.clock, self.stuck = advance, clock, stuck
        self.calls = 0

    def measure(self, spec_slice, working_dir=None):
        self.calls += 1
        if self.clock is not None:
            self.clock["now"] += self.advance
        if self.stuck is not None:
            self.stuck.wait(30)
        return self.value


def test_the_whole_reading_has_one_budget_not_one_per_meter():
    clock = {"now": 0.0}
    first = Stub("first", None, cheap=False, advance=10.0, clock=clock)
    second = Stub("second", 0.9, cheap=False, clock=clock)
    told = []
    done = read_value([first, second], SpecSlice(root="/x", solution_id="s"), budget_seconds=8.0,
                      announce=lambda: told.append("measuring"), clock=lambda: clock["now"])
    assert done.value is None and second.calls == 0   # the budget was gone before the second meter could start
    assert "8s" in done.note and "second" in done.note
    assert told == ["measuring"]


def test_the_wait_is_announced_once_before_the_first_meter_that_takes_time_and_never_for_a_cheap_one():
    found = SpecSlice(root="/x", solution_id="s")
    told = []
    assert read_value([Stub("cheap", 0.4)], found, announce=lambda: told.append(1)).value == 0.4
    assert told == []
    both = [Stub("cheap", None), Stub("slow", None, cheap=False), Stub("slower", 0.7, cheap=False)]
    assert read_value(both, found, announce=lambda: told.append(1)).value == 0.7
    assert told == [1]   # once, before "slow" ran; the cheap one before it was silent


def test_a_meter_that_never_answers_is_left_behind_at_the_budget():
    stuck = threading.Event()
    started = time.monotonic()
    done = read_value([Stub("stuck", 0.5, cheap=False, stuck=stuck)], SpecSlice(root="/x", solution_id="s"),
                      budget_seconds=0.3)
    assert time.monotonic() - started < 2 and done.value is None
    assert done.note == "stuck did not finish within 0.3s"
    stuck.set()


def test_a_meter_that_raises_gives_no_value_and_the_next_one_is_tried():
    class Boom:
        name, cheap = "boom", True

        def measure(self, spec_slice, working_dir=None):
            raise RuntimeError("broken")

    done = read_value([Boom(), Stub("fine", 0.2)], SpecSlice(root="/x", solution_id="s"))
    assert done == Reading(0.2, "fine")


def test_run_bounded_reports_whether_the_call_finished():
    assert run_bounded(lambda: 7, 1.0) == (7, True)
    release = threading.Event()
    value, finished = run_bounded(lambda: release.wait(30), 0.1)
    assert value is None and finished is False
    release.set()


def test_a_slow_offline_arm_costs_the_budget_and_no_more(greet_repo):
    impl = greet_repo / "evaluation" / "components" / "greet_a_person" / "impls" / "live.py"
    impl.write_text("import time\ntime.sleep(60)\n" + impl.read_text(encoding="utf-8"), encoding="utf-8")
    announced = []
    started = time.monotonic()
    done = read_value([arm_meter()], slice_of(greet_repo), budget_seconds=1.0, announce=lambda: announced.append(1))
    assert time.monotonic() - started < 6
    assert done.value is None and done.note == "offline_arm did not finish within 1s" and announced == [1]


def test_an_offline_arm_made_for_one_reading_carries_its_own_limit_and_the_shared_one_is_untouched():
    shared = arm_meter()
    own = shared.within(2.5)
    assert own.timeout_seconds == 2.5 and shared.timeout_seconds is None and own is not shared
    assert shared.cheap is False and RecordedRowMeter.cheap is True
    assert own.environ == shared.environ


def test_the_environment_an_arm_sees_is_the_one_it_was_given_less_credentials_and_the_repositorys_own_scrub():
    class Config:
        hermetic = {"prefixes": ["APP_"], "names": ["DATABASE_URL"], "set": {"APP_MODE": "offline"}}

    seen = scrubbed_environment(Config(), {"PATH": "/bin", "APP_DEBUG": "1", "DATABASE_URL": "x", "MY_API_KEY": "k",
                                           "DB_PASSWORD": "p", "KEEP": "yes"})
    assert seen == {"PATH": "/bin", "KEEP": "yes", "APP_MODE": "offline"}
    assert scrubbed_environment(type("Bare", (), {"hermetic": None})(), {"A": "1"}) == {"A": "1"}


def test_a_process_group_is_killed_with_its_children():
    code = ("import subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "print(child.pid, flush=True)\ntime.sleep(60)\n")
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, start_new_session=True)
    child = int(proc.stdout.readline())
    kill_process_group(proc)
    proc.wait(timeout=10)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError("the child of the killed process survived")
