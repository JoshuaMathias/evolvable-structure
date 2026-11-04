"""What an implementation needs from its environment, declared as data beside the arm and checked, reported and turned into files.

An arm (a class or function that implements a solution) attaches its needs with a ``REQUIRES`` attribute::

    from esoi.requirements import api, env, python

    @implementation("literature-search", "openalex")
    class OpenAlex:
        REQUIRES = (
            api("OpenAlex", key=env("OPENALEX_API_KEY", option="api_key", secret=True), keyless=True,
                signup_url="https://openalex.org/settings/api", free_tier="free key, higher daily limit", as_of="2026-10"),
            python("requests", "requests"),
        )

The vocabulary is ``env``, ``api``, ``python``, ``binary``, ``service``, ``network``, ``download`` and ``resource``. The older
``ENVIRON = {option: variable}`` and ``ENVIRON_REQUIRED`` attributes keep working and are read as env requirements.
``check`` says per requirement whether it is met, unmet or unknown, with one remedy line, and touches no network unless asked
to ``probe``. ``Assembler.requirements`` reports the needs of exactly the arms an assembly uses; ``env_template``,
``install_script`` and ``report`` turn them into the generated files and the text report. These are code declarations, not
fields of the ESOI records. Only variable names ever appear in output, never values.
"""
from __future__ import annotations

import ast
import collections
import importlib
import importlib.util
import importlib.metadata
import inspect
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

MET, UNMET, UNKNOWN = "met", "unmet", "unknown"
NETWORK_REMEDY = "needs network access; not attempted offline"
REQUIRES_ATTRIBUTE = "REQUIRES"
BLOCKING_KINDS = ("env", "api", "python", "binary", "network")   # an unmet required one of these keeps an arm pending
OFFLINE_ENV = "ESOI_OFFLINE"   # "1": no network and no model process; a network requirement is unmet while it is set
PROBE_SECONDS = 3.0
SCHEMA = "esoi.requirements/1"   # the "schema" field of the JSON output; a field is only ever added within a version
EXIT_MET, EXIT_UNMET, EXIT_ERROR = 0, 1, 2   # the exit codes of esoi requirements --check and esoi install


@dataclass(frozen=True)
class Requirement:
    """Common part of every kind. ``required`` False means the arm still works without it."""
    kind: str = ""
    required: bool = True
    note: str = ""

    @property
    def label(self) -> str:
        return self.kind


@dataclass(frozen=True)
class Env(Requirement):
    """A variable. ``also`` lists alternative names of which any one suffices; ``option`` is the constructor option it fills;
    ``group`` joins variables of which any one is enough across separate declarations."""
    kind: str = "env"
    name: str = ""
    option: Optional[str] = None
    secret: bool = False
    also: Tuple[str, ...] = ()
    group: str = ""

    @property
    def names(self) -> Tuple[str, ...]:
        return (self.name,) + self.also

    @property
    def label(self) -> str:
        return "env " + " or ".join(self.names)


@dataclass(frozen=True)
class Api(Requirement):
    """An external API: the account or key it needs, whether a keyless path exists, the official links and the arm author's
    dated statements of its free tier and rate limit. ``probe_url`` is an optional cheap GET used only by ``probe=True``."""
    kind: str = "api"
    service: str = ""
    key: Optional[Env] = None
    keyless: bool = False
    signup_url: str = ""
    docs_url: str = ""
    pricing_url: str = ""
    free_tier: str = ""
    rate_limit: str = ""
    as_of: str = ""
    probe_url: str = ""

    @property
    def label(self) -> str:
        return "api " + self.service


@dataclass(frozen=True)
class Python(Requirement):
    """An importable module and the pip requirement that provides it (``extra`` is the owning package's extra)."""
    kind: str = "python"
    module: str = ""
    distribution: str = ""
    extra: Optional[str] = None
    alternatives: Tuple[str, ...] = ()

    @property
    def parsed(self) -> "Parsed":
        return parse_requirement(self.distribution, self.extra)

    @property
    def pip_spec(self) -> str:
        """The pip requirement with the owning package's extra (the environment marker, if any, is kept)."""
        found = self.parsed
        return found.spec() + (f"; {found.marker}" if found.marker else "")

    @property
    def label(self) -> str:
        return "python " + self.module


@dataclass(frozen=True)
class Binary(Requirement):
    """An executable on PATH; ``version_args`` (for example ``("--version",)``) is what ``probe=True`` runs."""
    kind: str = "binary"
    name: str = ""
    install_hint: str = ""
    version_args: Optional[Tuple[str, ...]] = None

    @property
    def label(self) -> str:
        return "binary " + self.name


