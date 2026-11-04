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

STANDARDS_DIRS = ("docs/standards", "esoi/standards")   # the first that exists in a repository
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
    when: str = ""          # optional regex on the file's content: the standard is shown only when the file matches it
    read_when: str = ""


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
                    paths=tuple(p.strip() for p in re.split(r"[;]", paths[0]) if p.strip()), rule=rule[0], checks=checks,
                    when=(header_line(text, "When") or [""])[0], read_when=(header_line(text, "Read when") or [""])[0])


def standards_dir(root: Path) -> Optional[Path]:
    return next((root / d for d in STANDARDS_DIRS if (root / d).is_dir()), None)


def find_root(start: Path) -> Optional[Path]:
    """The nearest folder above ``start`` that has a standards folder."""
    here = start if start.is_dir() else start.parent
    for folder in (here, *here.parents):
        if standards_dir(folder):
            return folder
    return None


def load(root: Path) -> List[Standard]:
    folder = standards_dir(root)
    found = (parse_standard(root, p) for p in sorted(folder.glob("*.md"))) if folder else ()
    return [s for s in found if s]


def for_file(file: Path, tags: Optional[Set[str]] = None) -> str:
    """The rules that apply to editing ``file``, as a few lines; empty when none do. ``tags`` narrows to those risk tags."""
    file = file.resolve()
    root = find_root(file)
    if root is None:
        return ""
    relative = str(file.relative_to(root))
    content = file.read_text(encoding="utf-8", errors="replace") if file.is_file() else ""
    hits = [s for s in load(root) if matches(relative, s.paths) and (not tags or tags & set(s.tags))
            and (not s.when or not content or re.search(s.when, content))]
    if not hits:
        return ""
    lines = [f"Standards for {relative} (full text only if you need it):"]
    lines += [f"- [{', '.join(s.tags)}] {s.rule} ({s.file})" for s in hits[:MAX_SHOWN]]
    if len(hits) > MAX_SHOWN:
        lines.append(f"- and {len(hits) - MAX_SHOWN} more in the standards folder")
    return "\n".join(lines)


@dataclass(frozen=True)
class Tag:
    tag: str
    mitigates: str     # the id of the problem in the repository's records that the tag is a handle on
    meaning: str       # "Risk of X because Y", one sentence
    keywords: Tuple[str, ...]   # task-language words that suggest the risk, for matching before any code exists


def load_tags(root: Path) -> Dict[str, Tag]:
    folder = standards_dir(root)
    path = folder / "tags.csv" if folder else None
    if not path or not path.is_file():
        return {}
    import csv
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {r["tag"]: Tag(r["tag"], r.get("mitigates", ""), r.get("meaning", ""),
                          tuple(w.strip().lower() for w in (r.get("keywords") or "").split(";") if w.strip())) for r in rows}


WORD = re.compile(r"[a-z][a-z0-9-]+")


def rank_task(root: Path, task: str) -> List[Tuple[float, Standard, List[str]]]:
    """The standards a described task is likely to meet, best first, as (score, standard, matched keywords)."""
    words = set(WORD.findall(task.lower()))
    tags = load_tags(root)
    scored = []
    for std in load(root):
        keyword_hits = {k for t in std.tags for k in (tags[t].keywords if t in tags else ()) if k in words or any(w.startswith(k) for w in words)}
        own = words & set(WORD.findall(f"{std.title} {std.rule} {std.read_when}".lower())) - STOP
        score = len(keyword_hits) + 0.5 * len(own)
        if score >= 1:
            scored.append((score, std, sorted(keyword_hits)))
    scored.sort(key=lambda item: -item[0])
    return scored


BASE_RATE_MIN = 0.10   # a standard broken by at least this share of past commits is shown for every task
KEYWORD_SLOTS = 2      # slots kept for standards the task names, so frequent rules never crowd out a rare one


