"""Rules about where files live and which way imports point: S1 to S6 and S13.

S1 coverage, S2 component rows, S3 root, S4 size, S5 docstring, S6 direction, S13 environment-free layers.
"""
from __future__ import annotations

from typing import List, Tuple

from esoi.structure.intent_registry.tables import document_entries, glob_re, ids
from esoi.structure.structure_check.rules.base import Context, RuleGroup
from esoi.structure.structure_check.rules.modulefacts import Facts

SUMMARIES = {
    "S1": "Every file belongs to exactly one component and every component path glob matches a file; a document named in `documents` is a file of that component and has one owning solution.",
    "S2": "Every component row has a role and a layer from the configured set.",
    "S3": "No Python file at the repository root (unless root_python_files is set, the file is listed in "
          "root_python_allow, or a waiver names it).",
    "S4": "No Python module over the size ceiling (max_lines); split by role or waive with a reason.",
    "S5": "Every module of the package opens with a docstring that states its role.",
    "S6": "Dependencies point inward: a module imports its own layer or a lower one (TYPE_CHECKING imports ignored).",
    "S13": "A layer (or path prefix) listed in [rules.S13] reads no environment variables; the value is passed in.",
}


def resolve_import(level: int, module: str, names, pkg_parts: List[str]) -> Tuple[List[str], list]:
    """The dotted parts an import names (a relative one resolved against the module's package) and the imported names that stand for modules."""
    if level:
        base = pkg_parts[: len(pkg_parts) - (level - 1)]
        return base + (module.split(".") if module else []), (names if not module else [])
    return (module or "").split("."), []


def module_imports(facts: Facts, dotted: str, package: str, is_init: bool) -> List[Tuple[int, str]]:
    """(line, top-level name under ``package``) for each import of a module, lazy ones included."""
    parts = dotted.split(".")
    pkg_parts = parts if is_init else parts[:-1]
    found: List[Tuple[int, str]] = []
    for line, level, module, names in facts.imports:
        full, from_names = resolve_import(level, module, names, pkg_parts)
        if full[:1] == [package] and len(full) > 1:
            found.append((line, full[1]))
        elif full == [package] or (level and len(full) == 1 and not module):
            found.extend((line, n) for n in from_names)
    for line, name in facts.plain:
        p = name.split(".")
        if p[0] == package and len(p) > 1:
            found.append((line, p[1]))
    return found


def component_row_problems(ctx: Context) -> List[str]:
    """S1 duplicate ids and patterns that match no file; S2 layer and role of each component row."""
    bad: List[str] = []
    seen = set()
    for r in ctx.components:
        cid = r["component_id"]
        if cid in seen:
            bad.append(f"S1 {cid}: duplicate component_id")
        seen.add(cid)
        if r["layer"] not in ctx.config.component_layers:
            bad.append(f"S2 {cid}: layer {r['layer']!r} not in {sorted(ctx.config.component_layers)}")
        if not r["role"].strip():
            bad.append(f"S2 {cid}: column role is empty (state the role the component owns)")
        for p in ids(r["path"]):
            rx = glob_re(p)
            if not any(rx.match(f) for f in ctx.files):
                bad.append(f"S1 {cid}: path pattern {p!r} matches no file")
    return bad


def document_problems(ctx: Context) -> List[str]:
    """S1 for each `documents` entry: it has one owning solution that exists, and is a file the component owns."""
    bad: List[str] = []
    sol_ids = {r["solution_id"] for r in ctx.every_solution()}
    document_owner: dict = {}
    for r in ctx.components:
        patterns = [glob_re(p) for p in ids(r["path"])]
        for path, solution in document_entries(r.get("documents", "")):
            where = f"S1 {r['component_id']}: documents entry {path!r}"
            if not solution:
                bad.append(f"{where} has no owner (write path=solution-id)")
            elif solution not in sol_ids:
                bad.append(f"{where}: solution {solution!r} is not in solutions.csv")
            if path not in ctx.files:
                bad.append(f"{where} is not a file of the repository")
            elif not any(rx.match(path) for rx in patterns):
                bad.append(f"{where} is not matched by this component's path (the component owns the file, `documents` names whose it is)")
            if path in document_owner and document_owner[path] != solution:
                bad.append(f"{where} is owned by two solutions ({document_owner[path]}, {solution}); a document has one owner")
            document_owner.setdefault(path, solution)
    return bad


