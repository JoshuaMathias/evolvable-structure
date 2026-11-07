"""Solution coherence of every intent, model-free: the first cascade stage of `metric-solution-coherence`, and rule S38.

Run as ``python3 -m esoi.structure.structure_check.coherence [root] [--json] [--gate] [--pairs]`` from a project. Standard library plus esoi's own config,
intent discovery and records. It reads the records and the package's Python source; it runs nothing and calls no model.

The hierarchy is the ``uses_solution_ids`` of each solution's SELECTED implementation (the composition that runs; a rival's
uses are an alternative, not the structure). Per intent folder:

  paragraph (M1, S38)  solution_coherence is one paragraph that names every solution of the intent and no solution of another
                       intent no edge reaches; it states every uses edge in one clause (split on . ; : ! ?) that names the user
                       before the used with at least MIN_CLAUSE_WORDS words between them that are not solution names (the words that
                       say how one uses the other); no sentence
                       names more than ``max_names_per_sentence`` solutions (default max_fan_out + 1); and when four or more
                       clauses state edges, no more than half of them share one wording once the names are taken out. A clause
                       that opens with "It" speaks of the first solution the clause before it names (so "card-store keeps the
                       cards. It finds them by meaning through index-by-meaning." states card-store -> index-by-meaning). So a
                       list of names, one sentence that names everything, or one template repeated per edge states nothing.
                       What stays unseen (whether the paragraph reads as one line of thought) is the model-judge stage's.
  roots (M5, S38)      the top intent has one root; a sub-intent's roots are used by the implementation it arises from; every
                       solution is reachable from a root
  diagram (M3, S39)    esoi's generated diagram.md is current and every edge is labelled (the provider's outputs is filled)
  code (M2, S39)       for each uses edge whose two ends both have Python modules or owned documents (coverage = checkable / all edges), the
                       strongest evidence the code shows in the user's direction:
                         E1  a module of the user imports a module of the used directly (at module level or lazily inside a function:
                             an import is executable code wherever it stands)                         (strong)
                         E2  executable code of a module of the user names the used's id or its interface class: an
                             identifier, attribute, import, annotation, decorator or call argument, or a string literal used as a
                             value. A docstring, a comment and any bare string statement are prose and never count   (strong)
                         E3  the user's implementation class takes a parameter typed with the used's interface: a need the
                             esoi Assembler injects                                               (strong)
                         E4  a module that components.csv gives only to the user (or to the user among others) imports a module
                             it gives only to the used: the user's code reaches the used through its own module   (strong)
                         E5  a document only the user owns links to or includes a document only the used owns (a markdown link,
                             image, reference definition or include directive; fenced code, inline code, HTML comments, URLs and
                             bare mentions of a path never count). A document is a solution's when a components.csv row names it in
                             its `documents` cell (path=solution-id) or the solution's selected implementation names it as its filepath; a document several
                             solutions own does not say which is meant and counts on neither side    (strong)
                         W1  a module of the user imports one that imports the used               (weak, reported)
                         W2  a module of the user builds an esoi Assembler over a scope that declares the used (weak)
                         W3  a third module imports both ends                                     (weak)
                       Evidence is attributed per solution: in a module several solutions share (one interfaces file holding
                       many arms), a solution's evidence is only what its own classes (declared with ``@implementation`` or
                       ``@solution``) contain, and importing the shared file counts only when the import names the used's class.
                       precision = strong / checkable. The same evidence is scored on every ordered pair of solutions with
                       modules that is NOT a uses edge (the base rate); lift = precision / base rate. A sub-intent's host edges
                       are checked the same way (the host implementation's module against the sub-intent's roots).
  balance (M4, S38)    no implementation uses more than ``max_fan_out`` solutions of its intent; no solution lies more than
                       ``max_depth`` edges below a root

Limits come from the project's esoi.toml ``[rules.S38]``: ``max_fan_out = 9, max_depth = 4``, ``min_lift`` and
``max_names_per_sentence``, and the limits per intent, ``[rules.S38.floors.<intent-id>] precision = .., coverage = ..,
min_lift = .., max_fan_out = .., max_names_per_sentence = ..`` (each defaults to the repository-wide value). An intent that records
no uses edges has an undefined lift, reported as n/a and never failed; the flat
``code_floor`` and ``coverage_floor`` are the floors of an intent with no table of its own. The defaults below apply when absent. ``--gate`` exits 1 unless every intent
passes paragraph, roots, diagram and balance and its precision, coverage and lift are at or above their floors.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry import config as esoi_config
from esoi.structure.intent_registry import intents as esoi_intents
from esoi.structure.structure_check.coherence_code_evidence import Code
from esoi.structure.structure_check.coherence_paragraph import SOLUTION_NAMES, check_paragraph
from esoi.structure.structure_check.coherence_records import ids, read, selected_record

DEFAULTS = {"max_fan_out": 9, "max_depth": 4, "code_floor": 1.0, "coverage_floor": 0.0, "min_lift": 1.0}
STRONG = ("E1", "E2", "E3", "E4", "E5")
WEAK = ("W1", "W2", "W3")


def limits(cfg, intent_id: str = "") -> Dict[str, float]:
    """The limits of one intent: its own ``[rules.S38.floors.<intent-id>]`` table (``precision``, ``coverage``, ``min_lift``,
    ``max_fan_out``, ``max_names_per_sentence``), else the repository-wide values, else the defaults."""
    out = dict(DEFAULTS)
    for key in ("max_fan_out", "max_depth", "min_lift", "code_floor", "coverage_floor"):
        out[key] = cfg.option("S38", key, out[key])
    own = (cfg.option("S38", "floors", {}) or {}).get(intent_id, {})
    if "precision" in own:
        out["code_floor"] = own["precision"]
    if "coverage" in own:
        out["coverage_floor"] = own["coverage"]
    for key in ("min_lift", "max_fan_out"):   # a justified, written limit of one intent; the repository-wide value is the default
        if key in own:
            out[key] = own[key]
    out["max_names_per_sentence"] = own.get("max_names_per_sentence",
                                            cfg.option("S38", "max_names_per_sentence", out["max_fan_out"] + 1))
    return out


@dataclass
class Hierarchy:
    """Every solution and implementation of the repository, where each solution lives, what each selected implementation uses and its code evidence."""
    cfg: object
    every_solution: Dict[str, Dict[str, str]]
    every_impl: List[Dict[str, str]]
    home: Dict[str, str]
    uses: Dict[str, List[str]]
    code: Code

    @property
    def impl_by_id(self) -> Dict[str, Dict[str, str]]:
        return {r["implementation_id"]: r for r in self.every_impl}


def load_hierarchy(cfg) -> Hierarchy:
    """Read the records of every intent folder and the code evidence over them; the solution names feed the paragraph check."""
    every_solution: Dict[str, Dict[str, str]] = {}
    every_impl: List[Dict[str, str]] = []
    home: Dict[str, str] = {}
    for intent_id, folder in esoi_intents.folders(cfg):
        for r in read(folder / "solutions.csv"):
            every_solution[r["solution_id"]] = r
            home[r["solution_id"]] = intent_id
        every_impl += read(folder / "implementations.csv")
    SOLUTION_NAMES.clear()
    SOLUTION_NAMES.update({sid: r.get("name", "") for sid, r in every_solution.items()})
    selected = {sid: selected_record(sid, r, every_impl) for sid, r in every_solution.items()}
    uses = {sid: [t for t in ids(rec.get("uses_solution_ids", "")) if t != sid] for sid, rec in selected.items()}
    components = [r for _, folder in esoi_intents.folders(cfg) for r in read(folder / "components.csv")]
    return Hierarchy(cfg, every_solution, every_impl, home, uses, Code(cfg, every_solution, every_impl, selected, components))


def base_evidence(h: Hierarchy) -> Counter:
    """The evidence found on every ordered pair of solutions with modules that is not a uses edge (the base rate)."""
    edges_all = {(a, b) for a in h.uses for b in h.uses[a] if b in h.every_solution}
    with_code = [s for s in h.every_solution if h.code.modules.get(s)]
    base: Counter = Counter()
    for a in with_code:
        for b in with_code:
            if a != b and (a, b) not in edges_all:
                base[h.code.evidence(a, b)] += 1
    return base


def host_of(h: Hierarchy, intent) -> Tuple[str, Set[str]]:
    """The solution of the implementation a sub-intent arises from, and the solutions that implementation uses."""
    if intent.is_top:
        return "", set()
    host = h.impl_by_id.get(intent.row.get("implements", "").strip(), {})
    return host.get("solution_id", ""), set(ids(host.get("uses_solution_ids", "")))


def root_problems(h: Hierarchy, intent, mine: List[str], inner: Set[Tuple[str, str]], host_uses: Set[str],
                  problems: Dict[str, List[str]]) -> Tuple[List[str], Dict[str, int]]:
    """The roots of an intent and the depth of every solution below them; M5 problems for the wrong roots and for unreachable solutions."""
    used_inside = {b for _, b in inner}
    roots = [s for s in mine if s not in used_inside]
    if intent.is_top and len(roots) != 1:
        problems["roots"].append(f"{len(roots)} roots, the top intent has one: {', '.join(roots)}")
    if not intent.is_top:
        loose = [r for r in roots if r not in host_uses]
        if loose:
            problems["roots"].append(f"roots not used by {intent.row.get('implements')}: {', '.join(loose)}")
    depth = {r: 0 for r in roots}
    stack = list(roots)
    while stack:
        x = stack.pop()
        for t in h.uses[x]:
            if t in mine and depth.get(t, -1) < depth[x] + 1 and depth[x] + 1 <= len(mine):
                depth[t] = depth[x] + 1
                stack.append(t)
    unreached = [s for s in mine if s not in depth]
    if unreached:
        problems["roots"].append(f"unreachable from a root: {', '.join(unreached)}")
    return roots, depth


def diagram_problems(h: Hierarchy, intent, mine: List[str], problems: Dict[str, List[str]]) -> None:
    """M3 problems: an edge whose provider has no outputs label, and a diagram page that is not current."""
    all_edges = {(b, a) for r in h.every_impl if r.get("solution_id") in mine
                 for a in [r["solution_id"]] for b in ids(r.get("uses_solution_ids", "")) if b in mine and b != a}
    unlabelled = sorted({b for b, _ in all_edges if not (h.every_solution[b].get("outputs") or "").strip()})
    if unlabelled:
        problems["diagram"].append(f"edges with no label (the provider's outputs is empty): {', '.join(unlabelled)}")
    try:
        from esoi.understanding.readable_records import diagram as esoi_diagram
        from esoi.structure.intent_registry.registry import load as load_registry
        page = intent.folder / esoi_diagram.FILE
        want_text = esoi_diagram.render(load_registry(h.cfg), intent)
        if want_text and (not page.is_file() or page.read_text(encoding="utf-8") != want_text):
            problems["diagram"].append(f"{page.relative_to(h.cfg.root)} is not current (run `esoi diagram`)")
    except ImportError:
        problems["diagram"].append("this esoi has no `esoi diagram` (template version 4 and later)")


def code_scores(h: Hierarchy, checked: Set[Tuple[str, str]], base_rate: Optional[float], lim: Dict[str, float],
                problems: Dict[str, List[str]]) -> Dict[str, object]:
    """M2: the strongest code evidence of each checked edge, the precision, coverage and lift of an intent, and the problems under the floors."""
    verdicts = {f"{a}->{b}": h.code.evidence(a, b) for a, b in sorted(checked)}
    checkable = {e: v for e, v in verdicts.items() if v != "n/a"}
    strong = [e for e, v in checkable.items() if v in STRONG]
    precision = round(len(strong) / len(checkable), 3) if checkable else None
    coverage = round(len(checkable) / len(verdicts), 3) if verdicts else None
    lift = round(precision / base_rate, 2) if precision is not None and base_rate else None
    if precision is not None and precision < lim["code_floor"]:
        problems["code"].append(f"precision {precision} below the floor {lim['code_floor']}; not shown by strong evidence: "
                                + ", ".join(f"{e} ({v or 'none'})" for e, v in checkable.items() if v not in STRONG))
    if coverage is not None and coverage < lim["coverage_floor"]:
        problems["code"].append(f"coverage {coverage} below the floor {lim['coverage_floor']}: edges with an end that has no code: "
                                + ", ".join(e for e, v in verdicts.items() if v == "n/a"))
    if lift is not None and lift < lim["min_lift"]:
        problems["code"].append(f"lift {lift} below {lim['min_lift']}: the evidence fires on non-edges as often as on edges")
    return dict(verdicts=verdicts, checkable=checkable, strong=strong, precision=precision, coverage=coverage, lift=lift)


def code_recall(h: Hierarchy, mine: List[str]) -> Tuple[int, Optional[float]]:
    """How many import edges the code has between an intent's solutions, and the share that lie on a recorded uses path."""
    reach = {}
    for s in mine:
        out, st = set(), [s]
        while st:
            x = st.pop()
            for t in h.uses.get(x, ()):
                if t not in out:
                    out.add(t)
                    st.append(t)
        reach[s] = out
    code_edges = h.code.import_edges(set(mine))
    on_path = [e for e in code_edges if e[1] in reach[e[0]] or e[0] in reach[e[1]]]
    return len(code_edges), round(len(on_path) / len(code_edges), 3) if code_edges else None