def combine(frequent: List[str], named: List[str]) -> List[str]:
    """Frequent standards first, but never so many that fewer than ``KEYWORD_SLOTS`` named ones fit in ``MAX_SHOWN``."""
    named = [sid for sid in named if sid not in frequent] + [sid for sid in named if sid in frequent]
    fresh = [sid for sid in named if sid not in frequent]
    room = MAX_SHOWN - min(len(fresh), KEYWORD_SLOTS)
    head = frequent[:room]
    return head + [sid for sid in fresh if sid not in head] + [sid for sid in frequent[room:] if sid not in head]


def load_rates(root: Path) -> Dict[str, float]:
    """Standard id -> share of past commits that broke it, from ``rates.csv`` beside the standards (written by ``train``)."""
    folder = standards_dir(root)
    path = folder / "rates.csv" if folder else None
    if not path or not path.is_file():
        return {}
    import csv
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["standard"]: float(row["rate"]) for row in csv.DictReader(handle)}


def select_for_task(root: Path, task: str) -> List[Tuple[Standard, str]]:
    """The standards shown for a task: first those past commits broke most often, then those whose tag keywords the task
    names. Selected by the metric (see ``standards_measure.compare``): the base rate alone beats matching task words on
    commits it had not seen, and the keywords keep a rare standard reachable."""
    by_id = {std.id: std for std in load(root)}
    rates = load_rates(root)
    ranked = rank_task(root, task)
    if not rates:
        return [(std, "matched " + (", ".join(hits) or "its own wording")) for _, std, hits in ranked]
    frequent = [sid for sid in sorted(rates, key=lambda i: -rates[i]) if rates[sid] >= BASE_RATE_MIN and sid in by_id]
    hit_words = {std.id: hits for _, std, hits in ranked if hits}
    named = [std.id for _, std, hits in ranked if hits]
    return [(by_id[sid], f"broken by {rates[sid]:.0%} of past commits" if sid in frequent and sid not in hit_words
             else "matched " + ", ".join(hit_words[sid])) for sid in combine(frequent, named)]


def for_task(root: Path, task: str) -> str:
    """Before any code exists: the standards a described task is likely to meet, found without a model."""
    chosen = select_for_task(root, task)
    if not chosen:
        return ""
    lines = ["Standards this task is likely to meet (open the file only for detail):"]
    lines += [f"- [{', '.join(std.tags)}] {std.rule} ({std.file}; {why})" for std, why in chosen[:MAX_SHOWN]]
    return "\n".join(lines)


STOP = {"the", "and", "for", "that", "with", "this", "from", "into", "each", "when", "are", "not", "any", "can", "all", "one"}
HEDGES = ("should", "try to", "consider", "ideally", "if possible")


def lint(root: Path) -> List[str]:
    """The standard for writing standards, checked: every tag is defined, and rule and message text is plain and short."""
    tags, problems = load_tags(root), []
    for std in load(root):
        for t in std.tags:
            if t not in tags:
                problems.append(f"{std.file}: tag '{t}' is not a row of tags.csv")
        words = len(std.rule.split())
        if words > 40 or not std.rule.rstrip().endswith("."):
            problems.append(f"{std.file}: the Rule is one sentence of at most 40 words ({words} here) ending in a full stop")
        if any(h in std.rule.lower() for h in HEDGES):
            problems.append(f"{std.file}: the Rule states what to do, with no hedge words ({', '.join(HEDGES)})")
        for check in std.checks:
            if len(check.message.split()) > 45:
                problems.append(f"{std.file}: a Check message is at most 45 words and says what to do instead")
        for text in (std.rule, *[c.message for c in std.checks]):
            if "\u2014" in text:
                problems.append(f"{std.file}: no em dash in rule or message text")
    for t in tags.values():
        if not (t.mitigates and t.meaning and t.keywords):
            problems.append(f"tags.csv: tag '{t.tag}' needs mitigates, meaning and keywords")
        elif not t.meaning.lower().startswith("risk of"):
            problems.append(f"tags.csv: tag '{t.tag}' meaning starts 'Risk of ...' (the risk the tag mitigates)")
    return problems


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
    diff = added_lines(git(root, "diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR"))
    staged = sorted(diff)
    findings: List[Finding] = []
    folder = standards_dir(root)
    if folder and any(f.startswith(str(folder.relative_to(root))) for f in staged):
        findings += [Finding("standards-lint", str(folder.relative_to(root)), 0, p) for p in lint(root)]
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


