"""One configuration per adopting repository: ``esoi.toml`` (top-level keys) or ``[tool.esoi]`` in ``pyproject.toml``.

Every key has a default, so a repository states only what differs. Paths are relative to the folder that holds
the config file (the repository root). Sub-tables (``[rules.S13]``, ``[hermetic]``, ``[consumer]``, ``[sheets]``, ``[skill]``, ``[records]``)
are kept as plain dicts for the module that reads them.

    package = "mylib"                 # the importable package the module rules look at ("" turns them off)
    layers = ["core", "adapters", ["cli", "tools"]]   # inner to outer; a nested list shares one rank
    disable = ["S13"]                 # rule ids that do not apply here
    plugins = ["tools/my_rules.py"]   # extra rules (see esoi.rules)
"""
from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .tables import DEFAULT_METRIC_COMMAND

CONFIG_NAME = "esoi.toml"
TEMPLATE_ENV = "ESOI_TEMPLATE_SOURCE"
DEFAULT_OTHER_LAYERS = ["docs", "evaluation", "examples", "scripts", "tests", "vendor", "prompts"]
# The folder that holds a project's top intent. One place, so renaming the default is one edit. The folder only HOLDS the
# top intent (its intent.csv and its specifications): the top intent itself is the project's own purpose, why the project
# exists, whatever the folder is called.
DEFAULT_STRUCTURE_DIR = "esoi"
# Folders earlier versions used by default, in the order they are looked for when `structure_dir` is not configured.
PREVIOUS_STRUCTURE_DIRS = ("structure", "docs/structure")
SPECIFICATION_FILES = ("intent.csv", "solutions.csv", "problems.csv")


NOTED: Set[Path] = set()   # roots whose fallback note was printed, so a run says it once


class ConfigError(ValueError):
    """The configuration is missing or malformed."""


class ConfigMissing(ConfigError):
    """There is no configuration file at all (a malformed one is a plain ConfigError)."""