@dataclass(frozen=True)
class Service(Requirement):
    """A running service. The address comes from ``url_env`` or ``default_url``; ``health_path`` is what ``probe=True`` fetches."""
    kind: str = "service"
    name: str = ""
    url_env: str = ""
    default_url: Optional[str] = None
    health_path: Optional[str] = None

    @property
    def label(self) -> str:
        return "service " + self.name


@dataclass(frozen=True)
class Network(Requirement):
    """The arm reaches the network (``host`` names where, for the reader). It is met unless ``ESOI_OFFLINE=1``, in which case it is
    unmet and the arm is pending (the seat is never built, so nothing is attempted)."""
    kind: str = "network"
    host: str = ""

    @property
    def label(self) -> str:
        return "network " + self.host if self.host else "network"


@dataclass(frozen=True)
class Download(Requirement):
    """Model weights or data fetched on first use. Informational: never blocks."""
    kind: str = "download"
    name: str = ""
    size_mb: float = 0
    cache_hint: str = ""

    @property
    def label(self) -> str:
        return "download " + self.name


@dataclass(frozen=True)
class Resource(Requirement):
    """CPU, GPU, memory or time notes. Informational: never blocks."""
    kind: str = "resource"

    @property
    def label(self) -> str:
        return "resource " + self.note


@dataclass(frozen=True)
class ScriptFile(Requirement):
    """The shell-level escape hatch: a ``requirements.txt``, ``install.sh`` or ``install.py`` found beside an implementation file
    (``<stem>.requirements.txt`` and so on), or in its folder when the file is ``__init__.py`` or named for the folder. Prefer a
    code declaration; use a file only for what code cannot express. ``role`` is ``requirements``, ``shell`` or ``python``."""
    kind: str = "file"
    path: str = ""
    role: str = ""

    @property
    def label(self) -> str:
        return f"{self.role} file {Path(self.path).name}"


SCRIPT_ROLES = (("install.sh", "shell"), ("requirements.txt", "requirements"), ("install.py", "python"))   # the order they run in


@dataclass(frozen=True)
class Parsed:
    """A pip requirement string taken apart: ``name[extras]specifier; marker``."""
    name: str
    extras: Tuple[str, ...] = ()
    specifier: str = ""
    marker: str = ""

    @property
    def key(self) -> str:
        return re.sub(r"[-_.]+", "-", self.name).lower()

    def spec(self) -> str:
        return self.name + (f"[{','.join(sorted(self.extras))}]" if self.extras else "") + self.specifier


REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[([^\]]*)\])?\s*([^;]*?)\s*(?:;\s*(.*?))?\s*$")


def parse_requirement(text: str, extra: Optional[str] = None) -> Parsed:
    """``name[extras]specifier; marker`` from a distribution string plus the owning package's ``extra``. An unparseable string
    keeps its text as the name so pip reports it."""
    found = REQUIREMENT.match(text or "")
    if not found:
        return Parsed(text.strip(), (extra,) if extra else ())
    extras = [one.strip() for one in (found.group(2) or "").split(",") if one.strip()] + ([extra] if extra else [])
    return Parsed(found.group(1), tuple(dict.fromkeys(extras)), (found.group(3) or "").replace(" ", ""), found.group(4) or "")


def packaging_parts() -> Optional[Tuple[Any, Any]]:
    """``(SpecifierSet, Marker)`` from ``packaging`` when it is installed, else None."""
    try:
        from packaging.markers import Marker
        from packaging.specifiers import SpecifierSet
        return SpecifierSet, Marker
    except ImportError:
        return None


def marker_applies(marker: str) -> bool:
    """Whether an environment marker (``python_version``, ``sys_platform``, ...) holds here; true when it cannot be evaluated."""
    parts = packaging_parts()
    if not marker or parts is None:
        return True
    try:
        return bool(parts[1](marker).evaluate())
    except Exception:
        return True


def env(name: str, option: Optional[str] = None, required: bool = True, secret: bool = False, also: Sequence[str] = (),
        group: str = "", note: str = "") -> Env:
    """A variable, optionally filling a constructor option. ``also``: alternative variable names, any one suffices."""
    return Env(required=required, note=note, name=name, option=option, secret=secret, also=tuple(also), group=group)


def api(service: str, key: Optional[Env] = None, keyless: bool = False, signup_url: str = "", docs_url: str = "",
        pricing_url: str = "", free_tier: str = "", rate_limit: str = "", as_of: str = "", probe_url: str = "",
        required: bool = True, note: str = "") -> Api:
    """An external API. With ``keyless=True`` the arm works without the key (only better with one)."""
    return Api(required=required, note=note, service=service, key=key, keyless=keyless, signup_url=signup_url, docs_url=docs_url,
               pricing_url=pricing_url, free_tier=free_tier, rate_limit=rate_limit, as_of=as_of, probe_url=probe_url)


