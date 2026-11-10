"""Run a standard's Check lines over the lines a commit adds, and install the pre-commit hook that does it.

A standard whose header carries ``**Check:**`` lines (see ``esoi.understanding.spec_search.standards_nav`` for the format and
for selecting standards by tag and path) is a rule that can be run: ``check_staged`` applies each check to the lines the
staged change ADDS, never the old code, so a repository with years of legacy adopts a standard without a waiver for every
old violation. A finding is waived at the line that causes it with ``standards-waive: <standard id> <reason>``. The
command line for this module is ``python -m esoi.understanding.spec_search.standards_nav check-staged`` and
``install-hook``. The module reads no environment; ``install_hook`` writes only the hook file.
"""
from __future__ import annotations

import ast
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from esoi.understanding.spec_search.standards_nav import (WAIVER, Check, Standard, glob_to_regex, lint, load, matches,
                                                           standards_dir)


@dataclass(frozen=True)
class Finding:
    standard: str
    file: str
    line: int
    message: str

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.standard}] {where}: {self.message}"



def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else ""


def added_lines(diff: str) -> Dict[str, Dict[int, str]]:
    """File -> {line number: text} for the lines a ``-U0`` diff adds."""
    out: Dict[str, Dict[int, str]] = {}
    current, number = "", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current, number = raw[6:], 0
            out.setdefault(current, {})
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            number = int(m.group(1)) if m else 0
        elif current and raw.startswith("+") and not raw.startswith("+++"):
            out[current][number] = raw[1:]
            number += 1
    return out


def waived(standard: str, line: str) -> bool:
    """A waiver names the standard and gives a reason of at least three words."""
    m = re.search(rf"{re.escape(WAIVER)}\s*{re.escape(standard)}\s+(.+)", line)
    return bool(m and len(m.group(1).split()) >= 3)


def waived_no_test(standard: str, line: str) -> bool:
    """A missing test is waived only by ``standards-waive: <id> no-test <reason>``, so a waiver of another check cannot cover it."""
    m = re.search(rf"{re.escape(WAIVER)}\s*{re.escape(standard)}\s+no-test\s+(.+)", line)
    return bool(m and len(m.group(1).split()) >= 3)


def undecorated_defs(source: str, added: Dict[int, str]) -> List[int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [n.lineno for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.decorator_list and n.lineno in added]


def check_one(std: Standard, check: Check, root: Path, file: str, added: Dict[int, str], staged: List[str]) -> List[Finding]:
    if check.kind == "regex":
        pattern = re.compile(check.argument)
        return [Finding(std.id, file, n, check.message) for n, text in added.items()
                if pattern.search(text) and not waived(std.id, text)]
    if check.kind == "undecorated-def":
        source = git(root, "show", f":{file}")
        return [Finding(std.id, file, n, check.message) for n in undecorated_defs(source, added)
                if not waived(std.id, added.get(n, ""))]
    return []


def untested(std, check, in_scope: List[str], staged: List[str], diff: dict) -> bool:
    """Whether files in a standard's scope are staged with no test beside them and no waiver in what was added."""
    tests = glob_to_regex(check.argument or "tests/**")
    if not in_scope or any(tests.match(f) for f in staged):
        return False
    return not any(waived_no_test(std.id, t) for f in in_scope for t in diff[f].values())


def standard_findings(std, root: Path, staged: List[str], diff: dict) -> List[Finding]:
    """The findings of one standard's checks over the staged files in its scope."""
    findings: List[Finding] = []
    in_scope = [f for f in staged if matches(f, std.paths)]
    for check in std.checks:
        if check.kind == "needs-test":
            if untested(std, check, in_scope, staged, diff):
                findings.append(Finding(std.id, in_scope[0], 0, check.message))
            continue
        for f in in_scope:
            findings += check_one(std, check, root, f, diff[f], staged)
    return findings


def check_staged(root: Path) -> List[Finding]:
    """Run every standard's checks over the lines the staged change adds."""
    standards = [s for s in load(root) if s.checks]
    diff = added_lines(git(root, "diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR"))
    staged = sorted(diff)
    findings: List[Finding] = []
    folder = standards_dir(root)
    if folder and any(f.startswith(str(folder.relative_to(root))) for f in staged):
        findings += [Finding("standards-lint", str(folder.relative_to(root)), 0, p) for p in lint(root)]
    for std in standards:
        findings += standard_findings(std, root, staged, diff)
    return findings


def unchecked(root: Path) -> List[Standard]:
    """Standards that apply to the staged files but have no automatic check, so the author confirms them by hand."""
    staged = sorted(added_lines(git(root, "diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR")))
    return [s for s in load(root) if not s.checks and any(matches(f, s.paths) for f in staged)]


def advisory(root: Path) -> str:
    rules = unchecked(root)
    if not rules:
        return ""
    return "\n".join(["Rules for this change with no automatic check (confirm each by hand before committing):",
                      *[f"  - [{', '.join(s.tags)}] {s.rule} ({s.file})" for s in rules]])


def report(findings: List[Finding]) -> str:
    if not findings:
        return ""
    head = f"{len(findings)} standards finding(s) in the lines this commit adds:"
    tail = (f"Fix them, or waive one at its line with `{WAIVER} <standard id> <reason in three or more words>` "
            "(a missing test is waived on any changed line of the module with `standards-waive: <standard id> no-test <reason>`).")
    return "\n".join([head, *[f"  {f}" for f in findings], tail])


HOOK_MARK = "# Installed by `python -m esoi.understanding.spec_search.standards_nav install-hook`."
HOOK = """#!/bin/sh
""" + HOOK_MARK + """ Checks the staged change against the repository's standards
# (docs/standards or esoi/standards): a finding blocks the commit, rules with no automatic check are listed.
# Tries the interpreter that installed the hook first, then the repository's own environments.
# Fails open when esoi is not importable, so a checkout without it (a server) still commits.
root=$(git rev-parse --show-toplevel)
for py in {python} "$root/venv/bin/python3" "$root/.venv/bin/python3" python3; do
  "$py" -c "import esoi.understanding.spec_search.standards_nav" 2>/dev/null && exec "$py" -m esoi.understanding.spec_search.standards_nav check-staged "$root"
done
echo "standards check skipped: esoi is not installed here" >&2
exit 0
"""


def hook_text(python: str) -> str:
    """The hook, trying ``python`` (the interpreter that installs it) before the repository's environments."""
    return HOOK.replace("{python}", shlex.quote(python))


def install_hook(root: Path, python: str = sys.executable) -> Path:
    """Write the pre-commit hook where git looks for hooks (``core.hooksPath`` is honoured). Rewrites an earlier copy of this
    hook, so reinstalling with a working interpreter repairs it; never overwrites another hook."""
    folder = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
    target = folder / "pre-commit"
    if target.exists() and HOOK_MARK not in target.read_text():
        raise FileExistsError(f"{target} exists and is not this hook; add `python -m esoi.understanding.spec_search.standards_nav check-staged` to it")
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(hook_text(python))
    if target.stat().st_mode & 0o111 != 0o111:   # a shared checkout's hook may belong to another user; chmod only when needed
        target.chmod(0o755)
    return target
