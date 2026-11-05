"""Run a command with a timeout and return its outcome, and keep what is shown or returned free of secret values."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence


PIP_TIMEOUT = 900.0
SCRIPT_TIMEOUT = 600.0
TAIL_LINES = 20


@dataclass(frozen=True)
class Outcome:
    """What a command did: its exit code, the tail of its output, and whether it timed out."""
    code: int
    output: str = ""
    timed_out: bool = False


Runner = Callable[[Sequence[str], Optional[str], float], Outcome]


def run_command(command: Sequence[str], cwd: Optional[str] = None, timeout: float = PIP_TIMEOUT) -> Outcome:
    """Run a command, capturing output; a missing program or a timeout is an ``Outcome``, never an exception."""
    try:
        done = subprocess.run(list(command), cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        return Outcome(124, str(error.stdout or "") + str(error.stderr or ""), True)
    except OSError as error:
        return Outcome(127, f"{command[0]}: {error}")
    return Outcome(done.returncode, (done.stdout or "") + (done.stderr or ""))


def scrub(text: str, environ: Mapping[str, str]) -> str:
    """The text with every secret-looking value of the environment replaced by ``***`` (values of four characters or more)."""
    for value in sorted({str(v).strip() for v in environ.values() if len(str(v).strip()) >= 4}, key=len, reverse=True):
        text = text.replace(value, "***")
    return text


def tail(text: str, environ: Mapping[str, str], lines: int = TAIL_LINES) -> str:
    """The last lines of captured output, scrubbed."""
    return "\n".join(scrub(text, environ).strip().splitlines()[-lines:])
