"""esoi.entry: one line for any solution, by its declared kind; nothing here calls a model or the network."""
import typing
from pathlib import Path

import pytest

from esoi import implementation, solution
from esoi.assemble import Assembler
from esoi.entry import EntryError, Pending, call_entry, runner


@solution("notes", scope="entrytest", kind="store", entry="find", example="milk")
@typing.runtime_checkable
class Notes(typing.Protocol):
    def find(self, query: str) -> typing.List[str]: ...


@solution("summary", scope="entrytest", kind="event", entry="summarize", example="milk")
class Summarizing(typing.Protocol):
    def summarize(self, query: str) -> str: ...


@solution("note-check", scope="entrytest", kind="evaluate", entry="score", example="buy milk")
class NoteChecking(typing.Protocol):
    def score(self, text: str) -> dict: ...


@solution("needs-a-path", scope="entrytest", kind="store", entry="find", example="x")
class NeedsAPath(typing.Protocol):
    def find(self, query: str) -> typing.List[str]: ...


@solution("undeclared-kind", scope="entrytest")
class NoKind(typing.Protocol):
    def go(self, x: str) -> str: ...


class MemoryNotes:
    def __init__(self):
        self.items = ["buy milk", "call Ada"]

    def find(self, query):
        return [t for t in self.items if query in t]


class FirstLine:
    def __init__(self, notes: Notes):
        self.notes = notes

    def summarize(self, query):
        found = self.notes.find(query)
        return found[0] if found else ""


class Length:
    def score(self, text):
        return {"words": len(text.split()), "ok": len(text.split()) <= 10}


class OnDisk:
    def __init__(self, path: str):
        self.path = path

    def find(self, query):
        return []


@pytest.fixture()
def run(tmp_path: Path):
    parts = Assembler("entrytest", tmp_path)
    for sid, name, target in (("notes", "memory", MemoryNotes), ("summary", "first_line", FirstLine), ("note-check", "length", Length),
                              ("needs-a-path", "on_disk", OnDisk), ("undeclared-kind", "plain", type("Plain", (), {"go": lambda s, x: x}))):
        parts.register(sid, name, target)
    arms = {"notes": "memory", "summary": "first_line", "note-check": "length", "needs-a-path": "on_disk", "undeclared-kind": "plain"}
    one = runner(parts)
    return lambda target, input=None, **kw: one(target, input, arms=arms, environ={}, **kw)


def test_a_store_returns_its_handle_without_input_and_its_query_with_one(run):
    assert isinstance(run("notes"), MemoryNotes)
    assert run("notes", "milk") == ["buy milk"]


def test_an_event_returns_its_output_and_its_needs_are_built_by_name(run):
    assert run("summary", "Ada") == "call Ada"


def test_an_evaluation_scores_the_artifact_and_asks_for_one(run):
    assert run("note-check", "buy milk") == {"words": 2, "ok": True}
    with pytest.raises(EntryError, match="evaluates an artifact"):
        run("note-check")


def test_a_seat_that_needs_an_option_is_pending_with_the_line_to_set(run):
    with pytest.raises(Pending, match=r"needs-a-path \(on_disk\).*options=.*'path'"):
        run("needs-a-path", "x")


def test_a_solution_without_a_kind_names_rule_s37(run):
    with pytest.raises(EntryError, match="S37"):
        run("undeclared-kind", "x")


def test_a_mapping_is_passed_as_keywords_only_when_its_keys_are_the_entrys_parameters():
    def act(goal, brief=""):
        return (goal, brief)
    assert call_entry(act, {"goal": "g", "brief": "b"}) == ("g", "b")
    assert call_entry(act, {"other": 1}) == ({"other": 1}, "")


# Strict one-line outcomes: only ok, pending-key and pending-install answer; each pending carries structured reasons.

from esoi import requirements as req  # noqa: E402
from esoi.entry import ANSWERING, Offline, classify  # noqa: E402


@solution("keyed", scope="entrytest", kind="event", entry="go", example="x")
class Keyed(typing.Protocol):
    def go(self, text: str) -> str: ...


@solution("installed", scope="entrytest", kind="event", entry="go", example="x")
class Installed(typing.Protocol):
    def go(self, text: str) -> str: ...


@solution("calls-a-program", scope="entrytest", kind="event", entry="go", example="x")
class CallsAProgram(typing.Protocol):
    def go(self, text: str) -> str: ...


class NeedsAKey:
    REQUIRES = (req.env("ENTRYTEST_KEY"),)

    def go(self, text):
        return text


class NeedsAPackage:
    REQUIRES = (req.python("no_such_module_for_entrytest", "no-such-distribution"),)

    def go(self, text):
        return text


STARTED = []


