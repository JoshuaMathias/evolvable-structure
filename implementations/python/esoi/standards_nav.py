"""Navigate a repository's standards by risk tag, at the moment of an edit, and check a commit against them.

A repository keeps one small file per standard in ``docs/standards/``. A file takes part in navigation when its header
carries these lines (the rest of the file is read only by someone who needs the detail)::

    **Tags:** request-path-cost, low-quality-code
    **Paths:** app/api/endpoints/**/*.py; app/api/routes/**/*.py
    **Rule:** One sentence an author can act on without opening the file.
    **Check:** regex:\\b(embed_text|call_llm)\\( => Say what bounds this call ...
    **Check:** undecorated-def => A route module holds handlers only; move the helper into a service.
    **Check:** needs-test:tests/** => A change under these paths ships with a test.

Tags name the risk a standard mitigates (the skill's R1 to R4 style risks, here the risk of low quality code), so a tag
is a handle on a problem the repository's records define, never a topic. Navigation is by tag and path: ``for_file``
returns only the rules whose paths match the file being edited, so an author sees three lines instead of a standards
index. ``check_staged`` runs the ``Check:`` lines against the lines a commit ADDS, never the old code, so a repository
with years of legacy adopts a standard without a waiver for every old violation.

A finding is waived at the line that causes it with ``standards-waive: <standard id> <reason>``; the reason shows in
review. The module reads no environment and writes nothing.
"""
from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

STANDARDS_DIR = "docs/standards"
WAIVER = "standards-waive:"
MAX_SHOWN = 4


@dataclass(frozen=True)
class Check:
    kind: str          # regex | undecorated-def | needs-test
    argument: str
    message: str


@dataclass(frozen=True)
class Standard:
    id: str
    file: str          # path relative to the repository root
    title: str
    tags: Tuple[str, ...]
    paths: Tuple[str, ...]
    rule: str
    checks: Tuple[Check, ...] = ()


@dataclass(frozen=True)
class Finding:
    standard: str
    file: str
    line: int
    message: str

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.standard}] {where}: {self.message}"


def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """``**`` crosses folders, ``*`` stays in one, ``?`` is one character."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def matches(path: str, patterns: Tuple[str, ...]) -> bool:
    return any(glob_to_regex(p).match(path) for p in patterns)


def header_line(text: str, name: str) -> List[str]:
    return [m.group(1).strip() for m in re.finditer(rf"^\*\*{name}:\*\*[ \t]*(.+)$", text, re.M)]


def parse_check(raw: str) -> Optional[Check]:
    body, _, message = raw.partition("=>")
    body, message = body.strip(), message.strip()
    kind, _, argument = body.partition(":")
    if kind not in ("regex", "undecorated-def", "needs-test") or not message:
        return None
    return Check(kind, argument.strip(), message)


def parse_standard(root: Path, path: Path) -> Optional[Standard]:
    """A standard takes part in navigation when it has Tags, Paths and Rule lines; otherwise it is skipped."""
    text = path.read_text(encoding="utf-8")
    tags, paths, rule = header_line(text, "Tags"), header_line(text, "Paths"), header_line(text, "Rule")
    if not (tags and paths and rule):
        return None
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), path.stem)
    checks = tuple(c for c in (parse_check(r) for r in header_line(text, "Check")) if c)
    return Standard(id=path.stem, file=str(path.relative_to(root)), title=title,
                    tags=tuple(t.strip() for t in tags[0].split(",") if t.strip()),
                    paths=tuple(p.strip() for p in re.split(r"[;]", paths[0]) if p.strip()), rule=rule[0], checks=checks)


def find_root(start: Path) -> Optional[Path]:
    """The nearest folder above ``start`` that has a standards folder."""
    here = start if start.is_dir() else start.parent
    for folder in (here, *here.parents):
        if (folder / STANDARDS_DIR).is_dir():
            return folder
    return None


def load(root: Path) -> List[Standard]:
    found = (parse_standard(root, p) for p in sorted((root / STANDARDS_DIR).glob("*.md")))
    return [s for s in found if s]


def for_file(file: Path, tags: Optional[Set[str]] = None) -> str:
    """The rules that apply to editing ``file``, as a few lines; empty when none do. ``tags`` narrows to those risk tags."""
    file = file.resolve()
    root = find_root(file)
    if root is None:
        return ""
    relative = str(file.relative_to(root))
    hits = [s for s in load(root) if matches(relative, s.paths) and (not tags or tags & set(s.tags))]
    if not hits:
        return ""
    lines = [f"Standards for {relative} (full text only if you need it):"]
    lines += [f"- [{', '.join(s.tags)}] {s.rule} ({s.file})" for s in hits[:MAX_SHOWN]]
    if len(hits) > MAX_SHOWN:
        lines.append(f"- and {len(hits) - MAX_SHOWN} more under {STANDARDS_DIR}/")
    return "\n".join(lines)


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


def check_staged(root: Path) -> List[Finding]:
    """Run every standard's checks over the lines the staged change adds."""
    standards = [s for s in load(root) if s.checks]
    if not standards:
        return []
    diff = added_lines(git(root, "diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR"))
    staged = sorted(diff)
    findings: List[Finding] = []
    for std in standards:
        in_scope = [f for f in staged if matches(f, std.paths)]
        for check in std.checks:
            if check.kind == "needs-test":
                tests = glob_to_regex(check.argument or "tests/**")
                if in_scope and not any(tests.match(f) for f in staged) and not any(waived_no_test(std.id, t) for f in in_scope for t in diff[f].values()):
                    findings.append(Finding(std.id, in_scope[0], 0, check.message))
                continue
            for f in in_scope:
                findings += check_one(std, check, root, f, diff[f], staged)
    return findings


def report(findings: List[Finding]) -> str:
    if not findings:
        return ""
    head = f"{len(findings)} standards finding(s) in the lines this commit adds:"
    tail = (f"Fix them, or waive one at its line with `{WAIVER} <standard id> <reason in three or more words>` "
            "(a missing test is waived on any changed line of the module with `standards-waive: <standard id> no-test <reason>`).")
    return "\n".join([head, *[f"  {f}" for f in findings], tail])


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="esoi.standards_nav", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("for-file", help="print the rules that apply to editing a file")
    f.add_argument("file")
    f.add_argument("--tag", action="append", default=[])
    c = sub.add_parser("check-staged", help="check the staged change against the standards' Check lines")
    c.add_argument("repo", nargs="?", default=".")
    args = ap.parse_args(argv)
    if args.cmd == "for-file":
        print(for_file(Path(args.file), set(args.tag) or None))
        return 0
    root = find_root(Path(args.repo).resolve())
    text = report(check_staged(root)) if root else ""
    print(text)
    return 1 if text else 0


if __name__ == "__main__":
    raise SystemExit(main())
