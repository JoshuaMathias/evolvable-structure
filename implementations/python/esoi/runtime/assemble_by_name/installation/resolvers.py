"""Resolvers that dry-run pip on a merged requirement set, in the current environment or in a throwaway virtual environment."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple

from esoi.runtime.assemble_by_name.environment_needs.declarations import python
from esoi.runtime.assemble_by_name.installation.command_running import Outcome, PIP_TIMEOUT, Runner, run_command


Resolver = Callable[[Sequence[str], Sequence[str]], Outcome]


def pip_resolver(run: Runner = run_command, python: Optional[str] = None) -> Resolver:
    """A resolver that asks pip for a dry run (``--dry-run --report -``, pip 22.2 or later) of the requirement set, optionally
    with a constraints file. It changes nothing."""
    def resolve(specs: Sequence[str], constraints: Sequence[str]) -> Outcome:
        with tempfile.TemporaryDirectory() as work:
            command = [python or sys.executable, "-m", "pip", "install", "--dry-run", "--quiet", "--report", str(Path(work) / "report.json"), *specs]
            if constraints:
                path = Path(work) / "constraints.txt"
                path.write_text("\n".join(constraints) + "\n", encoding="utf-8")
                command += ["-c", str(path)]
            return run(command, None, PIP_TIMEOUT)
    return resolve


def venv_resolver(run: Runner = run_command) -> Tuple[Resolver, Callable[[], None]]:
    """A resolver that works in a throwaway virtualenv (so what is installed here cannot influence it), and its cleanup.
    Opt-in: it needs the network for pip's index."""
    work = tempfile.mkdtemp(prefix="esoi-coherence-")
    made = run([sys.executable, "-m", "venv", work], None, PIP_TIMEOUT)
    inner = str(Path(work) / ("Scripts" if os.name == "nt" else "bin") / "python")

    def cleanup() -> None:
        import shutil
        shutil.rmtree(work, ignore_errors=True)

    if made.code:
        cleanup()
        raise RuntimeError("could not create a temporary virtualenv: " + made.output.strip()[-200:])
    return pip_resolver(run, inner), cleanup
