"""Show an author only the standards whose risk tags and paths match a task or a file, and front the standards commands.

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
index. Running the ``Check:`` lines on a commit is ``esoi.structure.structure_check.standards_check``; this module is
the one command-line front for ``for-task``, ``for-file``, ``lint``, ``measure``, ``compare``, ``train``, ``check-staged``
and ``install-hook`` (``python -m esoi.understanding.spec_search.standards_nav``). The module reads no environment and
writes nothing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

STANDARDS_DIRS = ("docs/standards", "esoi/standards")   # the first that exists in a repository
WAIVER = "standards-waive:"   # the marker a check module honours; kept here so the format has one home
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
                    tags=listed(tags[0], ","), paths=listed(paths[0], ";"), rule=rule[0], checks=checks,
                    when=first_value(text, "When"), read_when=first_value(text, "Read when"))


def listed(line: str, separator: str) -> Tuple[str, ...]:
    """The non-empty, stripped items of a header line split on ``separator``."""
    return tuple(item.strip() for item in line.split(separator) if item.strip())


def first_value(text: str, key: str) -> str:
    """The first value of a header line, or an empty string when the line is absent."""
    return (header_line(text, key) or [""])[0]


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


def applies(std: Standard, relative: str, content: str, tags: Optional[Set[str]]) -> bool:
    """Whether a standard covers the file: its paths match, a requested tag is among its tags, and its When pattern is in the content."""
    if not matches(relative, std.paths) or (tags and not tags & set(std.tags)):
        return False
    return not std.when or not content or bool(re.search(std.when, content))


def for_file(file: Path, tags: Optional[Set[str]] = None) -> str:
    """The rules that apply to editing ``file``, as a few lines; empty when none do. ``tags`` narrows to those risk tags."""
    file = file.resolve()
    root = find_root(file)
    if root is None:
        return ""
    relative = str(file.relative_to(root))
    content = file.read_text(encoding="utf-8", errors="replace") if file.is_file() else ""
    hits = [s for s in load(root) if applies(s, relative, content, tags)]
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
    return by_rate(by_id, rates, ranked)


def by_rate(by_id: Dict[str, Standard], rates: Dict[str, float], ranked) -> List[Tuple[Standard, str]]:
    """The frequently broken standards first, then those the task names, each with the reason it is shown."""
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


def standard_problems(std, tags: dict) -> List[str]:
    """What one standard breaks of the standard for writing standards: undefined tags, a long or hedged rule, long messages, em dashes."""
    problems = [f"{std.file}: tag '{t}' is not a row of tags.csv" for t in std.tags if t not in tags]
    words = len(std.rule.split())
    if words > 40 or not std.rule.rstrip().endswith("."):
        problems.append(f"{std.file}: the Rule is one sentence of at most 40 words ({words} here) ending in a full stop")
    if any(h in std.rule.lower() for h in HEDGES):
        problems.append(f"{std.file}: the Rule states what to do, with no hedge words ({', '.join(HEDGES)})")
    problems += [f"{std.file}: a Check message is at most 45 words and says what to do instead"
                 for check in std.checks if len(check.message.split()) > 45]
    problems += [f"{std.file}: no em dash in rule or message text" for text in (std.rule, *[c.message for c in std.checks]) if "\u2014" in text]
    return problems


def tag_problems(t) -> List[str]:
    """What one tag row breaks: missing mitigates, meaning or keywords, or a meaning that does not name the risk."""
    if not (t.mitigates and t.meaning and t.keywords):
        return [f"tags.csv: tag '{t.tag}' needs mitigates, meaning and keywords"]
    if not t.meaning.lower().startswith("risk of"):
        return [f"tags.csv: tag '{t.tag}' meaning starts 'Risk of ...' (the risk the tag mitigates)"]
    return []


def lint(root: Path) -> List[str]:
    """The standard for writing standards, checked: every tag is defined, and rule and message text is plain and short."""
    tags = load_tags(root)
    problems: List[str] = []
    for std in load(root):
        problems += standard_problems(std, tags)
    for t in tags.values():
        problems += tag_problems(t)
    return problems


def build_parser():
    """The command-line parser of the standards navigator."""
    import argparse
    ap = argparse.ArgumentParser(prog="esoi.understanding.spec_search.standards_nav", description=__doc__.split("\n")[0])
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
    return ap


def measured_report(args, root: Path) -> str:
    """The text of the ``compare``, ``train`` and ``measure`` commands, which score the standards against a cases file."""
    from esoi.understanding.spec_search import standards_measure
    repo, cases = Path(args.repo).resolve(), Path(args.cases)
    if args.cmd == "compare":
        return standards_measure.compare_report(standards_measure.compare(root, repo, cases))
    if args.cmd == "train":
        return standards_measure.train(root, repo, cases, args.date)
    return standards_measure.report(standards_measure.run(root, repo, cases, args.baseline, args.label))


def rooted_command(args, root: Path) -> Optional[int]:
    """Run a command that needs the standards folder; None when the command is another kind."""
    if args.cmd == "for-task":
        print(for_task(root, " ".join(args.task)))
        return 0
    if args.cmd in ("compare", "train", "measure"):
        print(measured_report(args, root))
        return 0
    if args.cmd == "lint":
        problems = lint(root)
        print("\n".join(problems))
        return 1 if problems else 0
    return None


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "for-file":
        for file in args.file:
            print(for_file(Path(file), set(args.tag) or None))
        return 0
    root = find_root(Path(args.repo).resolve())
    done = rooted_command(args, root) if root else None
    return done if done is not None else hook_or_staged(args, root)


def hook_or_staged(args, root: Optional[Path]) -> int:
    """Install the pre-commit hook, or check the staged change (and print the advisory) when a standards folder was found."""
    from esoi.structure.structure_check import standards_check
    if args.cmd == "install-hook":
        print(standards_check.install_hook(root or Path(args.repo).resolve()))
        return 0
    text = standards_check.report(standards_check.check_staged(root)) if root else ""
    print(text or (standards_check.advisory(root) if root else ""))
    return 1 if text else 0


if __name__ == "__main__":
    raise SystemExit(main())
