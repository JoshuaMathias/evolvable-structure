"""``esoi new solution <id>``: one command for everything a new solution needs.

It writes the record rows (problem, ideal, solution, implementation, metric) into the intent folder, the code skeleton
with the declarations (``@solution`` on the interface and ``@implementation`` on a first alternative), and the
evaluation folder (a scorer using the declarative ``expect``, and one example case). The text only a person can write
is left empty, so ``esoi check`` names it; nothing is filled with sample prose. Nothing that exists is overwritten.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from . import declarations, registry as registry_module
from .config import Config
from .records import TEMPLATE_DATA, load_template
from .tables import glob_re, ids, write_csv

IMPLEMENTATION = "simple"
MODULE = '''"""{title}: the interface and its first implementation. Edit both; `esoi records sync` keeps the records in step."""
from esoi import implementation, solution


@solution("{sid}")
def {fn}(value: str) -> str:
    """Say here, in one sentence, what this solution does for its caller."""


@implementation("{sid}", "{impl}")
def {impl}(value: str) -> str:
    """The first and simplest way."""
    return value
'''
SCORE = '''"""Score one {sid} case against its declarative ``expect`` (see ``esoi.expect``)."""
from esoi import expect


def score_case(fn, case):
    return expect.score_kind_case(fn, case)
'''
CASES = '[{"id": "C-1", "kind": "run", "area": "example", "args": {"value": "x"}, "expect": {"eq": {"text": "x"}}}]\n'


def slug(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "-", text.lower()).strip("-")


def create(config: Config, solution_id: str, intent_id: Optional[str] = None) -> List[str]:
    """Create the solution ``solution_id``; returns the files written or changed (repository-relative). Raises
    ``ValueError`` when the id is taken, the package is not configured, or any file it would write exists."""
    sid = slug(solution_id)
    if not sid or not config.package_dir:
        raise ValueError("a solution needs an id and a configured package (`package` in esoi.toml)")
    loaded = registry_module.load(config)
    if sid in {r.get("solution_id") for r in loaded.every_solution()}:
        raise ValueError(f"the solution {sid!r} already exists")
    fn = sid.replace("-", "_")
    module = f"{config.package_dir}/{fn}.py"
    component = f"{config.evaluation_dir}/{fn}"
    taken = [p for p in (module, f"{component}/score.py", f"{component}/cases.json") if (config.root / p).exists()]
    if taken:
        raise ValueError(f"would overwrite {', '.join(taken)}")
    folder = declarations.intent_folder(config, intent_id)
    template = load_template(TEMPLATE_DATA)
    tables = {name: declarations.table_rows(folder, f"{name}.csv", key, template, entity) for name, key, entity in (
        ("problems", "problem_id", "problem"), ("ideals", "ideal_id", "ideal"), ("solutions", "solution_id", "solution"),
        ("implementations", "implementation_id", "implementation"), ("metrics", "metric_id", "metric"))}
    command = f"esoi run {fn} --impl {IMPLEMENTATION}"
    new_rows: Dict[str, Dict[str, str]] = {
        "problems": declarations.blank(tables["problems"][0], problem_id=f"prob-{sid}", solution_ids=sid, ideal_ids=f"ideal-{sid}"),
        "ideals": declarations.blank(tables["ideals"][0], ideal_id=f"ideal-{sid}", problem_ids=f"prob-{sid}"),
        "solutions": declarations.blank(tables["solutions"][0], solution_id=sid, name=declarations.title(sid),
                                        problem_ids=f"prob-{sid}", ideal_ids=f"ideal-{sid}", metric_ids=f"metric-{sid}",
                                        implementations=IMPLEMENTATION, selected=IMPLEMENTATION),
        "implementations": declarations.blank(tables["implementations"][0], implementation_id=f"{sid}:{IMPLEMENTATION}",
                                              solution_id=sid, filepath=module, name=declarations.title(IMPLEMENTATION)),
        "metrics": declarations.blank(tables["metrics"][0], metric_id=f"metric-{sid}", solution_ids=sid, command=command),
    }
    written: List[str] = []
    for name, (columns, rows) in tables.items():
        write_csv(folder / f"{name}.csv", columns, rows + [new_rows[name]])
        written.append(str((folder / f"{name}.csv").relative_to(config.root)))
    columns, rows = declarations.table_rows(folder, "components.csv", "component_id", {}, "component")
    columns = columns if (folder / "components.csv").is_file() else ["component_id", "layer", "path", "role", "solutions"]
    layer = next(iter(config.layer_names), "core")
    extra: List[Dict[str, str]] = []
    for cid, path, where, role in ((fn, f"{config.package_dir}/{fn}.py", module,
                                    f"The {declarations.title(sid).lower()} solution's interface and implementations."),
                                   (f"eval-{fn}", f"{component}/**", f"{component}/score.py", f"Cases and scorer for {sid}.")):
        owners = [r for r in rows if any(glob_re(p).match(where) for p in ids(r.get("path", "")))]
        if not owners:
            extra.append(declarations.blank(columns, component_id=cid, layer="evaluation" if cid.startswith("eval-") else layer,
                                            path=path, role=role, solutions=sid))
        elif sid not in ids(owners[0].get("solutions", "")):
            owners[0]["solutions"] = ";".join(ids(owners[0].get("solutions", "")) + [sid])   # the owning component serves it too
    write_csv(folder / "components.csv", columns, rows + extra)
    written.append(str((folder / "components.csv").relative_to(config.root)))
    files = {module: MODULE.format(title=declarations.title(sid), sid=sid, fn=fn, impl=IMPLEMENTATION),
             f"{component}/__init__.py": "", f"{component}/score.py": SCORE.format(sid=sid), f"{component}/cases.json": CASES}
    for rel, text in files.items():
        path = config.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(rel)
    return written