HOOK = """#!/bin/sh
# Installed by `python -m esoi.standards_nav install-hook`. Checks the staged change against the repository's standards
# (docs/standards or esoi/standards): a finding blocks the commit, rules with no automatic check are listed.
# Fails open when esoi is not importable, so a checkout without it (a server) still commits.
root=$(git rev-parse --show-toplevel)
for py in "$root/venv/bin/python3" "$root/.venv/bin/python3" python3; do
  "$py" -c "import esoi.standards_nav" 2>/dev/null && exec "$py" -m esoi.standards_nav check-staged "$root"
done
echo "standards check skipped: esoi is not installed here" >&2
exit 0
"""


def install_hook(root: Path) -> Path:
    """Write the pre-commit hook where git looks for hooks (``core.hooksPath`` is honoured); never overwrites another hook."""
    folder = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
    target = folder / "pre-commit"
    if target.exists() and target.read_text() != HOOK:
        raise FileExistsError(f"{target} exists and is not this hook; add `python -m esoi.standards_nav check-staged` to it")
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(HOOK)
    target.chmod(0o755)
    return target


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="esoi.standards_nav", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("for-file", help="print the rules that apply to editing a file")
    f.add_argument("file", nargs="+")
    f.add_argument("--tag", action="append", default=[])
    c = sub.add_parser("check-staged", help="check the staged change against the standards' Check lines")
    c.add_argument("repo", nargs="?", default=".")
    t = sub.add_parser("for-task", help="print the standards a described task is likely to meet, before any code exists")
    t.add_argument("task", nargs="+")
    t.add_argument("--repo", default=".")
    sub.add_parser("lint", help="check the standards folder against the standard for writing standards").add_argument("repo", nargs="?", default=".")
    m = sub.add_parser("measure", help="score for-task against the standards that applied to real past work (cases file)")
    m.add_argument("cases")
    m.add_argument("--repo", default=".")
    m.add_argument("--baseline", action="store_true", help="score the arm that ignores the task and shows the first standards")
    m.add_argument("--label", choices=("applicable", "violated"), default="applicable")
    cp = sub.add_parser("compare", help="held-out comparison of the ways of choosing standards for a task")
    cp.add_argument("cases")
    cp.add_argument("--repo", default=".")
    tr = sub.add_parser("train", help="write rates.csv beside the standards from the cases (the share of past work that broke each)")
    tr.add_argument("cases")
    tr.add_argument("--repo", default=".")
    tr.add_argument("--date", required=True)
    i = sub.add_parser("install-hook", help="write the pre-commit hook for a repository")
    i.add_argument("repo", nargs="?", default=".")
    args = ap.parse_args(argv)
    if args.cmd == "for-file":
        for file in args.file:
            print(for_file(Path(file), set(args.tag) or None))
        return 0
    root = find_root(Path(args.repo).resolve())
    if args.cmd == "for-task" and root:
        print(for_task(root, " ".join(args.task)))
        return 0
    if args.cmd == "compare" and root:
        from esoi import standards_measure
        print(standards_measure.compare_report(standards_measure.compare(root, Path(args.repo).resolve(), Path(args.cases))))
        return 0
    if args.cmd == "train" and root:
        from esoi import standards_measure
        print(standards_measure.train(root, Path(args.repo).resolve(), Path(args.cases), args.date))
        return 0
    if args.cmd == "measure" and root:
        from esoi import standards_measure
        print(standards_measure.report(standards_measure.run(root, Path(args.repo).resolve(), Path(args.cases), args.baseline, args.label)))
        return 0
    if args.cmd == "lint" and root:
        problems = lint(root)
        print("\n".join(problems))
        return 1 if problems else 0
    if args.cmd == "install-hook":
        print(install_hook(root or Path(args.repo).resolve()))
        return 0
    text = report(check_staged(root)) if root else ""
    print(text or (advisory(root) if root else ""))
    return 1 if text else 0


if __name__ == "__main__":
    raise SystemExit(main())
