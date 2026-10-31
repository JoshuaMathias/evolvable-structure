"""The documentation standard and the wiki made from it: ``esoi docs check`` and ``esoi docs wiki``.

A repository's ``docs/`` holds the one source, in the four categories of the Diataxis framework: ``tutorials/``,
``how-to/``, ``explanation/`` and ``reference/``, plus an index ``docs/README.md``. ``check`` fails when a page sits outside
those folders or an internal link does not resolve. ``wiki`` generates a GitHub wiki from the same pages (Home from the index,
a sidebar grouped by category, links rewritten to wiki page names), so the wiki is never edited and cannot drift. Pushing the
result is a separate, explicit step (``--push``); nothing here runs a model or reads the network except that push.
"""
from __future__ import annotations

import posixpath
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

CATEGORIES: Tuple[Tuple[str, str], ...] = (("tutorials", "Tutorials"), ("how-to", "How-to guides"),
                                           ("explanation", "Explanation"), ("reference", "Reference"))
INDEX = "README.md"
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#)", re.I)


def pages_under(root: Path, docs: str = "docs") -> List[str]:
    """Every markdown file under the docs folder, relative to the repository root (posix), sorted."""
    return sorted(p.relative_to(root).as_posix() for p in (root / docs).rglob("*.md"))


def category_of(path: str, docs: str = "docs") -> Optional[str]:
    """The Diataxis folder name a docs page sits in, or None (the index, or a page outside the four)."""
    parts = Path(path).relative_to(docs).parts
    return parts[0] if len(parts) > 1 and parts[0] in dict(CATEGORIES) else None


def prose(text: str) -> str:
    """The text without fenced and inline code, where a bracketed example is not a link."""
    return re.sub(r"`[^`\n]*`", "", re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.M | re.S))


def check(root: Path, docs: str = "docs") -> List[str]:
    """Problems with the docs: pages outside the four categories, and internal links that do not resolve."""
    found: List[str] = []
    if not (root / docs / INDEX).exists():
        found.append(f"{docs}/{INDEX}: the index is missing")
    for path in pages_under(root, docs):
        if path != f"{docs}/{INDEX}" and category_of(path, docs) is None:
            found.append(f"{path}: sits outside {', '.join(name + '/' for name, label in CATEGORIES)}; move it into exactly one")
    for path in pages_under(root, docs):
        for bang, label, target in LINK.findall(prose((root / path).read_text(encoding="utf-8"))):
            if EXTERNAL.match(target):
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target.partition("#")[0]))
            if target.partition("#")[0] and not (root / resolved).exists():
                found.append(f"{path}: link to {target} does not resolve")
    return found


def page_name(title: str) -> str:
    """A short wiki page name from a heading: the text before a colon or comma, with "(... template)" as a prefix."""
    template = re.search(r"\(([\w ]*)template\)\s*$", title)
    if template:
        title = "Template " + title[: template.start()].strip()
    title = re.split(r"[:,]", title, maxsplit=1)[0]
    title = re.sub(r"[^\w\s-]", "", title).strip()
    return re.sub(r"\s+", "-", title)


def collect_pages(root: Path, docs: str, extra: Sequence[str]) -> Dict[str, str]:
    """Map each source path (relative, posix) to its wiki page name."""
    pages: Dict[str, str] = {}
    for rel in pages_under(root, docs) + [e for e in extra if (root / e).exists()]:
        if rel == f"{docs}/{INDEX}":
            pages[rel] = "Home"
            continue
        first = HEADING.search((root / rel).read_text(encoding="utf-8"))
        name = page_name(first.group(2)) if first else page_name(Path(rel).stem.replace("-", " ").title())
        if name in pages.values():
            raise ValueError(f"two pages would be named {name}; change one heading ({rel})")
        pages[rel] = name
    return pages


def rewrite_links(text: str, source: str, pages: Dict[str, str], root: Path, repo_url: str, branch: str) -> str:
    """Point each relative link at a wiki page when the target is one, else at the file on the repository host."""
    def replace(match: "re.Match[str]") -> str:
        bang, label, target = match.groups()
        if EXTERNAL.match(target):
            return match.group(0)
        path, _, fragment = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        anchor = f"#{fragment}" if fragment else ""
        if resolved in pages and not bang:
            return f"[{label}]({pages[resolved]}{anchor})"
        readme = posixpath.join(resolved, INDEX)
        if readme in pages and not bang:
            return f"[{label}]({pages[readme]}{anchor})"
        kind = "tree" if (root / resolved).is_dir() else ("raw" if bang else "blob")
        return f"{bang}[{label}]({repo_url}/{kind}/{branch}/{resolved}{anchor})"
    return LINK.sub(replace, text)


