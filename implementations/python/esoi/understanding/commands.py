"""The sub-commands of the understanding container: scaffold, skill, docs, readmes, diagrams, tracker, sheet sync, projects and the specification index."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_init(config, args: argparse.Namespace) -> int:
    from esoi.understanding.the_standard.scaffold import init
    init(Path(args.dir), args.package, args.force)
    print("next: write the top intent (the name and vision statement in intent.csv say why your project exists), "
          "git init && git add . && git commit, then `esoi run greet_a_person --impl live --record` and `esoi check --strict`")
    return 0


def run_skill(config, args: argparse.Namespace) -> int:
    from esoi.understanding.the_standard.skill_distribution import skill
    if args.action == "install":
        return skill.install(args.project, args.dest, args.from_dir, args.force)
    if args.action == "sync":
        return skill.sync(config, args.source)
    return skill.check(config, args.source, args.denylist)


def run_docs(config, args: argparse.Namespace) -> int:
    from esoi.understanding.the_standard import docs
    if args.action == "wiki" and not args.out:
        print("esoi docs wiki: pass --out DIR", file=sys.stderr)
        return 2
    return docs.run_cli(args, Path(args.root).resolve())


def run_readmes(config, args: argparse.Namespace) -> int:
    from esoi.understanding.readable_records import readme
    return readme.run_cli(config, args.check)


def run_diagram(config, args: argparse.Namespace) -> int:
    from esoi.understanding.readable_records import diagram
    return diagram.run_cli(config, args.check)


def run_tracker(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import registry
    from esoi.understanding.review_tracker import tracker
    loaded = registry.load(config)
    if args.action == "build":
        tracker.write(config, loaded)
        return 0
    bad = tracker.stale(config, loaded)
    print("tracker out of date: " + ", ".join(bad) if bad else "tracker ok")
    return 1 if bad else 0


def run_sheet_sync(config, args: argparse.Namespace) -> int:
    from esoi.understanding.review_tracker import sheets
    return sheets.run_cli(config, args.mode, args.dry_run)


def run_spec(config, args: argparse.Namespace) -> int:
    """``esoi spec``: build, search and read the specification index (no model is called)."""
    import json
    from esoi.understanding.spec_search import spec_index
    index = spec_index.cached(config, Path(args.cache)) if args.cache else spec_index.build(config)
    if args.action == "intent":
        for entry in spec_index.of_intent(index, args.target):
            print(spec_index.line(entry))
        return 0
    if args.action == "index":
        text = json.dumps(index, indent=1, sort_keys=True) + "\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out} ({index['n']} entries, digest {index['digest']})")
        else:
            print(text, end="")
        return 0
    if not args.target:
        print(f"esoi: spec {args.action} needs a {'record id' if args.action == 'show' else 'use case text'}", file=sys.stderr)
        return 2
    if args.action == "find":
        print(spec_index.render_scan(index, spec_index.find_specs(index, args.target, args.k, args.expand)))
        return 0
    if args.action == "related":
        try:
            hits = spec_index.related(index, args.target, args.depth, max(args.k, 1))
        except KeyError:
            print(f"esoi: no record {args.target!r}", file=sys.stderr)
            return 1
        by_id = {e["id"]: e for e in index["entries"]}
        print("\n".join(f"{spec_index.line(by_id[h['id']])}  (step {h['depth']} via {h['via']})" for h in hits))
        return 0
    try:
        print(spec_index.show(config, index, args.target, args.tier))
    except KeyError:
        print(f"esoi: no record {args.target!r}", file=sys.stderr)
        return 1
    return 0


def run_projects(config, args: argparse.Namespace) -> int:
    """``esoi projects``: the one place the index folder is resolved from ``ESOI_HOME``."""
    import os
    from esoi.understanding.local_application_index import projects
    home = projects.resolve_home(os.environ, Path.home())
    if args.action == "init":
        made = projects.init(home)
        print(f"{home}: " + (", ".join(made) + " created" if made else "already set up"))
        return 0
    if args.action == "add":
        if not args.target:
            print("esoi: projects add needs a path or URL", file=sys.stderr)
            return 2
        try:
            row = projects.add(home, args.target, args.id, args.name, args.vision, args.kind, args.specifications,
                               args.start_here, args.relations, args.notes, args.replace)
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        print(f"added {row['project_id']} ({row['kind']}, {row['location']})")
        if not projects.resolve([row])[0]["vision_statement"]:
            print("note: no vision statement found in the project's top intent.csv; add one there (or with --vision --replace)")
        return 0
    if args.action == "list":
        for line in projects.render_list(projects.resolve(projects.read_projects(home))):
            print(line)
        return 0
    if args.action == "check":
        bad = projects.check(home)
        for line in bad:
            print(line)
        print("esoi projects: " + (f"{len(bad)} problem(s)" if bad else "ok"))
        return 1 if bad else 0
    if args.action == "index":
        print(f"wrote {projects.index(home)}")
        return 0
    found = projects.where(home, Path(args.target or "."))
    if found is None:
        print("no listed project contains that path")
        return 1
    for line in projects.render_where(found):
        print(line)
    return 0


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    p = sub.add_parser("init", help="scaffold a passing example repository")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--package", default="", help="the package name (default: the folder name)")
    p.add_argument("--force", action="store_true", help="overwrite files that exist")
    p.set_defaults(handler=run_init, needs_config=False)
    p = sub.add_parser("skill", help="the public copy of the author's skill")
    p.add_argument("action", choices=["sync", "check", "install"])
    p.add_argument("--source", default=None, help="sync, check: the author's skill folder (else $ESOI_SKILL_SOURCE)")
    p.add_argument("--denylist", default=None, help="check: a file of private terms (else $ESOI_SKILL_DENYLIST)")
    p.add_argument("--project", default=None, help="install: a project folder; the skill goes in its .claude/skills")
    p.add_argument("--dest", default=None, help="install: a skills folder of another agent")
    p.add_argument("--from", dest="from_dir", default=None, help="install: a skill folder to install instead of the bundled one")
    p.add_argument("--force", action="store_true", help="install: replace a different skill already there")
    p.set_defaults(handler=run_skill, needs_config=lambda args: args.action != "install")
    p = sub.add_parser("readmes", help="write the README of every intent folder from its records (at a glance, with the diagram and links)")
    p.add_argument("--check", action="store_true", help="only report the READMEs that are out of date")
    p.set_defaults(handler=run_readmes)
    p = sub.add_parser("diagram", help="draw each intent's solution diagram (Mermaid) from the solutions' outputs and the implementations' dependencies")
    p.add_argument("--check", action="store_true", help="only report the diagrams that are out of date")
    p.set_defaults(handler=run_diagram)
    p = sub.add_parser("tracker", help="the review tracker")
    p.add_argument("action", choices=["build", "check"])
    p.set_defaults(handler=run_tracker)
    p = sub.add_parser("sheet-sync", help="sync the tracker with a Google Sheet")
    p.add_argument("mode", choices=["sync", "push", "pull", "check"])
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(handler=run_sheet_sync)
    p = sub.add_parser("projects", help="the local ESOI index: the projects ESOI is applied to on this machine")
    p.add_argument("action", choices=["init", "add", "list", "check", "index", "where"])
    p.add_argument("target", nargs="?", default=None, help="add: a local path or URL; where: a path (default: the current folder)")
    p.add_argument("--id", default="", help="add: the project id (default: from the name)")
    p.add_argument("--name", default="")
    p.add_argument("--vision", default="", help="add: the vision statement (default: from the project's top intent)")
    p.add_argument("--kind", default="", choices=["", "repository", "folder", "file", "board"])
    p.add_argument("--specifications", default="", help="add: where its ESOI specifications are, relative to the location")
    p.add_argument("--start-here", default="", help="add: the file to read first when applying ESOI there")
    p.add_argument("--relations", default="", help="add: ';'-separated kind:project_id (uses, used-by, sub-intent-of, example-of, related)")
    p.add_argument("--notes", default="")
    p.add_argument("--replace", action="store_true", help="add: update a project that is already listed")
    p.set_defaults(handler=run_projects, needs_config=False)
    p = sub.add_parser("spec", help="the specification index: a deterministic, non-AI map of the records")
    p.add_argument("action", choices=["index", "find", "show", "related", "intent"])
    p.add_argument("target", nargs="?", default="", help="find: the words of the use case or input; show: a record id")
    p.add_argument("-k", type=int, default=8, help="find: how many records to return")
    p.add_argument("--expand", type=int, default=0, help="find: linked records to add per hit")
    p.add_argument("--tier", type=int, default=1, choices=[0, 1, 2], help="show: 0 one line, 1 plus summary and links, 2 the full record")
    p.add_argument("--out", default=None, help="index: write the JSON here instead of printing it")
    p.add_argument("--depth", type=int, default=1, help="related: how many link steps to follow")
    p.add_argument("--cache", default=None, help="read the index from this file when the records have not changed, else rebuild it there")
    p.set_defaults(handler=run_spec)
    p = sub.add_parser("docs", help="the four-category docs standard, and the wiki generated from it")
    p.add_argument("action", choices=["check", "wiki"])
    p.add_argument("--root", default=".")
    p.add_argument("--docs-dir", default="docs")
    p.add_argument("--out", default=None, help="wiki: the folder to write the pages into")
    p.add_argument("--repo-url", default=None, help="wiki: the repository's web address (default: its origin remote)")
    p.add_argument("--branch", default="main")
    p.add_argument("--extra", action="append", help="wiki: a markdown file outside docs/ to include as a page (repeatable)")
    p.add_argument("--check", action="store_true", help="wiki: fail when a page is not linked from the start page")
    p.add_argument("--push", default=None, metavar="WIKI_GIT_URL", help="wiki: commit and push the pages to this wiki repository")
    p.set_defaults(handler=run_docs, needs_config=False)
