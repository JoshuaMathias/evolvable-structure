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


def spec_prompt_action(config, args: argparse.Namespace) -> int:
    """``esoi spec prompt``: the prompt for one solution's own consideration, formed from its network of records."""
    import json
    from esoi.understanding.solution_consideration import solution_prompt
    if not args.target:
        print("esoi: spec prompt needs a solution id", file=sys.stderr)
        return 2
    network = solution_prompt.load(config, args.with_records or (), stale=not args.no_stale)
    try:
        made = solution_prompt.prompt(network, args.target, args.task, solution_prompt.budget_of(config, args.budget), knowledge=args.knowledge)
    except KeyError:
        print(f"esoi: no solution {args.target!r}", file=sys.stderr)
        return 1
    print(json.dumps(made, indent=1) if args.json else made["text"])
    return 0


def print_consider(found, as_list: bool) -> None:
    """The prompts of ``esoi consider``: one line each with ``--list``, else the JSON."""
    import json
    if not as_list:
        print(json.dumps(found, indent=1))
        return
    for item in found["prompts"]:
        print(f"{item['role']} {item['solution_id']}: {item['name']} ({item['chars']} chars; reached by {', '.join(item['reached_by']) or 'name'})")


def run_consider(config, args: argparse.Namespace) -> int:
    """``esoi consider``: one generated prompt per solution a text concerns, and per parent level, as JSON."""
    from esoi.understanding.solution_consideration import fan_out, solution_prompt
    from esoi.understanding.spec_search import spec_index
    if not args.text and not args.solution:
        print("esoi: consider needs the text of a change, a candidate or a request, or --solution ID", file=sys.stderr)
        return 2
    network = solution_prompt.load(config, args.with_records or (), stale=not args.no_stale)
    unknown = [s for s in args.solution or () if s not in network.solutions]
    if unknown:
        print(f"esoi: no solution {', '.join(unknown)}", file=sys.stderr)
        return 1
    index = spec_index.cached(config, Path(args.cache)) if args.cache else spec_index.build(config)
    print_consider(fan_out.consider(network, index, args.text, args.max, solution_prompt.budget_of(config, args.budget), args.arm,
                                    args.solution or (), args.knowledge), args.list)
    return 0


def knowledge_cards(config, args: argparse.Namespace) -> int:
    """``esoi knowledge cards SOLUTION``: the solution's stable part as a managed card and each knowledge item as a card, as JSON."""
    import json
    from esoi.understanding.solution_consideration import knowledge, solution_prompt
    network = solution_prompt.load(config, stale=False)
    if args.solution not in network.solutions:
        print(f"esoi: no solution {args.solution!r}", file=sys.stderr)
        return 1
    made = solution_prompt.prompt(network, args.solution, "", solution_prompt.budget_of(config, None))
    cards = [knowledge.stable_card(network, args.solution, made["text"])] + [knowledge.item_card(i) for i in made["knowledge"]]
    print(json.dumps({"cards": cards, "quarantine": [knowledge.item_card(i) for i in made["knowledge_inactive"]]}, indent=1))
    return 0


def run_knowledge(config, args: argparse.Namespace) -> int:
    """``esoi knowledge``: add one item, migrate free-text Knowledge cells, list items, or export cards."""
    from esoi.understanding.solution_consideration import knowledge
    if args.action == "cards":
        return knowledge_cards(config, args)
    if args.action == "migrate":
        for line in knowledge.migrate(config, args.apply):
            print(line)
        print("applied" if args.apply else "dry run: add --apply to write")
        return 0
    if args.action == "add":
        try:
            found, created = knowledge.add(config, {"claim": args.claim, "kind": args.kind, "source": args.source,
                                                    "solution_ids": [args.solution] if args.solution else [], "expiration": args.expiration})
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        print(f"{'added' if created else 'already held'} {found}")
        return 0
    for item in knowledge.all_items(config):
        if not args.solution or args.solution in item["solution_ids"]:
            print(knowledge.line(item))
    return 0


def run_spec(config, args: argparse.Namespace) -> int:
    """``esoi spec``: build, search and read the specification index (no model is called)."""
    from esoi.understanding.spec_search import spec_index
    if args.action == "prompt":
        return spec_prompt_action(config, args)
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
    action | choices=index,find,show,related,intent,prompt |
    target | nargs=? default= | find: the words of the use case or input; show, related, prompt: a record id
    -k | type=int default=8 | find: how many records to return
    --expand | type=int default=0 | find: linked records to add per hit
    --tier | type=int default=1 choices=0,1,2 | show: 0 one line, 1 plus summary and links, 2 the full record
    --out | default=None | index: write the JSON here instead of printing it
    --depth | type=int default=1 | related: how many link steps to follow
    --cache | default=None | read the index from this file when the records have not changed, else rebuild it there
    --task | default= | prompt: the change, candidate or request the pass considers
    --budget | type=int default=None | prompt: the size budget in characters (default: [consider] budget, else 24000)
    --with | dest=with_records action=append | prompt: a CSV of findings or candidates to join the prompt (repeatable; esoi.toml [[consider.records]] declares them for good)
    --json | action=store_true | prompt: print the prompt with its sections, what was cut and its knowledge items, as JSON
    --knowledge | default=candidates choices=candidates,ranked,none | prompt: candidates beside the text for your retrieval, ranked into the text, or none
    --no-stale | action=store_true | prompt: skip the check of which results describe older code (faster)
consider | | one generated prompt per solution a change, candidate or request concerns, and per parent level, as JSON
    text | nargs=? default= | the change, candidate or request
    --solution | action=append | name the solution instead of classifying the text (repeatable)
    --max | type=int default=5 | how many relevant solutions to return before their parents
    --arm | default= choices=,index_with_links,lexical_index | the Solution Relevance arm that classifies the text (default: the selected one)
    --budget | type=int default=None | the size budget of each prompt in characters
    --with | dest=with_records action=append | a CSV of findings or candidates to join the prompts (repeatable)
    --list | action=store_true | print one line per prompt instead of the JSON
    --knowledge | default=candidates choices=candidates,ranked,none | knowledge items beside each prompt for your retrieval, ranked into it, or none
    --no-stale | action=store_true | skip the check of which results describe older code (faster)
    --cache | default=None | read the index from this file when the records have not changed, else rebuild it there
knowledge | | knowledge records: one row per piece of knowledge, linked to solutions (knowledge.csv beside problems.csv)
    action | choices=list,add,migrate,cards |
    --solution | default= | list, add: the solution; cards: the solution whose cards to export
    --claim | default= | add: one sentence
    --kind | default= | add: assumption, best guess (the default), evidence, theory, perspective or lesson
    --source | default= | add: result:<component>/<arm>@<date>, url:<address> grade <A-D>, person:<who>, <date>: "<words>", or mistake:<id>
    --expiration | default= | add: the date it must be re-confirmed by (YYYY-MM-DD)
    --apply | action=store_true | migrate: write the rows and replace each Knowledge cell with its ids (a dry run without it)
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
