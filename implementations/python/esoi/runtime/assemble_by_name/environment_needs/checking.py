"""Check declared needs against the environment: each requirement is met, unmet or unknown, with one remedy line, and no network unless asked to probe."""

from __future__ import annotations

import importlib
import importlib.util
import importlib.metadata
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Tuple

from esoi.runtime.assemble_by_name.environment_needs.api_links import api_hint
from esoi.runtime.assemble_by_name.environment_needs.declarations import Api, Binary, Download, Env, Network, Python, Requirement, ScriptFile, Service
from esoi.runtime.assemble_by_name.environment_needs.python_specs import marker_applies, packaging_parts


MET, UNMET, UNKNOWN = "met", "unmet", "unknown"
NETWORK_REMEDY = "needs network access; not attempted offline"
BLOCKING_KINDS = ("env", "api", "python", "binary", "network")   # an unmet required one of these keeps an arm pending
OFFLINE_ENV = "ESOI_OFFLINE"   # "1": no network and no model process; a network requirement is unmet while it is set
PROBE_SECONDS = 3.0


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


def check_env(item: Env, environ: Mapping[str, str]) -> Check:
    if present(environ, item.names):
        return Check(item, MET)
    return Check(item, UNMET, "set " + " or ".join(item.names) + (f" (fills option {item.option!r})" if item.option else ""))


def check_api(item: Api, environ: Mapping[str, str], probe: bool) -> Check:
    unreachable = Check(item, UNMET, f"{item.service} did not answer at {item.probe_url}; check the network")
    if item.key is None:
        ok = reach(item.probe_url) if probe and item.probe_url else None
        if ok is False:
            return unreachable
        return Check(item, MET if ok else UNKNOWN if item.probe_url else MET)
    if present(environ, item.key.names):
        return unreachable if probe and item.probe_url and not reach(item.probe_url) else Check(item, MET)
    return Check(item, MET if item.keyless else UNMET, api_hint(item))


def check_binary(item: Binary, probe: bool) -> Check:
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


def check_service(item: Service, environ: Mapping[str, str], probe: bool) -> Check:
    address = str(environ.get(item.url_env) or "").strip() or (item.default_url or "")
    if not address:
        return Check(item, UNMET, f"set {item.url_env} to the address of {item.name}")
    if probe and item.health_path is not None:
        ok = reach(address.rstrip("/") + "/" + item.health_path.lstrip("/"))
        return Check(item, MET) if ok else Check(item, UNMET, f"start {item.name} at {address} or set {item.url_env}")
    if present(environ, (item.url_env,)):
        return Check(item, MET)
    return Check(item, UNKNOWN, f"assumes {item.name} at {address}; set {item.url_env} to use another")


def check_download(item: Download) -> Check:
    where = f" (cached in {item.cache_hint})" if item.cache_hint else ""
    size = f"about {item.size_mb:g} MB " if item.size_mb else ""
    free = disk_free_mb(item.cache_hint) if item.size_mb else None
    if free is not None and free < item.size_mb:
        return Check(item, UNMET, f"free disk space: {item.name} needs {item.size_mb:g} MB{where} and {free:.0f} MB is free; clear space or set the cache elsewhere")
    return Check(item, UNKNOWN, f"first use downloads {size}{item.name}{where}")


def check_network(item: Network, environ: Mapping[str, str]) -> Check:
    offline = str(environ.get(OFFLINE_ENV, "") or os.environ.get(OFFLINE_ENV, "")).strip() == "1"
    return Check(item, UNMET, NETWORK_REMEDY + (f" ({item.host})" if item.host else "")) if offline else Check(item, MET)


def check_one(item: Requirement, environ: Mapping[str, str], probe: bool) -> Check:
    if isinstance(item, Env):
        return check_env(item, environ)
    if isinstance(item, Api):
        return check_api(item, environ, probe)
    if isinstance(item, Python):
        return check_python(item)
    if isinstance(item, Binary):
        return check_binary(item, probe)
    if isinstance(item, Network):
        return check_network(item, environ)
    if isinstance(item, Service):
        return check_service(item, environ, probe)
    if isinstance(item, Download):
        return check_download(item)
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