def balance_problems(h: Hierarchy, mine: List[str], depth: Dict[str, int], lim: Dict[str, float],
                     problems: Dict[str, List[str]]) -> Dict[str, int]:
    """M4 problems: a solution that uses too many others or lies too deep. Returns the fan-out of each solution."""
    fan = {s: len([t for t in h.uses[s] if t in mine]) for s in mine}
    wide = [f"{s} ({n})" for s, n in fan.items() if n > lim["max_fan_out"]]
    deep = [f"{s} ({d})" for s, d in depth.items() if d > lim["max_depth"]]
    if wide:
        problems["balance"].append(f"fan-out above {lim['max_fan_out']}: {', '.join(wide)}")
    if deep:
        problems["balance"].append(f"deeper than {lim['max_depth']}: {', '.join(deep)}")
    return fan


def intent_report(h: Hierarchy, intent, base_rate: Optional[float]) -> Dict[str, object]:
    """The coherence report of one intent: paragraph, roots, diagram, code evidence and balance."""
    lim = limits(h.cfg, intent.intent_id)   # the floors of this intent
    mine = sorted(s for s, home in h.home.items() if home == intent.intent_id)
    inner = {(a, b) for a in mine for b in h.uses[a] if b in mine}
    host_sid, host_uses = host_of(h, intent)
    problems: Dict[str, List[str]] = defaultdict(list)
    roots, depth = root_problems(h, intent, mine, inner, host_uses, problems)
    para = (intent.row.get("solution_coherence") or "").strip()
    check_paragraph(para, problems, mine, h.every_solution, h.uses, host_sid, host_uses, inner, lim["max_names_per_sentence"])
    diagram_problems(h, intent, mine, problems)
    checked = set(inner) | ({(host_sid, r) for r in roots if r in host_uses} if host_sid else set())
    scores = code_scores(h, checked, base_rate, lim, problems)
    import_edges, recall = code_recall(h, mine)
    fan = balance_problems(h, mine, depth, lim, problems)
    verdicts = scores["verdicts"]
    return dict(
        intent=intent.intent_id, solutions=len(mine), uses_edges=len(inner), roots=roots,
        max_fan_out=max(fan.values() or [0]), max_depth=max(depth.values() or [0]),
        paragraph_words=len(para.split()), paragraph_ok=not problems["paragraph"] and not problems["roots"],
        diagram_ok=not problems["diagram"], code_edges=len(verdicts), code_edges_checkable=len(scores["checkable"]),
        code_edges_strong=len(scores["strong"]), evidence=dict(Counter(verdicts.values())), code_precision=scores["precision"],
        code_coverage=scores["coverage"], code_lift=scores["lift"],
        code_lift_note="n/a (no recorded edges)" if not verdicts else "", code_import_edges=import_edges,
        code_recall=recall,
        verdicts=verdicts, wide={s: n for s, n in fan.items() if n > lim["max_fan_out"]},
        deep={s: d for s, d in depth.items() if d > lim["max_depth"]}, problems={k: v for k, v in problems.items() if v})


