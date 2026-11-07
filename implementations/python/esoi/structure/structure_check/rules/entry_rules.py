"""Rules S36 to S39, opt-in and advisory: the solution a repository implements, the one-line entry, coherence, and the ratchet.

They apply only in the intent layout (an ``intent.csv`` in the structure folder), and only where the project's ``esoi.toml`` has
``[rules.S3x] enabled = true``. Their findings never fail ``esoi check``: each says its next action, and ``esoi check --findings``
lists them with a count per rule. A waiver (``waivers.csv``) excuses one key; rule S9 reports a waiver that no longer excuses
anything, and S39 shows whether the waiver sets grew.

S36  network: the top intent's one root solution is the solution the repository implements; it names at least one problem and
     one ideal, an authoritative metric, and at least two implementations; every other problem, ideal and metric of the top intent
     reaches the root's through parent_problem_ids, parent_ideal_ids or parent_metric_ids; and each problem, ideal and metric linked
     to the root has real text (not empty, not its own id, not the library's ``unconfirmed:`` marker alone).
S37  entry: every solution with an implementation in the package's code names in ``interface_name`` a class or function declared
     with ``@solution(<id>, kind=..., entry=..., example=...)``; every declared solution and every intent answers its one line
     offline (ok, or pending on a key or an install: ``python3 -m esoi.runtime.assemble_by_name.entry_cli``); the README's first example that calls
     ``<package>.run(`` runs (and, with ``[rules.S37] installed = true``, from an installed wheel).
S38  coherence: every intent passes metric-solution-coherence's first stage (``esoi.structure.structure_check.coherence``): paragraph, roots, diagram, code
     precision, coverage and lift at the floors of ``[rules.S38]`` (per intent in ``[rules.S38.floors.<intent-id>]``), fan-out and depth.
S39  ratchet: the trend of the waiver sets, the enabled rules and the floors and ceilings against a base commit (``esoi.structure.structure_check.ratchet``).
S50  flow first: the intent's paragraph says how its solutions fit, and the flow it describes is written first, in the medium of the
     implementation (here, for code: the entry-point calls from each solution to the ones it uses). It informs when a solution the records
     say is used has an implementation but no caller shows it (nothing in the code of any solution that uses it imports, types or names
     it: evidence E1 to E5 of ``esoi.structure.structure_check.coherence``), and when some other stated edge has no call in the code yet. Only code is read; the
     principle covers documents, processes and organisations too (``docs/how-to/start-from-the-flow.md``).
"""
from __future__ import annotations

import ast
import hashlib
import json
import re as regex
import os
import subprocess
import sys
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry import intents
from esoi.runtime.implementation_selection.declare import KINDS
from esoi.structure.intent_registry.tables import ids
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S36": "Opt-in network: the top intent's one root solution is the solution the repository implements (a problem, an ideal, an "
           "authoritative metric and at least two implementations), every problem, ideal and metric of the top intent links up to "
           "it, and each linked record has real text (waive as the record id).",
    "S37": "Opt-in entry: a solution with code declares @solution(<id>, kind=, entry=, example=) and names it in interface_name; "
           "every declared solution and every intent answers its one line offline (python3 -m esoi.runtime.assemble_by_name.entry_cli); the README's first "
           "example that calls <package>.run( runs (waive as the solution or intent id, or README.md).",
    "S38": "Opt-in coherence: every intent passes python3 -m esoi.structure.structure_check.coherence: paragraph both ways, roots, diagram, code precision, "
           "coverage and lift at the [rules.S38] floors (per intent), fan-out and depth (waive as the intent id).",
    "S50": "Opt-in flow first (advisory): every solution the records say is used has a caller in the code (an import, a typed need or a name "
           "in the code of a solution that uses it), and every stated edge is called; informs where the flow is not written yet (code is read; the principle is general) "
           "(waive as the solution id, or intent id:solution id for an edge).",
    "S39": "Opt-in ratchet: the trend of the waiver sets, the enabled rules and the S38 floors and ceilings against a base commit "
           "(shown, never a failure).",
}