class RunsClaude:
    REQUIRES = (req.binary("claude"),)

    def __init__(self):
        STARTED.append("built")

    def go(self, text):
        raise AssertionError("must never run")


@pytest.fixture()
def strict(tmp_path: Path):
    parts = Assembler("entrytest", tmp_path)
    for sid, name, target in (("keyed", "k", NeedsAKey), ("installed", "i", NeedsAPackage), ("calls-a-program", "c", RunsClaude),
                              ("needs-a-path", "on_disk", OnDisk)):
        parts.register(sid, name, target)
    arms = {"keyed": "k", "installed": "i", "calls-a-program": "c", "needs-a-path": "on_disk"}
    one = runner(parts)
    return lambda target, **kw: one(target, "x", arms=arms, environ={}, **kw)


def outcome_of(call):
    try:
        call()
    except Exception as error:
        return classify(error)
    return ("ok", "", [])


def test_a_missing_key_is_pending_key_with_a_structured_reason(strict):
    outcome, detail, reasons = outcome_of(lambda: strict("keyed"))
    assert outcome == "pending-key" and reasons[0].kind == "key" and reasons[0].seat == "keyed"
    assert "ENTRYTEST_KEY" in reasons[0].need


def test_a_missing_package_is_pending_install(strict):
    outcome, detail, reasons = outcome_of(lambda: strict("installed"))
    assert outcome == "pending-install" and reasons[0].kind == "install"


def test_a_program_is_looked_up_on_the_path_of_environ_so_none_is_pending_install_and_never_started(strict):
    STARTED.clear()
    outcome, detail, reasons = outcome_of(lambda: strict("calls-a-program"))
    assert outcome == "pending-install" and "claude" in reasons[0].need
    assert STARTED == []     # the arm was never even built


def test_a_seat_that_needs_an_option_is_needs_option_and_does_not_answer(strict):
    outcome, detail, reasons = outcome_of(lambda: strict("needs-a-path"))
    assert outcome == "needs-option" and reasons[0].kind == "option"
    assert outcome not in ANSWERING and {"ok", "pending-key", "pending-install"} == set(ANSWERING)


def test_an_unpredicted_network_or_program_call_is_a_live_attempt_and_a_broken_arm_a_fail():
    assert classify(Offline("x"))[0] == "live-attempt"
    wrapped = RuntimeError("the arm failed")
    wrapped.__cause__ = Offline("x")
    assert classify(wrapped)[0] == "live-attempt"
    assert classify(ValueError("broken"))[0] == "fail"
    assert classify(ImportError("no module"))[0] == "load-error"
    assert classify(EntryError("declares no interface", code="no-entry"))[0] == "no-entry"


def test_an_interface_class_gives_the_ready_handle_typed_as_that_protocol(tmp_path: Path):
    parts = Assembler("entrytest", tmp_path)
    parts.register("notes", "memory", MemoryNotes)
    one = runner(parts)
    handle = one(Notes, arms={"notes": "memory"}, environ={})
    assert isinstance(handle, MemoryNotes) and handle.find("milk") == ["buy milk"]
    assert one.assembler is parts and one.__name__ == "run"
    assert one("notes", "milk", arms={"notes": "memory"}, environ={}) == ["buy milk"]
    with pytest.raises(EntryError, match="not declared"):
        one(MemoryNotes, environ={})


def test_a_composite_that_waits_on_a_child_key_is_pending_key_by_its_leaves():
    from esoi.entry import Pending, Reason, pending_outcome, run_block
    composite = Reason("whole", "arm", "needs", "whole: needs part; see those lines", ("part",))
    key = Reason("part", "arm", "key", "set KEY")
    assert pending_outcome([composite, key]) == "pending-key"
    assert pending_outcome([composite, Reason("part", "a", "install", "pip install x"), key]) == "pending-install"
    assert pending_outcome([composite, Reason("part", "a", "option", "pass options"), key]) == "needs-option"
    assert pending_outcome([composite]) == "needs-option"                      # nothing under it settles it
    assert pending_outcome([composite, Reason("other", "a", "key", "set KEY")]) == "needs-option"
    assert classify(Pending("whole", [composite.need, key.need], [composite, key]))[0] == "pending-key"
    block = (">>> from esoi.entry import Pending, Reason\n>>> raise Pending('whole', ['w', 'k'], [Reason('whole', 'a', 'needs', 'w', ('part',)), "
             "Reason('part', 'a', 'key', 'k')])\n")
    found = run_block(block, guard=False)
    assert found["problems"] == [] and found["pending"]
    bare = ">>> from esoi.entry import Pending, Reason\n>>> raise Pending('whole', ['w'], [Reason('whole', 'a', 'needs', 'w', ('part',))])\n"
    assert run_block(bare, guard=False)["problems"]
