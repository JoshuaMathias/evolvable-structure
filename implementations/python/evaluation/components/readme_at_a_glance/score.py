"""Score one intent folder: does its README read at a glance? Model-free checks over the text an arm writes for the folder.

A case passes when every check passes; ``aggregate`` reports how many folders passed each check. The checks (budgets are in
``esoi.understanding.readable_records.readme``): ``vision``, ``coherence`` and ``diagram`` all end inside the first screen; ``solutions`` gives every solution a row
with its one-line entry call and its selected implementation; ``links`` resolve, down to each sub-intent, up to the parent and to the
repository's top README; ``finished`` has no em dash, no unconfirmed marker and no machine path; ``pure`` is the same text when
generated again from a fresh read of the records (nothing hand-kept, no clock); ``size`` keeps the summary above the divider within
its budget with the long record tables below it.
"""
import posixpath
import re
from collections import Counter

import glance_fixture
from esoi.understanding.readable_records import diagram, readme_view

CHECKS = ("vision", "coherence", "diagram", "solutions", "links", "finished", "pure", "size")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")


def window(text):
    """The whole lines that end inside the first screen."""
    kept, total, inside = [], 0, False
    for line in text.splitlines():
        if line.startswith("```"):
            total += 0 if inside else readme_view.DIAGRAM_LINES
            inside = not inside
        elif not inside:
            total += max(1, -(-len(line) // readme_view.WRAP))
        if total > readme_view.FIRST_SCREEN_LINES:
            break
        kept.append(line)
    return "\n".join(kept)


def summary(text):
    return text.split("\n---\n", 1)[0]


def resolves(view, folder, target):
    path = target.partition("#")[0]
    if not path or re.match(r"^[a-z][a-z0-9+.-]*:", path):
        return True
    full = (folder / path).resolve()
    if full.exists():
        return True
    return any(i.folder.resolve() / readme_view.FILE == full for i in view.intents)


def verdicts(text, loaded, view, intent, again):
    vision = readme_view.one_line(intent.row.get("vision_statement", ""))
    coherence = readme_view.one_line(intent.row.get("solution_coherence", ""))
    screen = window(text)
    out = {"vision": not vision or vision in screen, "coherence": not coherence or coherence[:80] in screen}
    block = diagram.block(loaded, intent)
    out["diagram"] = not block or "\n".join(block) in screen
    rows = [r for r in loaded.every_solution() if r.get("intent_id", intent.intent_id) == intent.intent_id]
    package = view.config.package
    good = True
    for r in rows:
        sid = r.get("solution_id", "")
        lines = [ln for ln in text.splitlines() if f"`{sid}`" in ln and ln.startswith("|")]
        call = f'run("{sid}"' if sid in view.declared and (view.declared[sid].entry or view.declared[sid].kind) else (readme_view.recorded_call(r) or "no entry declared")
        picked = readme_view.one_line(r.get("selected", "")) or "none selected"
        good = good and any(call in ln and picked in ln for ln in lines)
    out["solutions"] = good
    targets = [t for t in LINK.findall(text)]
    wanted = [readme_view.link(intent.folder, c.folder / readme_view.FILE) for c in view.intents if c.parent == intent.intent_id]
    parent = view.intent(intent.parent) if intent.parent else None
    if parent is not None:
        wanted.append(readme_view.link(intent.folder, parent.folder / readme_view.FILE))
    if (view.config.root / readme_view.FILE).is_file():
        wanted.append(readme_view.link(intent.folder, view.config.root / readme_view.FILE))
    out["links"] = all(resolves(view, intent.folder, t) for t in targets) and all(w in targets for w in wanted)
    out["finished"] = bool(text) and not re.search(r"\u2014|unconfirmed|TODO|TBD|/home/", text, re.I)
    out["pure"] = bool(text) and text == again
    top = summary(text)
    tables = [ln for ln in top.splitlines() if ln.startswith("| Implementation |") or ln.startswith("| Solution | Name |")]
    out["size"] = bool(text) and readme_view.screen_lines(top) <= readme_view.SUMMARY_LINES and not tables
    return out


def score_case(fn, case):
    args = case["args"]
    try:
        text = fn("page", dict(args, fresh=False))["text"]
        again = fn("page", dict(args, fresh=True))["text"]
        cfg, loaded, view = glance_fixture.load(args["repo"])
        intent = glance_fixture.intent_of(view, args["intent"])
        found = verdicts(text, loaded, view, intent, again)
    except LookupError as exc:
        return dict(ok=False, got="unavailable", note=str(exc))
    failed = [c for c in CHECKS if not found.get(c)]
    return dict(ok=not failed, got=",".join(c for c in CHECKS if found.get(c)), note="ok" if not failed else "fails " + ", ".join(failed))


def aggregate(rows):
    seen = Counter()
    for r in rows:
        for c in (r.get("got") or "").split(","):
            if c in CHECKS:
                seen[c] += 1
    return ", ".join(f"{c} {seen[c]}/{len(rows)}" for c in CHECKS)