def solution_declaration(node, rel: str, deco) -> Optional[Tuple[str, Dict[str, object]]]:
    """``(solution id, its declaration)`` when ``deco`` is ``@solution("id", ...)`` on ``node``, else None."""
    if not (isinstance(deco, ast.Call) and getattr(deco.func, "id", getattr(deco.func, "attr", "")) == "solution"
            and deco.args and isinstance(deco.args[0], ast.Constant)):
        return None
    keywords = {k.arg: k.value for k in deco.keywords}
    return str(deco.args[0].value), dict(
        name=node.name, file=rel, is_class=isinstance(node, ast.ClassDef),
        kind=keywords["kind"].value if isinstance(keywords.get("kind"), ast.Constant) else "",
        entry=keywords["entry"].value if isinstance(keywords.get("entry"), ast.Constant) else "",
        example="example" in keywords,
        methods={n.name for n in getattr(node, "body", []) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))},
        bases=[ast.unparse(b) for b in getattr(node, "bases", [])])


def declarations(ctx: Context) -> Dict[str, Dict[str, object]]:
    """``{solution id: {name, kind, entry, example, is_class, methods, bases}}`` for every @solution in the measured code."""
    from esoi.structure.intent_registry.specify_from_code import declarations as declared_module
    out: Dict[str, Dict[str, object]] = {}
    measured = set(declared_module.code_files(ctx.config))
    for rel in ctx.files:
        if rel not in measured or not rel.endswith(".py"):
            continue
        tree = tree_of(ctx.root / rel)
        if tree is None:
            continue
        for node in nodes_of(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                found = [solution_declaration(node, rel, deco) for deco in node.decorator_list]
                out.update(f for f in found if f is not None)
    return out


TEXT_FIELD = {"problem": "problem", "ideal": "principle", "metric": "purpose"}   # the main text field of each record kind
MARKER = regex.compile(r"^\s*unconfirmed:\s*(for\b.*\bto confirm\.?)?\s*$", regex.I | regex.S)   # the placeholder the library itself writes


def real_text(row: Dict[str, str], field: str, own_id: str) -> bool:
    """Whether a record's main text says something: not empty, not its own id, not only the library's unconfirmed marker."""
    text = (row.get(field) or "").strip()
    return bool(text) and text != own_id and not MARKER.match(text)


def first_twelve(items: List[str]) -> str:
    """The first twelve ids comma-joined, with an ellipsis when there are more."""
    return ", ".join(items[:12]) + ("..." if len(items) > 12 else "")


def links_up(table: Dict[str, Dict[str, str]], column: str, goal: Set[str], start: str) -> bool:
    """Whether following ``column`` from ``start`` reaches one of the goal ids."""
    seen, stack = set(), [start]
    while stack:
        x = stack.pop()
        if x in goal:
            return True
        if x in seen:
            continue
        seen.add(x)
        stack += ids(table.get(x, {}).get(column, ""))
    return False


@dataclass(frozen=True)
class Chain:
    """One kind of record and the column that links it up: its table by id, the column, and the root's ids that count as the goal."""
    entity: str
    table: Dict[str, Dict[str, str]]
    column: str
    goal: Set[str]


def linked_up_problems(ctx: Context, top, sid: str, chain: Chain) -> List[str]:
    """S36 for the records of one kind that do not link up to the root's through ``column``, or link up with no real text."""
    entity, table, column, goal = chain.entity, chain.table, chain.column, chain.goal
    def reaches(start: str) -> bool:
        return links_up(table, column, goal, start)
    bad: List[str] = []
    loose = [rid for rid in table if not reaches(rid) and not ctx.waived("S36", rid)]
    if loose:
        bad.append(f"S36 {top.intent_id}: {len(loose)} {entity}(s) do not link up to {sid}'s through {column}: "
                   f"{first_twelve(loose)}; next: set {column} on each to the id of the root's {entity}")
    linked = [rid for rid in table if rid in goal or reaches(rid)]
    thin = [rid for rid in linked if not real_text(table[rid], TEXT_FIELD[entity], rid) and not ctx.waived("S36", rid)]
    if thin:
        bad.append(f"S36 {top.intent_id}: {len(thin)} {entity}(s) linked to {sid}'s have no real {TEXT_FIELD[entity]} text "
                   f"(empty, its own id, or only an unconfirmed marker): {first_twelve(thin)}; "
                   f"next: write the {TEXT_FIELD[entity]} from what the project owner decided")
    return bad


def root_solutions(ctx: Context, solutions: Dict[str, Dict[str, str]]) -> List[str]:
    """The solutions of the top intent that no other solution uses, through the selected implementation's `uses_solution_ids`."""
    from esoi.runtime.implementation_selection.select import default_name
    implementations = ctx.registry.implementations
    uses: Dict[str, List[str]] = {}
    for sid, row in solutions.items():
        chosen = (default_name(row, implementations) or "").lower()
        record = next((r for r in implementations if r.get("solution_id") == sid
                       and r["implementation_id"].split(":", 1)[-1].lower() == chosen), {})
        uses[sid] = [t for t in ids(record.get("uses_solution_ids", "")) if t in solutions and t != sid]
    used = {t for v in uses.values() for t in v}
    return [s for s in solutions if s not in used]


def authoritative_metric(root: Dict[str, str], metrics: Dict[str, Dict[str, str]]) -> str:
    """The root solution's authoritative metric: the one it names, else the first metric that measures it."""
    sid = root["solution_id"]
    return (root.get("authoritative_metric_id") or "").strip() or next((m for m, r in metrics.items() if sid in ids(r.get("solution_ids", ""))), "")


def many_roots_line(top, roots: List[str]) -> str:
    """The S36 line for a top intent whose solutions do not have exactly one root."""
    return (f"S36 {top.intent_id}: {len(roots)} root solutions; the solution the repository implements is the one root "
            f"of its top intent ({', '.join(roots[:8])}{'...' if len(roots) > 8 else ''}); next: make one solution the "
            "one the others are used by, through uses_solution_ids")


def root_lacks(ctx: Context, sid: str, problems: List[str], ideals: List[str], metric) -> List[str]:
    """What the root solution still lacks: a problem, an ideal, an authoritative metric, a second implementation."""
    arms = [r for r in ctx.registry.implementations if r.get("solution_id") == sid]
    return [what for what, ok in (("a problem", problems), ("an ideal", ideals), ("an authoritative metric", metric),
                                  ("an alternative implementation beside the selected one", len(arms) >= 2)) if not ok]


def overall_network(ctx: Context) -> List[str]:
    found = [i for i in intents.discover(ctx.config) if i.is_top]
    if not found:
        return []
    top = found[0]

    def mine(rows):
        return [r for r in rows if r.get("intent_id", top.intent_id) == top.intent_id]
    solutions = {r["solution_id"]: r for r in mine(ctx.registry.authored())}
    roots = root_solutions(ctx, solutions)
    if len(roots) != 1:
        return [] if ctx.waived("S36", top.intent_id) else [many_roots_line(top, roots)]
    return root_network_problems(ctx, top, solutions[roots[0]], mine)


def root_network_problems(ctx: Context, top, root: Dict[str, str], mine) -> List[str]:
    """S36 for the one root solution: what it lacks, and the problems, ideals and metrics that do not link up to it."""
    bad: List[str] = []
    sid = root["solution_id"]
    problems, ideals = ids(root.get("problem_ids", "")), ids(root.get("ideal_ids", ""))
    metrics = {r["metric_id"]: r for r in mine(ctx.registry.metrics)}
    metric = authoritative_metric(root, metrics)
    lacking = root_lacks(ctx, sid, problems, ideals, metric)
    if lacking and not ctx.waived("S36", sid):
        bad.append(f"S36 {sid}: the solution this repository implements lacks {'; '.join(lacking)}; next: add it to the records of {sid}")
    for entity, rows, key, column, goal in (
            ("problem", mine(ctx.registry.problems), "problem_id", "parent_problem_ids", set(problems)),
            ("ideal", mine(ctx.registry.ideals), "ideal_id", "parent_ideal_ids", set(ideals)),
            ("metric", list(metrics.values()), "metric_id", "parent_metric_ids", {metric} if metric else set())):
        bad += linked_up_problems(ctx, top, sid, Chain(entity, {r[key]: r for r in rows}, column, goal))
    return bad


def interface_problems(row: Dict[str, str], names: List[str], found: Dict[str, object]) -> List[str]:
    """What is wrong with the @solution declaration of a solution that has code."""
    problems = []
    if found["name"] not in names:
        problems.append(f"interface_name is {row.get('interface_name', '')!r}, not {found['name']}")
    if found["kind"] not in KINDS and (found["is_class"] or found["kind"]):
        problems.append(f"kind= is {found['kind']!r}, not one of {', '.join(KINDS)}")
    problems += entry_problems(found)
    if not found["example"]:
        problems.append("no example= input")
    return problems


def entry_problems(found: Dict[str, object]) -> List[str]:
    """What is wrong with the entry= method a class-based @solution names."""
    if not found["is_class"]:
        return []
    if not found["entry"]:
        return ["no entry= method"]
    if found["entry"] not in found["methods"] and not [b for b in found["bases"] if "Protocol" not in b]:
        return [f"entry {found['entry']!r} is not a method of {found['name']}"]
    return []


def in_package_code(record: Dict[str, str], package_dir: str, evaluation: str) -> bool:
    """Whether an implementation record points at a Python file of the package that is not evaluation code."""
    path = record.get("filepath") or ""
    return path.split("::")[0].endswith(".py") and path.startswith(package_dir) and not path.startswith(evaluation)


def interfaces(ctx: Context) -> List[str]:
    config = ctx.config
    declared = declarations(ctx)
    package_dir = (config.package_dir or "").rstrip("/") + "/"
    evaluation = (config.evaluation_dir or "").rstrip("/") + "/"
    bad: List[str] = []
    for row in ctx.every_solution():
        sid = row.get("solution_id", "")
        in_code = [r for r in ctx.registry.implementations if r.get("solution_id") == sid and in_package_code(r, package_dir, evaluation)]
        if in_code and not ctx.waived("S37", sid):
            bad += interface_finding(row, sid, in_code[0]["filepath"], declared.get(sid))
    return bad


def interface_finding(row: Dict[str, str], sid: str, filepath: str, found: Optional[Dict[str, object]]) -> List[str]:
    """The S37 line for one solution that has code: undeclared, or declared with problems; empty when sound."""
    names = ids(row.get("interface_name", ""))
    if found is None:
        return [f"S37 {sid}: has code ({filepath}) but no @solution({sid!r}, kind=, entry=, example=) declares "
                f"its interface{' (interface_name says ' + ', '.join(names) + ', which no @solution declares)' if names else ''}; next: "
                f"declare it where it lives"]
    problems = interface_problems(row, names, found)
    return [f"S37 {sid}: {found['file']}: " + "; ".join(problems) + "; next: fix the @solution declaration"] if problems else []


def child_json(ctx: Context, args: List[str]) -> object:
    """Run ``python3 -m <args>`` in the project root in a child process with the project's python path; parse its JSON."""
    env = dict(os.environ)
    paths = [str(ctx.root / p) for p in (ctx.config.python_path or ["."])] + [str(Path(__file__).resolve().parents[4])]
    env["PYTHONPATH"] = os.pathsep.join(paths + [env.get("PYTHONPATH", "")])
    done = subprocess.run([sys.executable, "-m", *args, "--json", str(ctx.root)], cwd=ctx.root, env=env, capture_output=True,
                          text=True, timeout=float(ctx.config.option("S37", "timeout", 600)))
    try:
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (done.stderr or done.stdout)[-400:]}