def python(module: str, distribution: str, extra: Optional[str] = None, required: bool = True,
           alternatives: Sequence[str] = ()) -> Python:
    """An importable module and the distribution (with the owning package's extra) that provides it. ``distribution`` may carry
    a version range (``requests>=2.31``) and a marker (``; python_version>='3.9'``). ``alternatives`` are other requirement
    strings that provide the same module (another distribution, or a wider tested range), tried when the first cannot coexist."""
    return Python(required=required, module=module, distribution=distribution, extra=extra, alternatives=tuple(alternatives))


@dataclass(frozen=True)
class Isolate(Requirement):
    """The arm can run out of process (``boundary``: ``subprocess``, ``cli`` or ``mcp``), so its python requirements may be
    installed in a virtual environment of their own when they cannot coexist with the rest."""
    kind: str = "isolate"
    boundary: str = ""

    @property
    def label(self) -> str:
        return f"isolatable via {self.boundary}"


def isolatable(boundary: str) -> Isolate:
    """Declare that the arm is reached through a process boundary (``subprocess``, ``cli`` or ``mcp``) and may be isolated."""
    return Isolate(required=False, boundary=boundary)


def binary(name: str, install_hint: str = "", version_args: Optional[Sequence[str]] = None, required: bool = True) -> Binary:
    """An executable on PATH."""
    return Binary(required=required, name=name, install_hint=install_hint, version_args=tuple(version_args) if version_args else None)


def service(name: str, url_env: str, default_url: Optional[str] = None, health_path: Optional[str] = None, required: bool = True) -> Service:
    """A running service (a vector database, a search engine) addressed by ``url_env``."""
    return Service(required=required, name=name, url_env=url_env, default_url=default_url, health_path=health_path)


def network(host: str = "", required: bool = True, note: str = "") -> Network:
    """The arm needs network access (``network("openalex.org")``). Under ``ESOI_OFFLINE=1`` it is pending: "needs network access;
    not attempted offline"."""
    return Network(required=required, note=note, host=host)


def download(name: str, size_mb: float = 0, cache_hint: str = "") -> Download:
    """Model weights or data fetched on first use."""
    return Download(required=False, name=name, size_mb=size_mb, cache_hint=cache_hint)


def resource(note: str) -> Resource:
    """A CPU, GPU, memory or time note."""
    return Resource(required=False, note=note)


# declaration

def declared(target: Any) -> Tuple[Requirement, ...]:
    """Every requirement an arm declares: its ``REQUIRES`` and its ``ENVIRON`` / ``ENVIRON_REQUIRED`` read as env requirements
    (a variable an api requirement already owns is not repeated)."""
    found: List[Requirement] = []
    for item in getattr(target, REQUIRES_ATTRIBUTE, ()) or ():
        if not isinstance(item, Requirement):
            raise TypeError(f"{getattr(target, '__qualname__', target)!r}: REQUIRES holds {item!r}, not a requirement; use env(), api(), ...")
        found.append(item)
    found.extend(script_files(target))
    owned = {name for item in found if isinstance(item, Api) and item.key for name in item.key.names}
    declared_env = getattr(target, "ENVIRON", None)
    if isinstance(declared_env, Mapping):
        groups: Dict[str, str] = {}
        required: set = set()
        for entry in getattr(target, "ENVIRON_REQUIRED", ()) or ():
            options = (entry,) if isinstance(entry, str) else tuple(entry)
            required.update(options)
            if len(options) > 1:
                groups.update({option: "|".join(options) for option in options})
        for option, names in declared_env.items():
            names = (names,) if isinstance(names, str) else tuple(names)
            if not names or names[0] in owned:
                continue
            found.append(Env(required=option in required, name=names[0], option=option, also=names[1:], group=groups.get(option, "")))
    return tuple(found)


@dataclass(frozen=True)
class Entry:
    """A requirement and who uses it (``solution:arm`` labels), once however many arms declare it."""
    requirement: Requirement
    used_by: Tuple[str, ...] = ()


def source_path(obj: Any) -> Optional[Path]:
    """The source file of a module, class or function (of its class for an instance); None when it has none."""
    try:
        if isinstance(obj, ModuleType):
            raw = getattr(obj, "__file__", None)
        else:
            raw = inspect.getsourcefile(obj if inspect.isclass(obj) or inspect.isroutine(obj) else type(obj))
    except (TypeError, OSError):
        return None
    return Path(raw).resolve() if raw else None


def script_files(obj: Any) -> List[ScriptFile]:
    """The per-implementation files for ``obj``: beside its file as ``<stem>.<name>``, and in the folder when the file is
    ``__init__.py`` or has the folder's name. In the order they run: install.sh, requirements.txt, install.py."""
    path = source_path(obj)
    if path is None:
        return []
    found: List[ScriptFile] = []
    for name, role in SCRIPT_ROLES:
        beside = path.parent / f"{path.stem}.{name}"
        inside = path.parent / name
        for candidate in ([beside] + ([inside] if path.stem in ("__init__", path.parent.name) else [])):
            if candidate.is_file() and not any(one.path == str(candidate) for one in found):
                found.append(ScriptFile(required=False, path=str(candidate), role=role))
    return found


