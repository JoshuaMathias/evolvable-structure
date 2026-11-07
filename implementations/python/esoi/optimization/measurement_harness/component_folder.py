"""Find the components under the evaluation folder and make their modules importable."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from esoi.structure.intent_registry.config import Config


def imported_from_elsewhere(folder: str, evaluation: Path) -> bool:
    """Whether a component module is already imported from a folder other than this project's evaluation folder."""
    loaded = sys.modules.get(folder)
    where = next(iter(getattr(loaded, "__path__", None) or []), "") if loaded is not None else ""
    return bool(where) and Path(where).resolve().parent != evaluation


def component_folders(evaluation: Optional[Path]) -> List[str]:
    """The names of the folders of the evaluation directory that hold a ``score.py``."""
    if evaluation is None:
        return []
    return sorted(p.name for p in evaluation.iterdir() if p.is_dir() and (p / "score.py").exists())


def prepare_path(config: Config) -> None:
    """Make the repository and the evaluation folder importable (score and impl modules import each other). A component module
    already imported from another project's folder (a process that runs more than one repository) is dropped first, or this
    project's ``<component>.score`` and ``.impls`` would resolve to the other project's files."""
    evaluation = config.evaluation.resolve() if config.evaluation.is_dir() else None
    for folder in component_folders(evaluation):
        if imported_from_elsewhere(folder, evaluation):
            for name in [m for m in sys.modules if m == folder or m.startswith(folder + ".")]:
                sys.modules.pop(name, None)
    for entry in (str(config.evaluation), str(config.root), *(str(config.root / p) for p in config.python_path)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def discover_components(config: Config) -> List[str]:
    """A component is any folder under the evaluation directory with a ``score.py``: adding one needs no edit here."""
    if not config.evaluation.is_dir():
        return []
    return sorted(p.name for p in config.evaluation.iterdir() if (p / "score.py").is_file())