INSIDE = "ESOI_IN_ENTRY_CHECK"   # set while an entry check runs: a structure check started by an entry skips the entry checks
FAILING = ("needs-option", "load-error", "live-attempt", "no-entry", "fail")   # the outcomes of an id that does not answer
NEXT = {"needs-option": "give its default arm what it needs so the line runs with no options, or declare the option as a requirement",
        "load-error": "make the arm importable (or declare the missing package as a requirement of the arm)",
        "live-attempt": "declare the program or service the arm calls as a requirement (so the line is pending) or fix the arm",
        "no-entry": "declare @solution(id, kind=, entry=, example=)", "fail": "fix the entry so the example returns a value of its kind"}


def skip_inside(ctx: Context, rule: str) -> bool:
    """Inside an entry check the rule is not run (it would start the check again); its waivers count as used, not stale."""
    if not os.environ.get(INSIDE):
        return False
    ctx.used_waivers.update((rule, w["path"]) for w in ctx.registry.waivers if w["rule"] == rule)
    return True


def imported_package_names(ctx: Context) -> set:
    """The top-level names the project's own package imports."""
    wanted: set = set()
    package_dir = (ctx.config.package_dir or "").rstrip("/") + "/"
    for rel in ctx.files:
        if rel.startswith(package_dir) and rel.endswith(".py"):
            wanted |= top_level_imports(tree_of(ctx.root / rel))
    return wanted