def imported_names(tree: ast.AST, module: ModuleType, path: Path, notes: List[str]) -> List[str]:
    """The dotted module names ``tree`` imports, sorted (a deterministic walk). Relative imports are resolved against
    ``module``; ``importlib.import_module(x)`` and ``__import__(x)`` with a computed argument are noted as not followed."""
    package = module.__name__ if path.name == "__init__.py" else module.__name__.rpartition(".")[0]
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                parts = parts[: max(len(parts) - (node.level - 1), 0)]
                base = ".".join(parts + ([base] if base else []))
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Call):
            callee = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if callee in ("import_module", "__import__") and node.args:
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    names.add(argument.value)
                else:
                    notes.append(f"{module.__name__} line {node.lineno}: dynamic import not followed; declare what it needs with REQUIRES")
    return sorted(name for name in names if name)


def walk_imports(start: ModuleType, notes: Optional[List[str]] = None) -> List[ModuleType]:
    """``start`` and every module of the same top-level package it imports, recursively and in a deterministic order (an ``ast``
    walk of the source, like a dependency lister: an import inside a function counts). An import cycle terminates and is noted.
    A module that cannot be read, parsed or imported is noted as unknown with the reason, never raised."""
    notes = notes if notes is not None else []
    top = start.__name__.split(".")[0]
    seen: Dict[str, ModuleType] = {start.__name__: start}
    edges: Dict[str, List[str]] = {}
    queue = collections.deque([start])
    while queue:
        module = queue.popleft()
        path = source_path(module)
        if path is None or path.suffix != ".py":
            if module is start and path is not None:
                notes.append(f"{module.__name__}: not Python source, imports not followed")
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as error:
            notes.append(f"{module.__name__}: unknown, cannot parse {path.name} ({type(error).__name__}: {error})")
            continue
        edges[module.__name__] = []
        for name in imported_names(tree, module, path, notes):
            if name.split(".")[0] != top:
                continue
            if name in seen:
                edges[module.__name__].append(name)
                continue
            try:
                if importlib.util.find_spec(name) is None:
                    continue
            except (ImportError, ValueError, AttributeError):
                continue   # not a module (for example a name imported from a module): nothing to follow
            try:
                found = importlib.import_module(name)
            except Exception as error:   # reported, never raised: the arm's own load says whether it is fatal
                notes.append(f"{name}: unknown, cannot import ({type(error).__name__}: {error})")
                continue
            seen[name] = found
            edges[module.__name__].append(name)
            queue.append(found)
    cycle = import_cycle(edges)
    if cycle:
        notes.append("import cycle (followed once): " + " -> ".join(cycle))
    return list(seen.values())


def import_cycle(edges: Mapping[str, Sequence[str]]) -> List[str]:
    """One import cycle in the graph as a closed path of names, or []."""
    state: Dict[str, int] = {}

    def visit(node: str, path: List[str]) -> List[str]:
        state[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt]
            if state.get(nxt) is None:
                found = visit(nxt, path + [nxt])
                if found:
                    return found
        state[node] = 2
        return []

    for start in sorted(edges):
        if state.get(start) is None:
            found = visit(start, [start])
            if found:
                return found
    return []


@dataclass(frozen=True)
class Member:
    """One item of a closure: an arm (``solution:name``), the object, and why it is in (``selected`` or ``needed by ...``)."""
    label: str
    target: Any
    reason: str = "selected"


def members_pairs(members: Iterable[Member], notes: Optional[List[str]] = None) -> List[Tuple[str, Any]]:
    """``(label, object)`` pairs for ``gather``: each arm, then each module of its package that it imports (labelled
    ``solution:name via module``), so a requirement declared on a helper module is included."""
    pairs: List[Tuple[str, Any]] = []
    for member in members:
        pairs.append((member.label, member.target))
        start = sys.modules.get(getattr(member.target, "__module__", "") or "") if not isinstance(member.target, ModuleType) else member.target
        if start is None:
            continue
        for module in walk_imports(start, notes):
            pairs.append((f"{member.label} via {module.__name__}", module))
    return pairs


def explain_closure(members: Iterable[Member]) -> List[str]:
    """One line per closure member with the reason it is in."""
    return [f"{one.label}  ({one.reason})" for one in members]


