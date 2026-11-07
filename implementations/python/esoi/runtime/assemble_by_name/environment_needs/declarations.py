"""Declare what an implementation needs from its environment, as data beside the arm, and gather the needs of many arms into one list.

An arm (a class or function that implements a solution) attaches its needs with a ``REQUIRES`` attribute::

    from esoi.runtime.assemble_by_name.environment_needs.declarations import api, env, python

    @implementation("literature-search", "openalex")
    class OpenAlex:
        REQUIRES = (
            api("OpenAlex", key=env("OPENALEX_API_KEY", option="api_key", secret=True), keyless=True,
                signup_url="https://openalex.org/settings/api", free_tier="free key, higher daily limit", as_of="2026-10"),
            python("requests", "requests"),
        )

The vocabulary is ``env``, ``api``, ``python``, ``binary``, ``service``, ``network``, ``download``, ``resource`` and ``isolatable``.
The older ``ENVIRON = {option: variable}`` and ``ENVIRON_REQUIRED`` attributes keep working and are read as env requirements.
``declared`` lists one arm's needs and ``gather`` merges many arms' into deduplicated entries naming every user. These are code
declarations, not fields of the ESOI records. Only variable names ever appear, never values."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from esoi.runtime.assemble_by_name.environment_needs.python_specs import Parsed, parse_requirement
from esoi.runtime.assemble_by_name.environment_needs.source_location import source_path


REQUIRES_ATTRIBUTE = "REQUIRES"


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
class Isolate(Requirement):
    """The arm can run out of process (``boundary``: ``subprocess``, ``cli`` or ``mcp``), so its python requirements may be
    installed in a virtual environment of their own when they cannot coexist with the rest."""
    kind: str = "isolate"
    boundary: str = ""

    @property
    def label(self) -> str:
        return f"isolatable via {self.boundary}"


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
    found.extend(environ_requirements(target, owned))
    return tuple(found)


def required_groups(declared_required: Iterable[Any]) -> Tuple[set, Dict[str, str]]:
    """``(required options, group per option)`` from ``ENVIRON_REQUIRED``: a tuple entry is a group of alternatives, any one of which will do."""
    groups: Dict[str, str] = {}
    required: set = set()
    for entry in declared_required:
        options = (entry,) if isinstance(entry, str) else tuple(entry)
        required.update(options)
        if len(options) > 1:
            groups.update({option: "|".join(options) for option in options})
    return required, groups


def environ_requirements(target: Any, owned: set) -> List["Env"]:
    """The env requirements an arm's ``ENVIRON`` mapping declares (required ones from ``ENVIRON_REQUIRED``, alternatives grouped);
    a variable an api requirement already owns is left out."""
    declared_env = getattr(target, "ENVIRON", None)
    if not isinstance(declared_env, Mapping):
        return []
    required, groups = required_groups(getattr(target, "ENVIRON_REQUIRED", ()) or ())
    found: List[Env] = []
    for option, names in declared_env.items():
        names = (names,) if isinstance(names, str) else tuple(names)
        if names and names[0] not in owned:
            found.append(Env(required=option in required, name=names[0], option=option, also=names[1:], group=groups.get(option, "")))
    return found


@dataclass(frozen=True)
class Entry:
    """A requirement and who uses it (``solution:arm`` labels), once however many arms declare it."""
    requirement: Requirement
    used_by: Tuple[str, ...] = ()


IDENTITY_KEYS = (
    (Env, lambda item: ("env", item.name)),
    (Api, lambda item: ("api", item.service)),
    (Python, lambda item: ("python", item.module, item.distribution, item.extra or "")),
    (Binary, lambda item: ("binary", item.name)),
    (Service, lambda item: ("service", item.name)),
    (Network, lambda item: ("network", item.host)),
    (Download, lambda item: ("download", item.name)),
    (ScriptFile, lambda item: ("file", item.path)),
    (Isolate, lambda item: ("isolate", item.boundary)),
)


def identity(item: Requirement) -> Tuple[str, ...]:
    for kind, key in IDENTITY_KEYS:
        if isinstance(item, kind):
            return key(item)
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
