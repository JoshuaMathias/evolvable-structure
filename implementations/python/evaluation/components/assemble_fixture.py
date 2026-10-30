"""A throwaway package for the assembly evaluation and tests: three solutions, one default arm with a packaged snapshot, a
consumer module with arms of its own, and the examples of the docs run in a fresh interpreter. No real data; public-repo safe.

``write_package(site, pkg)`` writes ``<site>/<pkg>/`` (solutions, arms, snapshot) and ``<site>/<pkg>consumer.py``. ``PKG`` in a text
stands for the package name and ``MARKER`` for a path a hostile file would write, so a case can tell that nothing ran.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, Optional

import esoi

SOLUTIONS = '''
import typing
from typing import runtime_checkable
from esoi import solution


@solution("toy-store")
@runtime_checkable
class Store(typing.Protocol):
    def put(self, key: str, value: str) -> None: ...
    def get(self, key: str) -> str: ...


@solution("toy-index")
@runtime_checkable
class Index(typing.Protocol):
    def find(self, key: str) -> str: ...


@solution("toy-report")
@runtime_checkable
class Report(typing.Protocol):
    def render(self) -> str: ...


@solution("toy-plain")
class Plain(typing.Protocol):
    def ping(self) -> str: ...


@solution("toy-fn")
def fn() -> None: ...
'''
ARMS = '''
from esoi import implementation
{marker}

@implementation("toy-store", "memory")
class Memory:
    def __init__(self):
        self.rows = {{}}

    def put(self, key, value):
        self.rows[key] = value

    def get(self, key):
        return self.rows[key]
'''
CONSUMER = '''
from PKG.solutions import Index, Report, Store


class Mine:
    def __init__(self):
        self.rows = {}

    def put(self, key, value):
        self.rows[key] = value

    def get(self, key):
        return self.rows[key]


class Pinger:
    def ping(self):
        return "pong"


class StoreIndex:
    def __init__(self, store: Store, prefix: str = ""):
        self.store, self.prefix = store, prefix

    def find(self, key):
        return self.store.get(self.prefix + key)


class IndexReport:
    def __init__(self, index: Index):
        self.index = index

    def render(self):
        return "report:" + self.index.find("k")


class LoopA:
    def __init__(self, other: Report):
        self.other = other


class LoopB:
    def __init__(self, other: Index):
        self.other = other


class ReportNeedsStore:
    def __init__(self, store: Store):
        self.store = store


class StoreNeedsIndex:
    def __init__(self, index: Index):
        self.index = index


class IndexNeedsReport:
    def __init__(self, report: Report):
        self.report = report
'''
STORE, INDEX, REPORT = "toy-store", "toy-index", "toy-report"


def write_package(site: Path, pkg: str = "esoitoy", module: Optional[str] = None, marker: str = "") -> None:
    """The package folder (``module`` is what the snapshot names for the default arm) and its consumer module."""
    package = site / pkg
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "solutions.py").write_text(textwrap.dedent(SOLUTIONS))
    line = f"open({marker!r}, 'a').write('x')\n" if marker else ""
    (package / "arms.py").write_text(textwrap.dedent(ARMS).replace("{marker}", line).replace("{{", "{").replace("}}", "}"))
    snapshot = {STORE: {"default": "memory", "modules": {"memory": module or f"{pkg}.arms"}}}
    (package / "esoi_selection.json").write_text(json.dumps(snapshot))
    (site / f"{pkg}consumer.py").write_text(textwrap.dedent(CONSUMER).replace("PKG", pkg))


# The examples of the docs: run in a fresh interpreter on a package named mylib, so they cannot rot.

ESOI_PATH = str(Path(esoi.__file__).resolve().parent.parent)
GUIDE = Path(__file__).resolve().parents[4] / "docs" / "guides" / "assemble-by-name.md"
RUNNER = """
import json, sys
from pathlib import Path
site, esoi_path = Path({site!r}), {esoi_path!r}
sys.path[:] = [str(site), esoi_path] + [p for p in sys.path if 'site-packages' not in p and p]
import mylib
namespace = {{"__name__": "mylib.system", "__file__": str(site / "mylib" / "system.py")}}
exec(compile(open({script!r}).read(), {script!r}, "exec"), namespace)
print(json.dumps({{"ok": True}}))
"""


def run_example(tmp_path: Path, source: str, files: Optional[Dict[str, str]] = None) -> None:
    """Run ``source`` as the module ``mylib.system`` beside the ``files`` (published path to text); raise on any failure."""
    site = tmp_path / "site"
    (site / "mylib").mkdir(parents=True)
    (site / "mylib" / "__init__.py").write_text("")
    for relative, text in (files or {}).items():
        (site / relative).parent.mkdir(parents=True, exist_ok=True)
        (site / relative).write_text(text)
    script = tmp_path / "example.py"
    script.write_text(source)
    done = subprocess.run([sys.executable, "-c", RUNNER.format(site=str(site), esoi_path=ESOI_PATH, script=str(script))],
                          cwd=tmp_path, capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "the example failed")


def docstring_example() -> str:
    """The indented example at the top of ``esoi.assemble``'s docstring."""
    from esoi import assemble
    lines, found = (assemble.__doc__ or "").splitlines(), []
    start = next(i for i, line in enumerate(lines) if line.startswith("    from pathlib import Path"))
    for line in lines[start:]:
        if line.strip() and not line.startswith("    "):
            break
        found.append(line)
    return textwrap.dedent("\n".join(found))


