"""Rules about where files live and which way imports point: S1 to S6 and S13.

S1 coverage, S2 component rows, S3 root, S4 size, S5 docstring, S6 direction, S13 environment-free layers.
"""
from __future__ import annotations

from typing import List, Tuple

from ..tables import glob_re, ids
from .base import Context, RuleGroup
from .modulefacts import Facts

SUMMARIES = {
    "S1": "Every file belongs to exactly one component and every component path glob matches a file.",
    "S2": "Every component row has a role and a layer from the configured set.",
    "S3": "No Python file at the repository root (unless root_python_files is set).",
    "S4": "No Python module over the size ceiling (max_lines); split by role or waive with a reason.",
    "S5": "Every module of the package opens with a docstring that states its role.",
    "S6": "Dependencies point inward: a module imports its own layer or a lower one (TYPE_CHECKING imports ignored).",
    "S13": "A layer (or path prefix) listed in [rules.S13] reads no environment variables; the value is passed in.",
}


def module_imports(facts: Facts, dotted: str, package: str, is_init: bool) -> List[Tuple[int, str]]:
    """(line, top-level name under ``package``) for each import of a module, lazy ones included."""
    parts = dotted.split(".")
    pkg_parts = parts if is_init else parts[:-1]
    found: List[Tuple[int, str]] = []
    for line, level, module, names in facts.imports:
        if level:
            base = pkg_parts[: len(pkg_parts) - (level - 1)]
            full = base + (module.split(".") if module else [])
            from_names = names if not module else []
        else:
            full = (module or "").split(".")
            from_names = []
        if full[:1] == [package] and len(full) > 1:
            found.append((line, full[1]))
        elif full == [package]:
            found.extend((line, n) for n in from_names)
        elif level and len(full) == 1 and not module:
            found.extend((line, n) for n in from_names)
    for line, name in facts.plain:
        p = name.split(".")
        if p[0] == package and len(p) > 1:
            found.append((line, p[1]))
    return found


def run(ctx: Context) -> List[str]:
    bad: List[str] = []
    config = ctx.config
    seen = set()
    for r in ctx.components:
        cid = r["component_id"]
        if cid in seen:
            bad.append(f"S1 {cid}: duplicate component_id")
        seen.add(cid)
        if r["layer"] not in config.component_layers:
            bad.append(f"S2 {cid}: layer {r['layer']!r} not in {sorted(config.component_layers)}")
        if not r["role"].strip():
            bad.append(f"S2 {cid}: column role is empty (state the role the component owns)")
        for p in ids(r["path"]):
            rx = glob_re(p)
            if not any(rx.match(f) for f in ctx.files):
                bad.append(f"S1 {cid}: path pattern {p!r} matches no file")
    for f, owning in ctx.owners.items():
        if not owning:
            bad.append(f"S1 {f}: belongs to no component (add it to {config.structure_dir}/components.csv)")
        elif len(owning) > 1:
            bad.append(f"S1 {f}: belongs to several components {owning}")
    if not config.root_python_files:
        for f in ctx.files:
            if "/" not in f and f.endswith(".py"):
                bad.append(f"S3 {f}: .py file at the repo root (use tests/, scripts/ or the package)")
    parent = config.package_dir.rpartition("/")[0]
    rank = config.layer_rank
    env_layers = set(config.option("S13", "layers", []))
    env_paths = tuple(config.option("S13", "paths", []))
    ctx.cache().prefetch([f for f in ctx.files if f.endswith(".py")])
    for f in ctx.files:
        if not f.endswith(".py"):
            continue
        path = config.root / f
        if not path.exists():
            continue
        facts = ctx.facts(f)
        if facts.lines > config.max_lines and not ctx.waived("S4", f):
            bad.append(f"S4 {f}: {facts.lines} lines (max {config.max_lines}); split by role or add a waiver")
        if not config.package_dir or not f.startswith(config.package_dir + "/"):
            continue
        if any(token in "/" + f for token in config.docstring_exempt):
            continue
        if facts.size and not facts.docstring:
            bad.append(f"S5 {f}: module has no docstring stating its role")
        dotted = f[len(parent) + 1 if parent else 0:-3].replace("/", ".")
        layer = ctx.file_layer.get(f, "")
        for line, top in module_imports(facts, dotted, config.package, path.name == "__init__.py"):
            target = ctx.top_layer(top)
            if layer in rank and target in rank and rank[target] > rank[layer] and not ctx.waived("S6", f"{f}:{top}"):
                bad.append(f"S6 {f}:{line}: {layer} imports {top} ({target}); dependencies point inward")
        if (layer in env_layers or (env_paths and f.startswith(env_paths))) and facts.env \
                and not ctx.waived("S13", f):
            hint = config.option("S13", "hint", "take the value from configuration, built by an outer layer")
            bad.append(f"S13 {f}:{facts.env[0]}: {layer or 'this code'} reads the environment; {hint} (or add a waiver)")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