@dataclass
class Config:
    """The resolved configuration of one repository."""
    root: Path
    package: str = ""
    package_dir: str = ""
    layers: List[Any] = field(default_factory=list)
    other_layers: List[str] = field(default_factory=lambda: list(DEFAULT_OTHER_LAYERS))
    max_lines: int = 1500
    root_python_files: bool = False
    root_python_allow: List[str] = field(default_factory=list)
    docstring_exempt: List[str] = field(default_factory=lambda: ["/vendor/"])
    structure_dir: str = DEFAULT_STRUCTURE_DIR
    tracker_folder: str = "tracker"   # the generated review tracker, a folder inside structure_dir (never an intent)
    evaluation_dir: str = "evaluation/components"
    results: str = ""
    shared_eval_dirs: List[str] = field(default_factory=lambda: ["__pycache__"])
    code_paths: List[str] = field(default_factory=list)
    metric_command: str = DEFAULT_METRIC_COMMAND
    live_imports: List[str] = field(default_factory=list)
    live_calls: List[str] = field(default_factory=list)
    paid_arms: List[str] = field(default_factory=list)
    prices: Dict[str, Dict[str, float]] = field(default_factory=dict)
    balance: Dict[str, Dict[str, Any]] = field(default_factory=dict)   # per component: weights and budgets of the balanced score (esoi.balance)
    structure_note: str = field(default="", init=False, repr=False)   # set when the folder fell back to a previous default
    selection: Any = ""   # a selection table "path.py:ATTR", or a [selection] table of deployment choices (see selection_table)
    selection_env: Dict[str, Any] = field(default_factory=dict)   # older environment variables per solution id: "VAR" or ["VAR", ...]
    overall: str = ""
    python_path: List[str] = field(default_factory=list)
    cache: bool = True
    templates_dir: str = ""
    excerpts_file: str = ""
    tracker_extra: Dict[str, List[str]] = field(default_factory=dict)
    template_source: str = ""
    template_csv: str = ""
    version_stamp: str = ""   # the generated stamp of the skill and template this library follows (esoi.versioning); only a library sets it
    plugins: List[str] = field(default_factory=list)
    disable: List[str] = field(default_factory=list)
    rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    hermetic: Dict[str, Any] = field(default_factory=dict)
    consumer: Dict[str, Any] = field(default_factory=dict)
    sheets: Dict[str, Any] = field(default_factory=dict)
    hygiene: Dict[str, Any] = field(default_factory=dict)
    skill: Dict[str, Any] = field(default_factory=dict)
    records: Dict[str, Any] = field(default_factory=dict)   # [records] approved_fields: columns the specification's owner approved
    source: Optional[Path] = None

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        self.package_dir = self.package_dir or self.package
        self.results = self.results or f"{self.evaluation_dir}/results.csv"
        self.code_paths = self.code_paths or ([self.package_dir] if self.package_dir else [])
        self.live_imports = self.live_imports or ([self.package] if self.package else [])
        names = self.layer_names
        if len(set(names)) != len(names):
            raise ConfigError("layers lists a layer twice")

    @property
    def approved_fields(self) -> Dict[str, Set[str]]:
        """Columns of each records file that the owner of the specification approved beyond the template, from
        ``[records.approved_fields]`` (``solutions = ["column", ...]``; a key may also be written ``solutions.csv``)."""
        table = self.records.get("approved_fields", {}) if isinstance(self.records, dict) else {}
        out: Dict[str, Set[str]] = {}
        for name, columns in table.items():
            out[name if name.endswith(".csv") else f"{name}.csv"] = {str(c) for c in columns}
        return out

    @property
    def selection_table(self) -> str:
        """The legacy selection table named by ``selection = "path.py:ATTR"``, or by ``table = "..."`` inside a
        ``[selection]`` table; empty when the repository has none."""
        return self.selection if isinstance(self.selection, str) else str(self.selection.get("table", ""))

    @property
    def selection_choices(self) -> Dict[str, str]:
        """The deployment layer of the selection cascade: ``[selection]`` entries ``solution_id = "implementation"``."""
        if isinstance(self.selection, str):
            return {}
        return {str(k): str(v) for k, v in self.selection.items() if k != "table"}

    @property
    def structure(self) -> Path:
        return self.root / self.structure_dir

    @property
    def intent_mode(self) -> bool:
        """Whether the configured folder holds a top intent (an ``intent.csv``) rather than the legacy layout."""
        return (self.structure / "intent.csv").is_file()

    @property
    def evaluation(self) -> Path:
        return self.root / self.evaluation_dir

    @property
    def results_path(self) -> Path:
        return self.root / self.results

    @property
    def tracker_dir(self) -> Path:
        return self.structure / self.tracker_folder

    @property
    def layer_names(self) -> List[str]:
        """Every layer name; an entry of ``layers`` may be a list of names that share one rank."""
        return [n for entry in self.layers for n in ([entry] if isinstance(entry, str) else entry)]

    @property
    def layer_rank(self) -> Dict[str, int]:
        ranks: Dict[str, int] = {}
        for index, entry in enumerate(self.layers):
            for name in ([entry] if isinstance(entry, str) else entry):
                ranks[name] = index
        return ranks

    @property
    def component_layers(self) -> set:
        return set(self.layer_names) | set(self.other_layers)

    def module_path(self, module: str) -> str:
        """The repository-relative file of a dotted module name inside the package (``pkg.a.b`` -> ``pkg/a/b.py``)."""
        if self.package and (module == self.package or module.startswith(self.package + ".")):
            module = self.package_dir.replace("/", ".") + module[len(self.package):]
        return module.replace(".", "/") + ".py"

    def option(self, rule: str, key: str, default: Any = None) -> Any:
        """A per-rule option from ``[rules.<id>]``."""
        return self.rules.get(rule, {}).get(key, default)

    def is_disabled(self, rule: str) -> bool:
        return rule in self.disable

    def template_source_path(self, override: Optional[str] = None) -> Optional[Path]:
        """Where the intent template is read from: an override, ``$ESOI_TEMPLATE_SOURCE``, then ``template_source``."""
        chosen = override or os.environ.get(TEMPLATE_ENV) or self.template_source
        if not chosen:
            return None
        path = Path(chosen).expanduser()
        return path if path.is_absolute() else (self.root / path)