def run_docstring_example(tmp_path: Path) -> None:
    run_example(tmp_path, docstring_example())


def run_guide(tmp_path: Path) -> None:
    """Every python block of the guide: a block headed ``# mylib/<file>.py`` is that file (``system.py`` is the module the rest
    runs as); records for the ``sync_uses`` block are written beside, as an adopter's ``esoi/`` folder would hold them."""
    files, script = {}, []
    for block in re.findall(r"```python\n(.*?)```", GUIDE.read_text(), re.S):
        header = re.match(r"# (mylib/\w+\.py)\n", block)
        if header and header.group(1) != "mylib/system.py":
            files[header.group(1)] = block
        else:
            script.append(block)
    if not files or not script:
        raise AssertionError("the guide has no runnable python blocks")
    (tmp_path / "esoi").mkdir()
    (tmp_path / "esoi" / "solutions.csv").write_text("solution_id,selected,tags\nstore,memory,\nreport,plain,\n")
    (tmp_path / "esoi" / "implementations.csv").write_text(
        "implementation_id,solution_id,uses_solution_ids\nstore:memory,store,\nreport:plain,report,\n")
    run_example(tmp_path, "\n".join(script), files)


# One case: a fresh package name, its folder, the files a case adds, and what happened afterwards.

import importlib
import itertools
import os
import tempfile
from typing import Any, Callable

from esoi import runtime

counter = itertools.count(1)


def substitute(text: str, pkg: str, marker: Path) -> str:
    return text.replace("PKG", pkg).replace("MARKER", repr(str(marker)))


def package_case(args: Dict[str, Any], strategy: Callable[[str, Path, Any, Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """Run ``strategy(pkg, site, consumer, args)`` on a fresh package and report ``error`` (the exception class, '' for none),
    ``text`` (its message), the strategy's own keys, and three facts about the world afterwards: ``executed`` (a hostile file
    wrote its marker), ``path_same`` (``sys.path`` is as the case found it) and ``arm_imports`` (how often the default arm's
    module ran). ``args``: ``snapshot_module``, ``outside`` and ``inside`` (files beside and inside the package; ``PKG`` and
    ``MARKER`` are substituted)."""
    pkg = f"evalpkg{next(counter)}"
    with tempfile.TemporaryDirectory(prefix="esoi_assemble_") as tmp:
        root = Path(tmp)
        site, marker, arms = root / "site", root / "marker", root / "arms"
        module = substitute(args["snapshot_module"], pkg, marker) if args.get("snapshot_module") else None
        write_package(site, pkg, module, marker=str(arms) if args.get("count_arm_imports") else "")
        for where, key in ((site, "outside"), (site / pkg, "inside")):
            for relative, text in args.get(key, {}).items():
                (where / relative).parent.mkdir(parents=True, exist_ok=True)
                (where / relative).write_text(substitute(text, pkg, marker))
        sys.path.insert(0, str(site))
        before = list(sys.path)
        out: Dict[str, Any] = {"error": "", "text": "", "built": {}, "order": []}
        try:
            out.update(strategy(pkg, site, importlib.import_module(f"{pkg}consumer"), args))
        except Exception as error:   # the case says which class and message it expects
            out["error"], out["text"] = type(error).__name__, str(error)
        out["executed"], out["path_same"] = marker.exists(), sys.path == before
        out["arm_imports"] = len(arms.read_text()) if arms.exists() else 0
        out["arm_loaded"] = f"{pkg}.arms" in sys.modules
        sys.path[:] = [p for p in sys.path if p != str(site)]
        for name in [m for m in sys.modules if m.split(".")[0] in (pkg, f"{pkg}consumer")]:
            sys.modules.pop(name)
        for key in [k for k in runtime.REGISTRY if k[0] == pkg]:
            runtime.REGISTRY.pop(key)
        runtime.PROJECTS.clear()
    return out


def docs_case(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run the docstring example or the guide's blocks (``args['docs']``); ``error`` is '' when they run."""
    with tempfile.TemporaryDirectory(prefix="esoi_assemble_docs_") as tmp:
        try:
            {"docstring": run_docstring_example, "guide": run_guide}[args["docs"]](Path(tmp))
            return {"error": "", "text": ""}
        except AssertionError as error:
            return {"error": "AssertionError", "text": str(error)}
