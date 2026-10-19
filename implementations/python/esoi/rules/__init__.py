"""The built-in rule groups, and the loader for a repository's own plugin rules (see ``rules.base``)."""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List

from ..config import Config
from . import generated, intents, layout, measurement, registry_rules
from .base import Context, RuleGroup

BUILTIN: List[RuleGroup] = [layout.GROUP, registry_rules.GROUP, measurement.GROUP, generated.GROUP, intents.GROUP]


def load_plugin(spec: str, root: Path) -> ModuleType:
    """Load a plugin named by a file path (relative to the repository root) or by an importable module name."""
    if spec.endswith(".py"):
        path = Path(spec) if Path(spec).is_absolute() else root / spec
        loader = importlib.util.spec_from_file_location(f"esoi_plugin_{path.stem}", path)
        if loader is None or loader.loader is None:
            raise ImportError(f"cannot load plugin {path}")
        module = importlib.util.module_from_spec(loader)
        sys.modules[loader.name] = module
        sys.path.insert(0, str(path.parent))
        try:
            loader.loader.exec_module(module)
        finally:
            sys.path.remove(str(path.parent))
        return module
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module(spec)


def plugins(config: Config) -> List[ModuleType]:
    return [load_plugin(spec, config.root) for spec in config.plugins]


def all_groups(config: Config) -> List[RuleGroup]:
    groups = list(BUILTIN)
    for module in plugins(config):
        groups.extend(getattr(module, "RULES", []))
    return groups


def summaries(config: Config) -> Dict[str, str]:
    """Every rule id with its one-line statement, built-in and plugin, in id order."""
    out: Dict[str, str] = {}
    for group in all_groups(config):
        out.update(group.summaries)
    return dict(sorted(out.items(), key=lambda kv: (kv[0][0], int(kv[0][1:]) if kv[0][1:].isdigit() else 0)))


__all__ = ["BUILTIN", "Context", "RuleGroup", "all_groups", "load_plugin", "plugins", "summaries"]
