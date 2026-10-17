"""QAR's own rule: S15, every environment variable the package reads is documented in docs/configuration.md.

This is the one structure rule that stays in quest-ai-runner, because it depends on QAR's naming convention
(``QAR_*``) and on its generated configuration page. It sits beside ``env_vars.py`` (the scanner QAR keeps) in
``scripts/`` and is named in ``esoi.toml`` as a plugin.
"""
from pathlib import Path

import env_vars
from esoi.rules.base import Context, RuleGroup


def env_docs(ctx: Context) -> list:
    root = Path(ctx.root)
    doc_path = root / "docs" / "configuration.md"
    doc_text = doc_path.read_text() if doc_path.exists() else ""
    described = env_vars.descriptions(root)
    bad = []
    for var, where in env_vars.env_vars_in_code(root).items():
        if ctx.waived("S15", var):
            continue
        if f"`{var}`" not in doc_text:
            bad.append(f"S15 {var}: read in {where[0]} but missing from docs/configuration.md "
                       "(run `esoi check --write-docs`)")
        elif var not in described and "| - |" in next(
                (ln for ln in doc_text.splitlines() if ln.startswith(f"| `{var}` |")), ""):
            bad.append(f"S15 {var}: read in {where[0]} but explained nowhere; add a line to "
                       "docs/structure/env_descriptions.csv")
    if env_vars.without_explained_in(doc_text) != env_vars.without_explained_in(env_vars.render_env_doc(root)):
        bad.append("S15 docs/configuration.md: out of date (run `esoi check --write-docs`)")
    return bad


def write_docs(ctx: Context) -> None:
    (Path(ctx.root) / "docs" / "configuration.md").write_text(env_vars.render_env_doc(Path(ctx.root)))


RULES = [RuleGroup({"S15": "Every environment variable read in the package is a row of docs/configuration.md "
                           "(generated from the code, described in env_descriptions.csv)."}, env_docs)]