def identity(item: Requirement) -> Tuple[str, ...]:
    if isinstance(item, Env):
        return ("env", item.name)
    if isinstance(item, Api):
        return ("api", item.service)
    if isinstance(item, Python):
        return ("python", item.module, item.distribution, item.extra or "")
    if isinstance(item, Binary):
        return ("binary", item.name)
    if isinstance(item, Service):
        return ("service", item.name)
    if isinstance(item, Network):
        return ("network", item.host)
    if isinstance(item, Download):
        return ("download", item.name)
    if isinstance(item, ScriptFile):
        return ("file", item.path)
    if isinstance(item, Isolate):
        return ("isolate", item.boundary)
    return ("resource", item.note)


def gather(arms: Iterable[Tuple[str, Any]]) -> List[Entry]:
    """The deduplicated requirements of ``(label, arm)`` pairs. A requirement several arms declare appears once, required if any
    arm requires it, with every user named."""
    order: List[Tuple[str, ...]] = []
    merged: Dict[Tuple[str, ...], Requirement] = {}
    users: Dict[Tuple[str, ...], List[str]] = {}
    for label, arm in arms:
        for item in declared(arm):
            key = identity(item)
            if key not in merged:
                merged[key] = item
                users[key] = []
                order.append(key)
            elif item.required and not merged[key].required:
                merged[key] = replace(merged[key], required=True)
            if label not in users[key]:
                users[key].append(label)
    return [Entry(merged[key], tuple(users[key])) for key in order]


# checking

@dataclass(frozen=True)
class Check:
    """The result for one requirement: ``status`` is met, unmet or unknown; ``remedy`` is one line (empty when nothing to do)."""
    requirement: Requirement
    status: str
    remedy: str = ""

    @property
    def blocking(self) -> bool:
        return self.status == UNMET and self.requirement.required and self.requirement.kind in BLOCKING_KINDS

    @property
    def failing(self) -> bool:
        """Counts toward exit code 1: unmet and either required, or a download that will not fit on disk."""
        return self.status == UNMET and (self.requirement.required or self.requirement.kind == "download")


def present(environ: Mapping[str, str], names: Iterable[str]) -> bool:
    return any(str(environ.get(name) or "").strip() for name in names)


def link(label: str, url: str) -> str:
    return f"{label}: {url}" if url else ""


def api_hint(item: Api) -> str:
    """The sentence naming how to get the key, from the declared links."""
    names = " or ".join(item.key.names) if item.key else ""
    detail = "; ".join(part for part in (("free key: " + item.signup_url) if item.signup_url else "", link("docs", item.docs_url)) if part)
    text = f"set {names}" + (f" ({detail})" if detail else "")
    return text + (", or leave it unset to use the keyless path" if item.keyless else "")


def reach(url: str) -> bool:
    """True when a GET answers with anything below 500 within the probe time. Only called for ``probe=True``."""
    try:
        with urllib.request.urlopen(url, timeout=PROBE_SECONDS):   # noqa: S310 (the url is the arm's own declaration)
            return True
    except urllib.error.HTTPError as error:
        return error.code < 500
    except (OSError, ValueError):
        return False


def find_binary(name: str) -> Tuple[Optional[str], str]:
    """``(path, problem)``: the executable on PATH, or why there is none (absent, or found but not executable)."""
    path = shutil.which(name)
    if path:
        return path, ""
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(folder or ".") / name
        if candidate.is_file():
            return None, f"{candidate} exists but is not executable (chmod +x it)"
    return None, ""


def disk_free_mb(where: str) -> Optional[float]:
    """Free megabytes at the nearest existing folder of ``where`` (a cache hint like ``~/.cache/x``); None when unknown."""
    path = Path(os.path.expanduser(where or "~")).resolve() if where else Path.home()
    while not path.exists() and path != path.parent:
        path = path.parent
    try:
        return shutil.disk_usage(path).free / (1024 * 1024)
    except OSError:
        return None


def check_python(item: Python) -> Check:
    """Met when the module imports at a version the specifier allows; the marker may make it not apply here."""
    found = item.parsed
    if found.marker and not marker_applies(found.marker):
        return Check(item, MET)
    try:
        present_module = importlib.util.find_spec(item.module) is not None
    except (ImportError, ValueError, AttributeError):
        present_module = False
    if not present_module:
        return Check(item, UNMET, f"pip install '{item.pip_spec}' (use a virtualenv)")
    if not found.specifier:
        return Check(item, MET)
    try:
        version = importlib.metadata.version(found.name)
    except importlib.metadata.PackageNotFoundError:
        return Check(item, UNKNOWN, f"{item.module} imports but {found.name} is not an installed distribution here; version {found.specifier} not verified, pip will decide")
    parts = packaging_parts()
    if parts is None:
        return Check(item, UNKNOWN, f"version {found.specifier} of {found.name} not verified (packaging is not installed); pip will decide")
    try:
        ok = parts[0](found.specifier).contains(version, prereleases=True)
    except Exception:
        return Check(item, UNKNOWN, f"specifier {found.specifier!r} of {found.name} could not be read; pip will decide")
    return Check(item, MET) if ok else Check(item, UNMET, f"installed {found.name} {version} does not satisfy {found.specifier}: pip install '{item.pip_spec}'")


