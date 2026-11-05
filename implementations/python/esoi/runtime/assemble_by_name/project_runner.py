"""Find the one-line entry of a project: its package's ``run``, its ``assembler()``, or an Assembler over its records."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Callable

from esoi.runtime.assemble_by_name.assemble import Assembler
from esoi.runtime.assemble_by_name.entry import own_runner, runner
from esoi.structure.intent_registry import config as config_module


def project_runner(root: Path) -> Callable[..., Any]:
    """The one-line entry of the project at ``root``: its package's ``run`` (bound by ``runner``), else its ``assembler()``,
    else an Assembler over the package's records; esoi's own repository uses ``esoi.run``."""
    cfg = config_module.load(root / "esoi.toml")
    for extra in reversed([str(root / p) for p in (cfg.python_path or ["."])]):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    if cfg.package == "esoi":
        return own_runner()
    module = importlib.import_module(cfg.package)
    bound = getattr(module, "run", None)
    if callable(bound) and getattr(bound, "assembler", None) is not None:
        return bound
    if callable(getattr(module, "assembler", None)):
        return runner(module.assembler())
    return runner(Assembler(cfg.package, root / cfg.package_dir, records=root))