KNOWN = {f for f in Config.__dataclass_fields__} - {"root", "source", "structure_note"}


def holds_specifications(folder: Path) -> bool:
    """Whether a folder holds ESOI records (a prose-only folder that happens to share a name does not count)."""
    return any((folder / name).is_file() for name in SPECIFICATION_FILES)


def resolve_structure_dir(root: Path) -> Tuple[str, str]:
    """(folder, note) for a project whose configuration does not set ``structure_dir``. The default ``esoi`` wins when
    it exists; when it does not and exactly one previous default holds records, that one is used with a note suggesting
    the rename. Two candidates that both hold records are never guessed between: the error names them."""
    root = Path(root)
    previous = [name for name in PREVIOUS_STRUCTURE_DIRS if holds_specifications(root / name)]
    if (root / DEFAULT_STRUCTURE_DIR).is_dir():
        if previous and holds_specifications(root / DEFAULT_STRUCTURE_DIR):
            raise ConfigError(f"both {DEFAULT_STRUCTURE_DIR}/ and {previous[0]}/ hold specifications; set `structure_dir` in the "
                              f"configuration to say which one this project uses")
        return DEFAULT_STRUCTURE_DIR, ""
    if len(previous) > 1:
        raise ConfigError(f"both {previous[0]}/ and {previous[1]}/ hold specifications; set `structure_dir` in the "
                          f"configuration to say which one this project uses")
    if previous:
        return previous[0], (f"note: using {previous[0]}/ (the previous default folder); rename it to the new default with "
                             f"`git mv {previous[0]} {DEFAULT_STRUCTURE_DIR}`, or set `structure_dir = \"{previous[0]}\"` to keep it")
    return DEFAULT_STRUCTURE_DIR, ""


def from_mapping(data: Dict[str, Any], root: Path, source: Optional[Path] = None) -> Config:
    """Build a Config from the parsed TOML table; unknown keys are an error so a typo does not pass silently."""
    unknown = sorted(set(data) - KNOWN)
    if unknown:
        raise ConfigError(f"unknown config key(s): {', '.join(unknown)}")
    note = ""
    if "structure_dir" not in data:
        data = dict(data)
        data["structure_dir"], note = resolve_structure_dir(root)
    config = Config(root=root, source=source, **data)
    config.structure_note = note
    return config


def find(start: Path) -> Optional[Path]:
    """The nearest ``esoi.toml``, or ``pyproject.toml`` with a ``[tool.esoi]`` table, from ``start`` upward."""
    start = Path(start).resolve()
    for folder in [start, *start.parents]:
        if (folder / CONFIG_NAME).is_file():
            return folder / CONFIG_NAME
        pyproject = folder / "pyproject.toml"
        if pyproject.is_file():
            try:
                if "esoi" in tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}):
                    return pyproject
            except tomllib.TOMLDecodeError:
                continue
    return None


def load(path: Optional[Path] = None, start: Optional[Path] = None) -> Config:
    """Load the configuration at ``path`` (a file, or a folder holding one), else the nearest from ``start``."""
    if path is not None:
        path = Path(path)
        if path.is_dir():
            path = find(path) or path / CONFIG_NAME
    else:
        path = find(Path(start or Path.cwd()))
    if path is None or not Path(path).is_file():
        raise ConfigMissing("no esoi.toml (or [tool.esoi] in pyproject.toml) found; run `esoi init` to create one")
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML ({exc})") from exc
    if Path(path).name == "pyproject.toml":
        data = data.get("tool", {}).get("esoi", {})
    config = from_mapping(data, Path(path).resolve().parent, Path(path).resolve())
    if config.structure_note and config.root not in NOTED:
        NOTED.add(config.root)
        print(config.structure_note, file=sys.stderr)
    return config