def top_level_imports(tree) -> set:
    """The top-level package names one syntax tree imports (none for a file that did not parse)."""
    wanted: set = set()
    for node in nodes_of(tree) if tree is not None else []:
        if isinstance(node, ast.Import):
            wanted.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            wanted.add(node.module.split(".")[0])
    return wanted


def esoi_user_folder(name: str, search: List[str]) -> Optional[Path]:
    """The folder of an importable package that itself uses esoi, else None."""
    import importlib.machinery
    try:
        spec = importlib.machinery.PathFinder.find_spec(name, search)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin or not spec.origin.endswith("__init__.py"):
        return None
    folder = Path(spec.origin).resolve().parent
    try:
        return folder if "esoi" in folder.joinpath("__init__.py").read_text(encoding="utf-8", errors="replace") else None
    except OSError:
        return None


def chain_digest(ctx: Context) -> str:
    """A digest of what an entry check reads beyond the project's own files: the esoi library, and every package the project
    imports that itself uses esoi (the parent hubs of an Assembler chain), by file path, size and modification time."""
    if ctx.chain:
        return ctx.chain
    found = {Path(__file__).resolve().parents[3]}
    search = [str(ctx.root / p) for p in (ctx.config.python_path or ["."])] + sys.path
    for name in sorted(imported_package_names(ctx) - {ctx.config.package, "esoi"} - set(sys.stdlib_module_names)):
        folder = esoi_user_folder(name, search)
        if folder is not None:
            found.add(folder)
    digest = hashlib.sha1()
    for folder in sorted(found):
        for file in sorted(folder.rglob("*.py")):
            if "__pycache__" not in file.parts:
                stat = file.stat()
                digest.update(f"{file}:{stat.st_size}:{stat.st_mtime_ns};".encode())
    ctx.chain = digest.hexdigest()   # both entry checks of one run share it
    return ctx.chain