def check_one(item: Requirement, environ: Mapping[str, str], probe: bool) -> Check:
    if isinstance(item, Env):
        if present(environ, item.names):
            return Check(item, MET)
        return Check(item, UNMET, "set " + " or ".join(item.names) + (f" (fills option {item.option!r})" if item.option else ""))
    if isinstance(item, Api):
        if item.key is None:
            ok = reach(item.probe_url) if probe and item.probe_url else None
            if ok is False:
                return Check(item, UNMET, f"{item.service} did not answer at {item.probe_url}; check the network")
            return Check(item, MET if ok else UNKNOWN if item.probe_url else MET)
        if present(environ, item.key.names):
            if probe and item.probe_url and not reach(item.probe_url):
                return Check(item, UNMET, f"{item.service} did not answer at {item.probe_url}; check the network")
            return Check(item, MET)
        return Check(item, MET if item.keyless else UNMET, api_hint(item))
    if isinstance(item, Python):
        return check_python(item)
    if isinstance(item, Binary):
        path, problem = find_binary(item.name)
        if path is None:
            return Check(item, UNMET, problem or item.install_hint or f"install {item.name} and put it on PATH")
        if probe and item.version_args:
            try:
                done = subprocess.run([path, *item.version_args], capture_output=True, timeout=PROBE_SECONDS)
            except subprocess.TimeoutExpired:
                return Check(item, UNMET, f"{item.name} {' '.join(item.version_args)} timed out after {PROBE_SECONDS:g}s; reinstall or repair {item.name}")
            except (OSError, subprocess.SubprocessError):
                return Check(item, UNMET, f"{item.name} is on PATH but would not run; reinstall it")
            if done.returncode != 0:
                return Check(item, UNMET, f"{item.name} is on PATH but {' '.join(item.version_args)} failed; reinstall or repair it")
        return Check(item, MET)
    if isinstance(item, Network):
        offline = str(environ.get(OFFLINE_ENV, "") or os.environ.get(OFFLINE_ENV, "")).strip() == "1"
        return Check(item, UNMET, NETWORK_REMEDY + (f" ({item.host})" if item.host else "")) if offline else Check(item, MET)
    if isinstance(item, Service):
        address = str(environ.get(item.url_env) or "").strip() or (item.default_url or "")
        if not address:
            return Check(item, UNMET, f"set {item.url_env} to the address of {item.name}")
        configured = present(environ, (item.url_env,))
        if probe and item.health_path is not None:
            ok = reach(address.rstrip("/") + "/" + item.health_path.lstrip("/"))
            return Check(item, MET) if ok else Check(item, UNMET, f"start {item.name} at {address} or set {item.url_env}")
        if configured:
            return Check(item, MET)
        return Check(item, UNKNOWN, f"assumes {item.name} at {address}; set {item.url_env} to use another")
    if isinstance(item, Download):
        where = f" (cached in {item.cache_hint})" if item.cache_hint else ""
        size = f"about {item.size_mb:g} MB " if item.size_mb else ""
        free = disk_free_mb(item.cache_hint) if item.size_mb else None
        if free is not None and free < item.size_mb:
            return Check(item, UNMET, f"free disk space: {item.name} needs {item.size_mb:g} MB{where} and {free:.0f} MB is free; clear space or set the cache elsewhere")
        return Check(item, UNKNOWN, f"first use downloads {size}{item.name}{where}")
    if isinstance(item, ScriptFile):
        return Check(item, UNKNOWN, f"`esoi install --yes` runs it ({item.role})")
    return Check(item, UNKNOWN)


def check(requirements: Iterable[Any], environ: Mapping[str, str], probe: bool = False, offline: bool = False) -> List[Check]:
    """One ``Check`` per requirement (entries or bare requirements), in order. Variables in one ``group`` are met when any is.
    No network unless ``probe=True`` (never when ``offline``), which uses only each requirement's declared cheap probe, with a short timeout."""
    items = [getattr(entry, "requirement", entry) for entry in requirements]
    probe = probe and not offline   # --offline disables every network call
    results = [check_one(item, environ, probe) for item in items]
    for group in {item.group for item in items if isinstance(item, Env) and item.group}:
        members = [i for i, item in enumerate(items) if isinstance(item, Env) and item.group == group]
        if any(results[i].status == MET for i in members):
            for i in members:
                results[i] = Check(items[i], MET)
        else:
            names = " or ".join(name for i in members for name in items[i].names)
            for i in members:
                results[i] = Check(items[i], UNMET, f"set {names}")
    return results