def ownership_problems(ctx: Context) -> List[str]:
    """S1 for a file no component or several components own; S3 for a Python file at the repository root."""
    bad: List[str] = []
    config = ctx.config
    for f, owning in ctx.owners.items():
        if not owning:
            bad.append(f"S1 {f}: belongs to no component (add it to {config.structure_dir}/components.csv)")
        elif len(owning) > 1:
            bad.append(f"S1 {f}: belongs to several components {owning}")
    if not config.root_python_files:
        for f in ctx.files:
            if "/" not in f and f.endswith(".py") and f not in config.root_python_allow and not ctx.waived("S3", f):
                bad.append(f"S3 {f}: .py file at the repo root (use tests/, scripts/ or the package)")
    return bad


def direction_problems(ctx: Context, f: str, facts: Facts, layer: str) -> List[str]:
    """S6 for each import of a module that points outward, to a layer above its own."""
    config = ctx.config
    rank = config.layer_rank
    parent = config.package_dir.rpartition("/")[0]
    dotted = f[len(parent) + 1 if parent else 0:-3].replace("/", ".")
    bad: List[str] = []
    for line, top in module_imports(facts, dotted, config.package, (config.root / f).name == "__init__.py"):
        target = ctx.top_layer(top)
        if layer in rank and target in rank and rank[target] > rank[layer] and not ctx.waived("S6", f"{f}:{top}"):
            bad.append(f"S6 {f}:{line}: {layer} imports {top} ({target}); dependencies point inward")
    return bad


def environment_problems(ctx: Context, f: str, facts: Facts, layer: str) -> List[str]:
    """S13 for a module of an environment-free layer or path that reads the environment."""
    config = ctx.config
    env_layers = set(config.option("S13", "layers", []))
    env_paths = tuple(config.option("S13", "paths", []))
    if (layer in env_layers or (env_paths and f.startswith(env_paths))) and facts.env and not ctx.waived("S13", f):
        hint = config.option("S13", "hint", "take the value from configuration, built by an outer layer")
        return [f"S13 {f}:{facts.env[0]}: {layer or 'this code'} reads the environment; {hint} (or add a waiver)"]
    return []


def module_problems(ctx: Context, f: str) -> List[str]:
    """S4 size, S5 docstring, S6 direction and S13 environment reads of one Python file."""
    bad: List[str] = []
    config = ctx.config
    facts = ctx.facts(f)
    if facts.lines > config.max_lines and not ctx.waived("S4", f):
        bad.append(f"S4 {f}: {facts.lines} lines (max {config.max_lines}); split by role or add a waiver")
    if not config.package_dir or not f.startswith(config.package_dir + "/"):
        return bad
    if any(token in "/" + f for token in config.docstring_exempt):
        return bad
    if facts.size and not facts.docstring:
        bad.append(f"S5 {f}: module has no docstring stating its role")
    layer = ctx.file_layer.get(f, "")
    return bad + direction_problems(ctx, f, facts, layer) + environment_problems(ctx, f, facts, layer)


def run(ctx: Context) -> List[str]:
    bad = component_row_problems(ctx) + document_problems(ctx) + ownership_problems(ctx)
    ctx.cache().prefetch([f for f in ctx.files if f.endswith(".py")])
    for f in ctx.files:
        if f.endswith(".py") and (ctx.config.root / f).exists():
            bad += module_problems(ctx, f)
    return bad


GROUP = RuleGroup(SUMMARIES, run)