def memo_globs(ctx: Context, *extra: str) -> List[str]:
    return [f"{ctx.config.package_dir}/**", f"{ctx.config.structure_dir}/**", *extra]


def entries(ctx: Context) -> List[str]:
    if skip_inside(ctx, "S37"):
        return []
    rows = ctx.memo("S37-entries", memo_globs(ctx), lambda: child_json(ctx, ["esoi.runtime.assemble_by_name.entry_cli"]), extra=chain_digest(ctx))
    if isinstance(rows, dict):
        return [f"S37 {ctx.config.package or '.'}: the entry check did not run: {rows.get('error', '')}"]
    return [f"S37 {r['id']}: {r['outcome']} ({r['detail'][:160]}); next: {NEXT[r['outcome']]}" for r in rows
            if r["outcome"] in FAILING and (r["level"] == "intent" or r["kind"]) and not ctx.waived("S37", r["id"])]


def readme(ctx: Context) -> List[str]:
    if skip_inside(ctx, "S37") or ctx.waived("S37", "README.md"):
        return []
    args = ["esoi.runtime.assemble_by_name.entry_cli", "--readme"] + (["--installed"] if ctx.config.option("S37", "installed", False) else [])
    found = ctx.memo("S37-readme" + ("-installed" if len(args) > 2 else ""), memo_globs(ctx, "README.md", "pyproject.toml",
                     "**/pyproject.toml"), lambda: child_json(ctx, args), extra=chain_digest(ctx))
    if "error" in found:
        return [f"S37 README.md: the README check did not run: {found['error']}"]
    return [f"S37 {line}; next: make the README's example match what the call returns" for line in found.get("problems", [])]


def start_background(ctx: Context) -> None:
    """Start the two S37 child-process checks (every id's one line, and the README example) before the other rules run. Each waits on a child
    process that does its own reading, so they run beside the rules that read this process's files, and ``run`` collects them in their order."""
    if not ctx.config.intent_mode or not ctx.config.enabled("S37") or os.environ.get(INSIDE):
        return
    pool = ThreadPoolExecutor(max_workers=2)
    ctx.background = {"entries": pool.submit(entries, ctx), "readme": pool.submit(readme, ctx)}
    pool.shutdown(wait=False)


def collected(name: str, part):
    """The findings of a part started by ``start_background``, waited for here (a part that was not started runs now)."""
    def finding(ctx: Context) -> List[str]:
        started = ctx.background.get(name)
        return started.result() if started is not None else part(ctx)
    return finding


