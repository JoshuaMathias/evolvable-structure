"""Run the README's first example that calls ``<package>.run(``, offline and from an installed wheel (rule S37)."""
from __future__ import annotations

import contextlib
import doctest
import io
import json
import os
import re as regex
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from esoi.runtime.assemble_by_name.entry_outcome import pending_outcome
from esoi.runtime.assemble_by_name.entry_types import Pending
from esoi.runtime.assemble_by_name.offline_guard import offline_guard
from esoi.runtime.assemble_by_name.project_runner import project_runner
from esoi.structure.intent_registry import config as config_module


def readme_block(root: Path) -> Tuple[str, str, List[str]]:
    """``(block text, entry name, problems)``: the first ``pycon`` or ``python`` block with ``>>>`` lines that calls the entry."""
    cfg = config_module.load(root / "esoi.toml")
    name = "esoi.run" if cfg.package == "esoi" else f"{cfg.package}.run"
    readme = root / "README.md"
    if not readme.is_file():
        return "", name, ["README.md: missing"]
    blocks = regex.findall(r"```(?:python|pycon)\n(.*?)```", readme.read_text(encoding="utf-8"), flags=regex.S)
    block = next((b for b in blocks if ">>>" in b and f"{name}(" in b), None)
    if block is None:
        return "", name, [f"README.md: no fenced example with >>> lines that calls {name}(...)"]
    return block, name, []


def run_block(block: str, label: str = "README.md", guard: bool = True) -> Dict[str, List[str]]:
    """Run a doctest-style block in this process, offline. Each ``>>>`` line's printed output must match the lines under it. An
    example that raises ``Pending`` whose reasons are only keys or installs is pending (its shown output is proven by the
    installed stage, not here), and so is every example after it. Any other mismatch or error is a problem. ``guard`` blocks the
    network and programs for the rest of this process, so only a process meant to exit after reporting passes True."""
    if guard:
        offline_guard()
    parser, checker = doctest.DocTestParser(), doctest.OutputChecker()
    flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    examples = parser.get_examples(block)
    names: Dict[str, Any] = {}
    problems: List[str] = []
    pending: List[str] = []
    for index, example in enumerate(examples):
        buffer = io.StringIO()
        raised: Optional[BaseException] = None
        with contextlib.redirect_stdout(buffer):
            try:
                exec(compile(example.source, label, "single"), names)
            except BaseException as error:   # noqa: BLE001  the example's own failure is the finding
                raised = error
        if raised is None:
            if example.exc_msg is not None:
                problems.append(f"{label}: `{example.source.strip()}` was shown raising an error, but it returned")
                break
            if not checker.check_output(example.want, buffer.getvalue(), flags):
                problems.append(f"{label}: `{example.source.strip()}` prints {buffer.getvalue().strip()!r}, not {example.want.strip()!r}")
                break
            continue
        if isinstance(raised, Pending) and raised.reasons and pending_outcome(raised.reasons) in ("pending-key", "pending-install", "pending-network"):
            pending.append(f"{label}: `{example.source.strip()}` is pending ({'; '.join(raised.lines)[:200]})")
            pending += [f"{label}: `{rest.source.strip()}` pending after it" for rest in examples[index + 1:]]
            break
        text = "".join(traceback.format_exception_only(type(raised), raised))
        if example.exc_msg is not None and checker.check_output(example.exc_msg, text, flags):
            continue
        problems.append(f"{label}: `{example.source.strip()}` raised {type(raised).__name__}: {str(raised)[:200]}")
        break
    return {"problems": problems, "pending": pending}


def installed_readme(root: Path, block: str) -> List[str]:
    """Build the project's wheel (``pip wheel --no-deps --no-build-isolation``), install it into a temporary virtual environment
    that sees the system packages, and run the README block there from a temporary folder with the project root off the path."""
    cfg = config_module.load(root / "esoi.toml")
    folders = [root / p for p in (cfg.python_path or ["."])]
    home = next((f for f in [root, *folders] if (f / "pyproject.toml").is_file()), None)
    if home is None:
        return ["README.md: installed stage: no pyproject.toml to build a wheel from"]
    with tempfile.TemporaryDirectory() as scratch:
        scratch_path = Path(scratch)
        source = scratch_path / "source"     # built from a copy, so the project folder never gets build/ or egg-info litter
        shutil.copytree(home, source, ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__", ".esoi_cache", ".git"))
        done = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir",
                               str(scratch_path / "dist"), str(source)], capture_output=True, text=True, timeout=600)
        wheels = sorted((scratch_path / "dist").glob("*.whl"))
        if done.returncode or not wheels:
            return [f"README.md: installed stage: the wheel did not build: {(done.stderr or done.stdout)[-300:]}"]
        env_dir = scratch_path / "venv"
        subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(env_dir)], check=True, capture_output=True, timeout=600)
        python = env_dir / "bin" / "python"
        clean = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}   # a path entry must not make pip think it is installed
        installed = subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--no-index", "--ignore-installed", str(wheels[0])],
                                   capture_output=True, text=True, timeout=600, env=clean)
        if installed.returncode:
            return [f"README.md: installed stage: the wheel did not install: {installed.stderr[-300:]}"]
        (scratch_path / "block.txt").write_text(block, encoding="utf-8")
        drop = {str(Path(p).resolve()) for p in [root, *folders]}
        kept = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and str(Path(p).resolve()) not in drop]
        library = str(Path(__file__).resolve().parents[3])
        if cfg.package != "esoi" and library not in kept:
            kept.append(library)   # the library that runs this check; esoi's own wheel supplies itself
        work = scratch_path / "cwd"
        work.mkdir()
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(kept), ESOI_IN_ENTRY_CHECK="1")
        ran = subprocess.run([str(python), "-m", "esoi.runtime.assemble_by_name.entry_cli", "--readme-block", str(scratch_path / "block.txt"), "--json"],
                             cwd=work, env=env, capture_output=True, text=True, timeout=600)
        try:
            found = json.loads(ran.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return [f"README.md: installed stage did not report: {(ran.stderr or ran.stdout)[-300:]}"]
        return [f"installed: {line}" for line in found.get("problems", [])]


def readme_check(root: Path, installed: bool = False) -> Dict[str, List[str]]:
    """The README example, offline (and from an installed wheel when ``installed``): ``{"problems": [...], "pending": [...]}``."""
    block, name, bad = readme_block(root)
    if bad:
        return {"problems": bad, "pending": []}
    if installed:
        return {"problems": installed_readme(root, block), "pending": []}
    project_runner(root)
    os.environ["ESOI_IN_ENTRY_CHECK"] = "1"
    return run_block(block)