def blocking(checks: Iterable[Check]) -> List[Check]:
    """The unmet required env, api, python and binary requirements: what keeps an arm from being built."""
    return [one for one in checks if one.blocking]


def remedy_line(checks: Iterable[Check]) -> str:
    """The unmet blocking remedies joined into one line."""
    return "; ".join(dict.fromkeys(one.remedy for one in blocking(checks) if one.remedy))


# outputs (generated, never hand-written)

GENERATED = "Generated by `esoi requirements`; edit the arms' declarations, not this file."


def describe(item: Requirement) -> str:
    """One short factual line about what the requirement is."""
    if isinstance(item, Env):
        return item.label + (" (secret)" if item.secret else "") + (f", fills {item.option}" if item.option else "")
    if isinstance(item, Api):
        bits = [item.label, "keyless path available" if item.keyless else "key required" if item.key else "no key"]
        for text, value in (("free tier", item.free_tier), ("rate limit", item.rate_limit)):
            if value:
                bits.append(f"{text}: {value}" + (f" (as of {item.as_of})" if item.as_of else ""))
        return ", ".join(bits)
    if isinstance(item, Python):
        return f"python module {item.module} from {item.pip_spec}"
    if isinstance(item, Binary):
        return f"binary {item.name} on PATH"
    if isinstance(item, Service):
        return f"service {item.name} at {item.url_env}" + (f" (default {item.default_url})" if item.default_url else "")
    if isinstance(item, Network):
        return "network access" + (f" to {item.host}" if item.host else "")
    if isinstance(item, Download):
        return f"download {item.name}" + (f", about {item.size_mb:g} MB" if item.size_mb else "")
    if isinstance(item, ScriptFile):
        return f"{item.role} file {item.path}"
    if isinstance(item, Isolate):
        return item.label
    return item.label


def report(entries: Sequence[Entry], checks: Optional[Sequence[Check]] = None) -> str:
    """A text report: one line per requirement with its status and remedy, and who uses it."""
    if not entries:
        return "no declared requirements\n"
    lines = []
    for i, entry in enumerate(entries):
        one = checks[i] if checks else None
        status = f"[{one.status}] " if one else ""
        need = "" if entry.requirement.required else " (optional)"
        line = f"{status}{describe(entry.requirement)}{need}"
        if entry.used_by:
            line += f"  <- {', '.join(entry.used_by)}"
        lines.append(line)
        if one and one.remedy:
            lines.append(f"    remedy: {one.remedy}")
    return "\n".join(lines) + "\n"


def as_json(entries: Sequence[Entry], checks: Optional[Sequence[Check]] = None, notes: Sequence[str] = ()) -> Dict[str, Any]:
    """The requirements as plain data under a versioned schema: ``{"schema", "requirements": [...], "notes": [...]}``. Names
    only: no variable's value is ever included."""
    out = []
    for i, entry in enumerate(entries):
        fields = {k: v for k, v in vars(entry.requirement).items() if v not in (None, "", ()) or k == "required"}
        item = entry.requirement
        if isinstance(item, Api) and item.key is not None:
            fields["key"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(item.key).items() if v not in (None, "", ())}
        for k, v in list(fields.items()):
            if isinstance(v, tuple):
                fields[k] = list(v)
        row: Dict[str, Any] = {**fields, "used_by": list(entry.used_by)}
        if checks:
            row["status"], row["remedy"] = checks[i].status, checks[i].remedy
        out.append(row)
    return {"schema": SCHEMA, "requirements": out, "notes": list(notes)}


def env_template(entries: Sequence[Entry]) -> str:
    """A ``.env`` template: every variable blank (secrets included, never filled), each with a comment saying what it is for and,
    for an api key, the signup and pricing links, the free tier and the keyless alternative."""
    lines = [f"# {GENERATED}", "# Fill in the values you have; leave the rest blank.", ""]
    seen: set = set()

    def variable(item: Env, comments: Sequence[str]) -> None:
        if item.name in seen:
            return
        seen.add(item.name)
        lines.extend(f"# {text}" for text in comments if text)
        if item.also:
            lines.append("# alternatives (any one): " + ", ".join(item.also))
        lines.extend([f"{item.name}=", ""])

    for entry in entries:
        item = entry.requirement
        users = ("used by " + ", ".join(entry.used_by)) if entry.used_by else ""
        if isinstance(item, Api) and item.key is not None:
            facts = [f"{item.service} API key" + (" (secret)" if item.key.secret else ""), users]
            facts += [link("signup", item.signup_url), link("docs", item.docs_url), link("pricing", item.pricing_url)]
            for text, value in (("free tier", item.free_tier), ("rate limit", item.rate_limit)):
                if value:
                    facts.append(f"{text}: {value}" + (f" (as of {item.as_of})" if item.as_of else ""))
            facts.append("works without a key (keyless path); a key is optional" if item.keyless else "required")
            variable(item.key, facts)
        elif isinstance(item, Env):
            variable(item, [("secret " if item.secret else "") + "variable" + (f" for option {item.option}" if item.option else ""),
                            users, "required" if item.required else "optional", item.note])
        elif isinstance(item, Service) and item.url_env and item.url_env not in seen:
            variable(Env(name=item.url_env), [f"address of {item.name}" + (f" (default {item.default_url})" if item.default_url else ""), users])
    return "\n".join(lines).rstrip() + "\n"