def coherence(ctx: Context) -> List[str]:
    from esoi.structure.structure_check import coherence as coherence_module
    report = coherence_module.check(ctx.root)
    bad: List[str] = []
    for r in report["intents"]:
        if ctx.waived("S38", r["intent"]):
            continue
        for part in ("paragraph", "roots", "diagram", "code", "balance"):
            for line in r["problems"].get(part, []):
                bad.append(f"S38 {r['intent']}: {part}: {line[:300]}; next: {NEXT_COHERENCE[part]}")
    return bad


NEXT_COHERENCE = {"paragraph": "edit the intent's solution_coherence so each uses edge reads user first and each stated relation is recorded",
                  "roots": "make one solution the root and let it use the rest (uses_solution_ids)",
                  "diagram": "run `esoi check --write-docs`", "code": "type the composition in code (import or inject the used interface) or lower the claim in the records",
                  "balance": "group solutions so no implementation uses more than max_fan_out"}


def edge_callers(verdicts: Dict[str, str], strong) -> Tuple[Dict[str, List[str]], List[str]]:
    """For each used solution the users whose edge shows strong evidence, and the edges whose evidence is not strong."""
    callers: Dict[str, List[str]] = {}
    unseen: List[str] = []
    for edge, evidence in sorted(verdicts.items()):
        user, _, used = edge.partition("->")
        if evidence == "n/a" or not used:
            continue
        callers.setdefault(used, [])
        if evidence in strong:
            callers[used].append(user)
        else:
            unseen.append(edge)
    return callers, unseen


def intent_flow_lines(r: Dict[str, object], waived) -> List[str]:
    """S50 lines for one intent of a coherence report."""
    from esoi.structure.structure_check.coherence import STRONG
    out: List[str] = []
    callers, unseen = edge_callers(r.get("verdicts", {}), STRONG)
    for used, who in sorted(callers.items()):
        if not who and not waived(used) and not waived(f"{r['intent']}:{used}"):
            users = ", ".join(sorted(e.partition("->")[0] for e in unseen if e.endswith("->" + used)))
            out.append(f"S50 {used}: it has an implementation, but no caller shows in the flow of {r['intent']} (the code of {users} neither imports, "
                       "types nor names it); next: write the flow first (here, a call through its entry point from the solution that uses it) "
                       "(docs/how-to/start-from-the-flow.md)")
    rest = [e for e in unseen if callers.get(e.partition("->")[2]) and not waived(f"{r['intent']}:{e}")]
    if rest:
        out.append(f"S50 {r['intent']}: {len(rest)} stated edge(s) are not called in the code yet: {', '.join(rest[:8])}"
                   f"{' and more' if len(rest) > 8 else ''}; next: write the flow first (in code, function definitions and calls of solution functions), "
                   "then the implementations it reaches")
    return out


def flow_lines(report, waived=lambda key: False) -> List[str]:
    """S50 lines from a coherence report: solutions with an implementation but no caller in the flow, and stated edges nothing calls."""
    return [line for r in report["intents"] for line in intent_flow_lines(r, waived)]


def flow(ctx: Context) -> List[str]:
    from esoi.structure.structure_check import coherence as coherence_module
    return flow_lines(coherence_module.check(ctx.root, pairs=False), lambda key: ctx.waived("S50", key))


def ratchet(ctx: Context) -> List[str]:
    """The trend against the base commit. Every moved item is listed with its direction; none of it fails a check."""
    from esoi.structure.structure_check import ratchet as ratchet_module
    moves, note = ratchet_module.trend(ctx.config)
    if note:
        return [f"S39 {note}"]
    return [t.line() + ("; next: " + ("restore the rule or floor" if "floor" in t.what or "rule" in t.what or "ceiling" in t.what
                                       else "close the new waiver by fixing what it excuses")
                        if t.adverse else "") for t in moves if t.direction != "unchanged"]


def run(ctx: Context) -> List[str]:
    """The findings of the enabled opt-in rules go to ``ctx.advisory`` (to do, with the next action); none is a problem."""
    if not ctx.config.intent_mode:
        return []
    for rule, parts in (("S36", (overall_network,)), ("S37", (interfaces, collected("entries", entries), collected("readme", readme))), ("S38", (coherence,)), ("S39", (ratchet,)), ("S50", (flow,))):
        if ctx.config.enabled(rule):
            for part in parts:
                ctx.advisory.extend(part(ctx))
    return []


GROUP = RuleGroup(SUMMARIES, run)