def summarize(report: List[Dict[str, object]], overall: Dict[str, float], base: Counter, base_rate: Optional[float]) -> Dict[str, object]:
    """The repository-wide measures over the reports of every intent."""
    n = len(report) or 1
    return dict(
        intents=len(report), limits=overall, m1_paragraph_share=round(sum(r["paragraph_ok"] for r in report) / n, 3),
        m2_precision=[r["code_precision"] for r in report], m2_coverage=[r["code_coverage"] for r in report],
        m2_base_rate=base_rate, m2_base_pairs=sum(base.values()), m2_base_evidence=dict(base), m2_lift=[r["code_lift"] for r in report],
        m3_diagram_share=round(sum(r["diagram_ok"] for r in report) / n, 3),
        m4_max_fan_out=max([r["max_fan_out"] for r in report] or [0]), m4_max_depth=max([r["max_depth"] for r in report] or [0]),
        roots=sum(len(r["roots"]) for r in report), passed=all(not r["problems"] for r in report))


def check(root: Path, pairs: bool = True) -> Dict[str, object]:
    cfg = esoi_config.load(root)
    overall = limits(cfg)
    found = esoi_intents.discover(cfg)
    h = load_hierarchy(cfg)
    base = base_evidence(h) if pairs else Counter()
    base_n = sum(base.values())
    base_rate = round(sum(base[k] for k in STRONG) / base_n, 3) if base_n else None
    report = [intent_report(h, intent, base_rate) for intent in found]
    return dict(summary=summarize(report, overall, base, base_rate), intents=report)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="esoi.structure.structure_check.coherence", description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate", action="store_true", help="exit 1 unless every intent passes")
    ap.add_argument("--no-pairs", action="store_true", help="skip the base rate over non-edges (faster)")
    args = ap.parse_args(argv)
    out = check(Path(args.root), pairs=not args.no_pairs)
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        for r in out["intents"]:
            print(f"{r['intent']}: {r['solutions']} solutions, {r['uses_edges']} uses edges, roots {len(r['roots'])}, fan-out "
                  f"{r['max_fan_out']}, depth {r['max_depth']}, paragraph {'ok' if r['paragraph_ok'] else 'FAIL'} "
                  f"({r['paragraph_words']} words), diagram {'ok' if r['diagram_ok'] else 'FAIL'}, code: {r['code_edges_strong']} of "
                  f"{r['code_edges_checkable']} checkable edges strong (precision {r['code_precision']}, coverage {r['code_coverage']}, "
                  f"lift {r['code_lift_note'] or r['code_lift']}), evidence {r['evidence']}")
            for k, v in r["problems"].items():
                for line in v:
                    print(f"  {k}: {line}")
        print("summary:", json.dumps(out["summary"]))
    return 1 if args.gate and not out["summary"]["passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