def install_script(entries: Sequence[Entry], environ: Optional[Mapping[str, str]] = None) -> str:
    """A bash install script, the generated successor of a per-folder install.sh: one ``pip install`` line for the python
    requirements not yet importable (extras merged per distribution), binary install hints as commented steps with a presence
    check, and downloads and services noted. It sets nothing up on its own beyond pip."""
    extras: Dict[str, List[str]] = {}
    for entry in entries:
        item = entry.requirement
        if isinstance(item, Python) and check_one(item, environ or {}, False).status != MET:
            extras.setdefault(item.distribution, [])
            if item.extra and item.extra not in extras[item.distribution]:
                extras[item.distribution].append(item.extra)
    lines = ["#!/usr/bin/env bash", f"# {GENERATED}", "set -euo pipefail", ""]
    if extras:
        specs = [f"{dist}[{','.join(sorted(found))}]" if found else dist for dist, found in sorted(extras.items())]
        lines += ["python -m pip install " + " ".join(f'"{spec}"' for spec in specs), ""]
    else:
        lines += ["# every declared python requirement is already importable", ""]
    for entry in entries:
        item = entry.requirement
        if isinstance(item, Binary):
            lines += [f"# {item.name}: {item.install_hint or 'install it and put it on PATH'}",
                      f'command -v {item.name} >/dev/null || echo "missing binary: {item.name}"', ""]
        elif isinstance(item, Download):
            lines += [f"# download on first use: {item.name}" + (f", about {item.size_mb:g} MB" if item.size_mb else "")
                      + (f" (cache: {item.cache_hint})" if item.cache_hint else ""), ""]
        elif isinstance(item, Service):
            lines += [f"# service: {item.name}; set {item.url_env}" + (f" (default {item.default_url})" if item.default_url else ""), ""]
        elif isinstance(item, Resource):
            lines += [f"# resource: {item.note}", ""]
    return "\n".join(lines).rstrip() + "\n"


# writing an env file safely

TEMPLATE_SUFFIXES = (".example", ".template", ".sample", ".dist")


def is_template_name(path: Path) -> bool:
    """A file name meant to be committed and shared (``.env.example``): it holds names and comments, never values."""
    return path.name.endswith(TEMPLATE_SUFFIXES)


def git_tracked(path: Path) -> bool:
    """True when git tracks the file (so a secret written there could be committed). False when git is absent."""
    try:
        done = subprocess.run(["git", "-C", str(path.parent), "ls-files", "--error-unmatch", path.name], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def write_env_file(path: Path, entries: Sequence[Entry]) -> str:
    """Write the env template to ``path`` and return what was done. A template name (``.env.example``) is regenerated whole. Any
    other name (``.env``) is never overwritten: missing variables are appended commented out, existing lines and values are
    kept, a new file is created with mode 600, and a git-tracked file is refused. Raises ``ValueError`` with the remedy."""
    text = env_template(entries)
    if is_template_name(path):
        path.write_text(text, encoding="utf-8")
        return f"wrote template {path}"
    if path.exists() and git_tracked(path):
        raise ValueError(f"{path} is tracked by git, so a secret written there could be committed; write to .env.example instead, "
                         "or untrack it (git rm --cached) and add it to .gitignore")
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    present_names = set(re.findall(r"^\s*(?:export\s+)?#?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", existing, flags=re.M))
    blocks = [block for block in text.split("\n\n") if block.strip().splitlines()[-1:] and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=$", block.strip().splitlines()[-1])]
    added = []
    chunks = []
    for block in blocks:
        lines = block.strip().splitlines()
        name = lines[-1][:-1]
        if name not in present_names:
            added.append(name)
            chunks.append("\n".join(lines[:-1] + [f"# {name}="]))
    if not path.exists():
        descriptor = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    else:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_APPEND)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        if chunks:
            handle.write(("" if not existing or existing.endswith("\n") else "\n") + ("\n" if existing else "") + "\n\n".join(chunks) + "\n")
    return f"{path}: added {len(added)} missing variable(s) commented out" + (f" ({', '.join(added)})" if added else "") + "; existing values untouched"
