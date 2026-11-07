"""Attestations: a person says the arm's own code changed but not what its result measures.

A result goes stale when the arm's own code changes (``esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness``). Some changes cannot move the number: a rename, a
comment, a refactor that keeps behaviour. ``esoi attest <component> <impl> --reason "..."`` records that, in
``attestations.csv`` beside the results log (commit it with the code it covers). An attestation names the commit range it covers
(``from_sha``, the commit the result was recorded at or the end of the previous attestation, through ``through_sha``), who made it
and why. The result then counts as current for that range, and goes stale again on any later change to the arm's own code outside
it. Staleness only informs: it never blocks the selection rule and never starts a re-run, attested or not.

An attestation is refused when no reason is given, when the arm has no whole-run result to attest, when that result was recorded
on uncommitted code, when nothing in the arm's own code changed (it is already current), and when the arm's own code changed
outside the range (an uncommitted edit, or a commit after ``--through``): commit it, or attest through it, or re-run. Standard
library only; nothing is run.
"""
from __future__ import annotations

import csv
import getpass
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.tables import read_csv

FILE = "attestations.csv"
COLUMNS = ["date", "component", "impl", "from_sha", "through_sha", "author", "reason", "files"]
Row = Dict[str, str]


class AttestError(ValueError):
    """The attestation is refused; the message says what to do instead."""


def path_of(config: Config) -> Path:
    return config.results_path.parent / FILE


def read(config: Config) -> List[Row]:
    return read_csv(path_of(config))


def chain(config: Config, component: str, impl: str, sha: str) -> List[Row]:
    """The attestations that follow one another from the commit a result was recorded at: each starts where the one before ended."""
    rows = [r for r in read(config) if r.get("component") == component and r.get("impl") == impl]
    found: List[Row] = []
    base = sha.removesuffix("-dirty")
    progressed = True
    while progressed:
        progressed = False
        for row in rows:
            if row.get("from_sha") == base and row not in found:
                found.append(row)
                base = row.get("through_sha", "")
                progressed = True
                break
    return found


def covered_base(config: Config, component: str, impl: str, sha: str) -> str:
    """The commit from which the arm's own code counts: the row's own, or where its attestations end."""
    found = chain(config, component, impl, sha)
    return found[-1]["through_sha"] if found else sha


def note(config: Config, component: str, impl: str, sha: str) -> str:
    """``current by attestation (reason)`` for a result that has attestations, '' for one that has none."""
    found = chain(config, component, impl, sha)
    if not found:
        return ""
    return "current by attestation (" + "; ".join(r.get("reason", "") for r in found) + ")"


def git(config: Config, *args: str) -> Tuple[int, str]:
    done = subprocess.run(["git", *args], cwd=config.root, capture_output=True, text=True)
    return done.returncode, done.stdout.strip()


def author_of(config: Config) -> str:
    _, name = git(config, "config", "user.name")
    _, email = git(config, "config", "user.email")
    return f"{name} <{email}>" if name and email else name or email or getpass.getuser()


def range_end(config: Config, base: str, through: str) -> str:
    """The commit an attestation runs through: ``through`` (default HEAD), which must be a commit descending from ``base``."""
    code, end = git(config, "rev-parse", "--short", through or "HEAD")
    if code != 0 or not end:
        raise AttestError(f"{through or 'HEAD'} is not a commit here")
    code, _ = git(config, "merge-base", "--is-ancestor", base, end)
    if code != 0:
        raise AttestError(f"{end} does not descend from {base}, the commit the result stands on")
    return end


def attestable_range(config: Config, component: str, impl: str, row: Row, through: str, staleness: Any):
    """``(base, end, what changed inside)`` of the commit range an attestation covers, or raise ``AttestError`` when none can be attested."""
    sha = row.get("git_sha", "").strip()
    if not sha or sha.endswith("-dirty"):
        raise AttestError(f"its latest row was recorded {'on uncommitted code' if sha else 'with no commit'}, so there is no commit range to attest; re-run it with --record")
    base = covered_base(config, component, impl, sha)
    end = range_end(config, base, through)
    inside = staleness.explain(config, component, impl, base, until=end)
    if inside is None:
        raise AttestError(f"the commit {base} is not known here, so no change can be compared")
    outside = staleness.explain(config, component, impl, end)
    if outside and outside["counts"]:
        raise AttestError("the arm's own code changed outside the range " + f"{base}..{end}: " + "; ".join(outside["counts"][:5])
                          + " (commit it and attest through it, or re-run the arm)")
    if not inside["counts"]:
        raise AttestError(f"nothing in the arm's own code changed between {base} and {end}: the result is already current")
    return base, end, inside


def append_entry(path: Path, entry: Row) -> None:
    """Append one attestation to the CSV, writing the header when the file is new."""
    fresh = not path.is_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        if fresh:
            writer.writeheader()
        writer.writerow(entry)


def attest(config: Config, component: str, impl: str, reason: str, through: str = "", author: str = "",
           say: Callable[[str], None] = print) -> Row:
    """Record an attestation for the arm's latest whole-run result, or raise ``AttestError``."""
    from esoi.optimization.leaderboard import results_log
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import staleness
    if not (reason or "").strip():
        raise AttestError("a reason is required: say what changed in the arm's code and why its result still measures the same thing")
    row = results_log.latest_results(config.results_path, whole=True).get(component, {}).get(impl)
    if row is None:
        raise AttestError(f"{component}/{impl} has no recorded whole-run result, so there is nothing to attest")
    base, end, inside = attestable_range(config, component, impl, row, through, staleness)
    entry = {"date": date.today().isoformat(), "component": component, "impl": impl, "from_sha": base, "through_sha": end,
             "author": (author or author_of(config)).strip(), "reason": " ".join(reason.split()),
             "files": ";".join(line.split(",")[0] for line in inside["counts"][:8])}
    path = path_of(config)
    append_entry(path, entry)
    say(f"attested {component}/{impl} for {base}..{end}: {entry['files'] or 'its own code'}; commit {path.relative_to(config.root).as_posix()} "
        f"with the change. It goes stale again on any later change to the arm's own code.")
    return entry


def run_cli(config: Config, component: str, impl: str, reason: str, through: str = "", author: str = "",
            say: Callable[[str], None] = print) -> int:
    """``esoi attest COMPONENT IMPL --reason TEXT [--through SHA] [--author NAME]``: 0 when recorded, 2 when refused."""
    try:
        attest(config, component, impl, reason, through, author, say)
    except AttestError as exc:
        say(f"esoi attest: {exc}")
        return 2
    return 0
