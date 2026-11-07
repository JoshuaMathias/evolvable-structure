"""The sub-commands of the understanding container: scaffold, skill, docs, readmes, diagrams, tracker, sheet sync, projects and the specification index."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from esoi import command_table


def run_init(config, args: argparse.Namespace) -> int:
    from esoi.understanding.the_standard.interface import init
    init(Path(args.dir), args.package, args.force)
    print("next: write the top intent (the name and vision statement in intent.csv say why your project exists), "
          "git init && git add . && git commit, then `esoi run greet_a_person --impl live --record` and `esoi check --strict`")
    return 0


def run_skill(config, args: argparse.Namespace) -> int:
    from esoi.understanding.the_standard.skill_distribution.interface import check, install, sync
    if args.action == "install":
        return install(args.project, args.dest, args.from_dir, args.force)
    if args.action == "sync":
        return sync(config, args.source)
    return check(config, args.source, args.denylist)


def run_docs(config, args: argparse.Namespace) -> int:
    from esoi.understanding.the_standard.interface import run_cli
    if args.action == "wiki" and not args.out:
        print("esoi docs wiki: pass --out DIR", file=sys.stderr)
        return 2
    return run_cli(args, Path(args.root).resolve())


def run_readmes(config, args: argparse.Namespace) -> int:
    from esoi.understanding.readable_records.interface import readme_run_cli
    return readme_run_cli(config, args.check)


def run_diagram(config, args: argparse.Namespace) -> int:
    from esoi.understanding.readable_records.interface import diagram_run_cli
    return diagram_run_cli(config, args.check)


def run_tracker(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import registry
    from esoi.understanding.review_tracker.interface import tracker_stale, tracker_write
    loaded = registry.load(config)
    if args.action == "build":
        tracker_write(config, loaded)
        return 0
    bad = tracker_stale(config, loaded)
    print("tracker out of date: " + ", ".join(bad) if bad else "tracker ok")
    return 1 if bad else 0


def run_sheet_sync(config, args: argparse.Namespace) -> int:
    from esoi.understanding.review_tracker.interface import run_cli
    return run_cli(config, args.mode, args.dry_run)


def spec_index_action(args: argparse.Namespace, index) -> int:
    """``esoi spec index``: print the index as JSON, or write it to ``--out``."""
    import json
    text = json.dumps(index, indent=1, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({index['n']} entries, digest {index['digest']})")
    else:
        print(text, end="")
    return 0


def spec_related_action(args: argparse.Namespace, index) -> int:
    """``esoi spec related``: the records linked to a record, with the step and link that reach each."""
    from esoi.understanding.spec_search import spec_index
    try:
        hits = spec_index.related(index, args.target, args.depth, max(args.k, 1))
    except KeyError:
        print(f"esoi: no record {args.target!r}", file=sys.stderr)
        return 1
    by_id = {e["id"]: e for e in index["entries"]}
    print("\n".join(f"{spec_index.line(by_id[h['id']])}  (step {h['depth']} via {h['via']})" for h in hits))
    return 0


def spec_show_action(config, args: argparse.Namespace, index) -> int:
    """``esoi spec show``: one record at the asked tier."""
    from esoi.understanding.spec_search import spec_index
    try:
        print(spec_index.show(config, index, args.target, args.tier))
    except KeyError:
        print(f"esoi: no record {args.target!r}", file=sys.stderr)
        return 1
    return 0


def run_spec(config, args: argparse.Namespace) -> int:
    """``esoi spec``: build, search and read the specification index (no model is called)."""
    from esoi.understanding.spec_search import spec_index
    index = spec_index.cached(config, Path(args.cache)) if args.cache else spec_index.build(config)
    if args.action == "intent":
        for entry in spec_index.of_intent(index, args.target):
            print(spec_index.line(entry))
        return 0
    if args.action == "index":
        return spec_index_action(args, index)
    if not args.target:
        print(f"esoi: spec {args.action} needs a {'record id' if args.action == 'show' else 'use case text'}", file=sys.stderr)
        return 2
    if args.action == "find":
        print(spec_index.render_scan(index, spec_index.find_specs(index, args.target, args.k, args.expand)))
        return 0
    if args.action == "related":
        return spec_related_action(args, index)
    return spec_show_action(config, args, index)


def projects_init(projects, home, args: argparse.Namespace) -> int:
    made = projects.init(home)
    print(f"{home}: " + (", ".join(made) + " created" if made else "already set up"))
    return 0


def projects_add(projects, home, args: argparse.Namespace) -> int:
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


def projects_list(projects, home, args: argparse.Namespace) -> int:
    for line in projects.render_list(projects.resolve(projects.read_projects(home))):
        print(line)
    return 0


def projects_check(projects, home, args: argparse.Namespace) -> int:
    bad = projects.check(home)
    for line in bad:
        print(line)
    print("esoi projects: " + (f"{len(bad)} problem(s)" if bad else "ok"))
    return 1 if bad else 0


def projects_index(projects, home, args: argparse.Namespace) -> int:
    print(f"wrote {projects.index(home)}")
    return 0


def projects_where(projects, home, args: argparse.Namespace) -> int:
    found = projects.where(home, Path(args.target or "."))
    if found is None:
        print("no listed project contains that path")
        return 1
    for line in projects.render_where(found):
        print(line)
    return 0


PROJECT_ACTIONS = {"init": projects_init, "add": projects_add, "list": projects_list, "check": projects_check,
                   "index": projects_index, "where": projects_where}


def run_projects(config, args: argparse.Namespace) -> int:
    """``esoi projects``: the one place the index folder is resolved from ``ESOI_HOME``."""
    import os
    from esoi.understanding.local_application_index.interface import projects
    home = projects.resolve_home(os.environ, Path.home())
    return PROJECT_ACTIONS[args.action](projects, home, args)


TABLE = """
init | needs_config=False | scaffold a passing example repository
    dir | nargs=? default=. |
    --package | default= | the package name (default: the folder name)
    --force | action=store_true | overwrite files that exist
