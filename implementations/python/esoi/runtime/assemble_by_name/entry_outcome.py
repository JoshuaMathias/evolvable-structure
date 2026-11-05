"""Classify what an entry call did (ok, pending-key, load-error, ...) from the exception it raised and its structured reasons."""
from __future__ import annotations

from typing import List, Sequence, Tuple

from esoi.runtime.assemble_by_name.assembly_errors import AssemblyError
from esoi.runtime.assemble_by_name.entry_types import EntryError, Pending, Reason
from esoi.runtime.assemble_by_name.offline_guard import Offline
from esoi.runtime.implementation_selection.selection_registry import SelectionError


ANSWERING = ("ok", "pending-key", "pending-install", "pending-network")   # the outcomes that count as the one line answering
OUTCOMES = ("ok", "pending-key", "pending-install", "pending-network", "needs-option", "load-error", "live-attempt", "no-entry", "fail")


def chain_of_errors(error: BaseException) -> List[BaseException]:
    out: List[BaseException] = []
    while error is not None and error not in out:
        out.append(error)
        error = error.__cause__ or error.__context__
    return out


def pending_outcome(reasons: Sequence[Reason]) -> str:
    """The outcome of a ``Pending`` read from its reasons by their leaves: a ``needs`` reason is settled by the reasons of the seats it
    waits on, so the result is the worst leaf (load-error, then needs-option for an option or an object to pass, then
    pending-install, then pending-key, then pending-network). The leaves are found through any chain of ``needs`` reasons. A ``needs`` with no leaf
    under it is needs-option."""
    settled = {one.seat for one in reasons if one.kind != "needs"}      # seats that end in a leaf
    grown = True
    while grown:    # a needs reason is settled once a seat it waits on is: a leaf, or a needs reason that is itself settled
        grown = False
        for one in reasons:
            if one.kind == "needs" and one.seat not in settled and any(seat in settled for seat in one.waits):
                settled.add(one.seat)
                grown = True
    kinds = set()
    for one in reasons:
        if one.kind != "needs":
            kinds.add(one.kind)
        elif one.seat not in settled:
            kinds.add("option")
    if "load" in kinds:
        return "load-error"
    if kinds & {"option", "provided"}:
        return "needs-option"
    if "install" in kinds:
        return "pending-install"
    if "key" in kinds:
        return "pending-key"
    if "network" in kinds:
        return "pending-network"
    return "needs-option"   # pending for a reason nothing declares: the default does not fill the seat


def classify(error: BaseException) -> Tuple[str, str, List[Reason]]:
    """``(outcome, detail, reasons)`` of an entry that raised, read from the exception's type and structured reasons."""
    if isinstance(error, Pending):
        outcome = pending_outcome(error.reasons)
        detail = " | ".join(error.lines)
        return outcome, detail, list(error.reasons)
    if any(isinstance(one, Offline) for one in chain_of_errors(error)):
        return "live-attempt", "tried the network or a program that no declared requirement named", []
    if isinstance(error, EntryError) and error.code == "no-entry":
        return "no-entry", str(error), []
    if isinstance(error, (AssemblyError, SelectionError, ImportError)):
        return "load-error", f"{type(error).__name__}: {error}"[:300], []
    return "fail", f"{type(error).__name__}: {error}"[:300], []
