"""Block sockets and child programs for the rest of the process, so an entry check proves what runs without the network."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


LOCAL_PROGRAMS = ("git",)   # the one program the offline check lets an entry start: reading the repository's own files


class Offline(RuntimeError):
    """Raised inside the check when an entry tries the network or starts a program no declared requirement predicted."""


def offline_guard() -> None:
    """Block sockets and child processes for the rest of this process (the check runs in its own process, which exits after
    reporting), and set ``ESOI_OFFLINE=1`` so a provider that reads it refuses to start a model process by itself (the contract
    is in docs/explanation/when-metrics-are-run.md)."""
    import socket
    os.environ["ESOI_OFFLINE"] = "1"
    import subprocess

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise Offline("needs the network or a program (blocked in the offline check)")
    socket.socket.connect = refuse          # type: ignore[assignment]
    socket.create_connection = refuse       # type: ignore[assignment]
    allowed = subprocess.Popen.__init__

    def local_only(self: Any, args: Any, *rest: Any, **kwargs: Any) -> Any:
        program = Path(str(args[0] if isinstance(args, (list, tuple)) else str(args).split()[0])).name
        if program not in LOCAL_PROGRAMS:
            refuse()
        return allowed(self, args, *rest, **kwargs)
    subprocess.Popen.__init__ = local_only  # type: ignore[assignment]
    os.system = refuse                      # type: ignore[assignment]