def sidebar(home_text: str, home_source: str, pages: Dict[str, str], docs: str, extra: Sequence[str]) -> Tuple[str, List[str]]:
    """The sidebar: Home, then one group per category (from the folder), each page labelled as the start page labels it when it
    links to it, in the start page's order and then alphabetically. Pages outside the four folders go under "More"."""
    labels: Dict[str, str] = {}
    order: List[str] = []
    for line in home_text.splitlines():
        if re.match(r"^##\s+about", line, re.I):
            break
        for bang, label, target in LINK.findall(line):
            if EXTERNAL.match(target):
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(home_source), target.partition("#")[0]))
            if resolved in pages and resolved not in labels:
                labels[resolved] = label
                order.append(resolved)
    lines = ["**[Home](Home)**"]
    reached = ["Home"]
    groups = [(f"{docs}/{folder}/", title) for folder, title in CATEGORIES] + [("", "More")]
    placed: set = {home_source}
    for prefix, title in groups:
        members = [p for p in pages if p not in placed and (p.startswith(prefix) if prefix else True)]
        members.sort(key=lambda p: (order.index(p) if p in order else len(order), pages[p]))
        if not members:
            continue
        lines += ["", f"**{title}**", ""]
        for p in members:
            placed.add(p)
            lines.append(f"- [{labels.get(p, pages[p].replace('-', ' '))}]({pages[p]})")
            reached.append(pages[p])
    return "\n".join(lines).strip() + "\n", [pages[p] for p in order if p in pages] + ["Home"]


def strip_generated_comment(text: str) -> str:
    """Drop a leading 'Generated by ... Do not edit.' HTML comment: on the wiki the footer says where to edit."""
    return re.sub(r"\A<!--.*?-->\s*", "", text, flags=re.S)


def build_wiki(root: Path, out: Path, repo_url: str, branch: str = "main", docs: str = "docs",
               extra: Sequence[str] = (), strict: bool = False) -> Tuple[int, List[str]]:
    """Write every page, Home and the sidebar into ``out``, replacing the pages already there. Returns the page count and the
    pages the start page does not link to (a failure with ``strict``)."""
    pages = collect_pages(root, docs, extra)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.md"):
        old.unlink()
    for rel, name in pages.items():
        text = strip_generated_comment((root / rel).read_text(encoding="utf-8"))
        body = rewrite_links(text, rel, pages, root, repo_url, branch).rstrip() + "\n"
        footer = (f"\n---\n*Generated from [{rel}]({repo_url}/blob/{branch}/{rel}) in the repository. "
                  "Edit it there: changes made on the wiki are replaced.*\n")
        (out / f"{name}.md").write_text(body + footer, encoding="utf-8")
    home = f"{docs}/{INDEX}"
    side, reached = sidebar((root / home).read_text(encoding="utf-8"), home, pages, docs, extra)
    (out / "_Sidebar.md").write_text(side, encoding="utf-8")
    return len(pages), sorted(set(pages.values()) - set(reached))


def remote_url(root: Path) -> str:
    """The repository's web address from its ``origin`` remote ('' when there is none)."""
    try:
        raw = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    raw = re.sub(r"^git@([^:]+):", r"https://\1/", raw)
    return re.sub(r"\.git$", "", raw)


def push_wiki(out: Path, wiki_url: str, message: str = "Regenerate the wiki from docs/") -> int:
    """Commit the generated pages to the wiki's git repository and push. Only reached when the caller passes ``--push``."""
    with tempfile.TemporaryDirectory() as work:
        clone = Path(work) / "wiki"
        subprocess.run(["git", "clone", "--depth", "1", wiki_url, str(clone)], check=True)
        for old in clone.glob("*.md"):
            old.unlink()
        for page in out.glob("*.md"):
            (clone / page.name).write_text(page.read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["git", "-C", str(clone), "add", "-A"], check=True)
        if not subprocess.run(["git", "-C", str(clone), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip():
            print("the wiki is already current")
            return 0
        subprocess.run(["git", "-C", str(clone), "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", str(clone), "push"], check=True)
    return 0


def run_cli(args: object, root: Path, say=print) -> int:
    """``esoi docs check`` and ``esoi docs wiki``."""
    docs = getattr(args, "docs_dir", "docs")
    if args.action == "check":
        problems = check(root, docs)
        for problem in problems:
            say(problem)
        say("esoi docs ok" if not problems else f"{len(problems)} docs problem(s)")
        return 1 if problems else 0
    url = args.repo_url or remote_url(root)
    if not url:
        say("esoi docs wiki: pass --repo-url (no origin remote to read it from)")
        return 2
    try:
        count, missing = build_wiki(root, Path(args.out), url, args.branch, docs, tuple(args.extra or ()))
    except ValueError as error:
        say(f"esoi docs wiki: {error}")
        return 2
    say(f"wrote {count} page(s) and the sidebar to {args.out}")
    if missing:
        say("not linked from the start page: " + ", ".join(missing))
    if args.push:
        push_wiki(Path(args.out), args.push)
    return 1 if args.check and missing else 0