skill | | the public copy of the author's skill
    action | choices=sync,check,install |
    --source | default=None | sync, check: the author's skill folder (else $ESOI_SKILL_SOURCE)
    --denylist | default=None | check: a file of private terms (else $ESOI_SKILL_DENYLIST)
    --project | default=None | install: a project folder; the skill goes in its .claude/skills
    --dest | default=None | install: a skills folder of another agent
    --from | dest=from_dir default=None | install: a skill folder to install instead of the bundled one
    --force | action=store_true | install: replace a different skill already there
readmes | | write the README of every intent folder from its records (at a glance, with the diagram and links)
    --check | action=store_true | only report the READMEs that are out of date
diagram | | draw each intent's solution diagram (Mermaid) from the solutions' outputs and the implementations' dependencies
    --check | action=store_true | only report the diagrams that are out of date
tracker | | the review tracker
    action | choices=build,check |
sheet-sync | | sync the tracker with a Google Sheet
    mode | choices=sync,push,pull,check |
    --dry-run | action=store_true |
projects | needs_config=False | the local ESOI index: the projects ESOI is applied to on this machine
    action | choices=init,add,list,check,index,where |
    target | nargs=? default=None | add: a local path or URL; where: a path (default: the current folder)
    --id | default= | add: the project id (default: from the name)
    --name | default= |
    --vision | default= | add: the vision statement (default: from the project's top intent)
    --kind | default= choices=,repository,folder,file,board |
    --specifications | default= | add: where its ESOI specifications are, relative to the location
    --start-here | default= | add: the file to read first when applying ESOI there
    --relations | default= | add: ';'-separated kind:project_id (uses, used-by, sub-intent-of, example-of, related)
    --notes | default= |
    --replace | action=store_true | add: update a project that is already listed
spec | | the specification index: a deterministic, non-AI map of the records
    action | choices=index,find,show,related,intent |
    target | nargs=? default= | find: the words of the use case or input; show: a record id
    -k | type=int default=8 | find: how many records to return
    --expand | type=int default=0 | find: linked records to add per hit
    --tier | type=int default=1 choices=0,1,2 | show: 0 one line, 1 plus summary and links, 2 the full record
    --out | default=None | index: write the JSON here instead of printing it
    --depth | type=int default=1 | related: how many link steps to follow
    --cache | default=None | read the index from this file when the records have not changed, else rebuild it there
docs | needs_config=False | the four-category docs standard, and the wiki generated from it
    action | choices=check,wiki |
    --root | default=. |
    --docs-dir | default=docs |
    --out | default=None | wiki: the folder to write the pages into
    --repo-url | default=None | wiki: the repository's web address (default: its origin remote)
    --branch | default=main |
    --extra | action=append | wiki: a markdown file outside docs/ to include as a page (repeatable)
    --check | action=store_true | wiki: fail when a page is not linked from the start page
    --push | default=None metavar=WIKI_GIT_URL | wiki: commit and push the pages to this wiki repository
"""


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    command_table.register(sub, TABLE, globals(), {"skill": {"needs_config": lambda args: args.action != "install"}})
