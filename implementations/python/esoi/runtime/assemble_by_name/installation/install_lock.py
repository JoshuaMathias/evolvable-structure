"""A process lock so only one esoi install runs against an environment at a time."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


class InstallLocked(RuntimeError):
    """Another install is running in this environment."""


class InstallLock:
    """A process lock so two installs cannot run at once in one environment (a lock file per interpreter prefix)."""

    def __init__(self, folder: Optional[Path] = None):
        import hashlib
        name = "esoi-install-" + hashlib.sha1(sys.prefix.encode()).hexdigest()[:12] + ".lock"
        self.path = (folder or Path(tempfile.gettempdir())) / name
        self.handle: Any = None

    def __enter__(self) -> "InstallLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a+")
        try:
            import fcntl
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:   # no fcntl (Windows): fall back to an exclusive marker file
            self.handle.close()
            try:
                self.handle = os.fdopen(os.open(str(self.path) + ".run", os.O_CREAT | os.O_EXCL | os.O_WRONLY), "w")
            except FileExistsError:
                raise InstallLocked(f"another install holds {self.path}.run; wait for it, or delete the file if it is stale") from None
        except OSError:
            self.handle.close()
            raise InstallLocked(f"another esoi install is running in this environment (lock {self.path}); wait for it to finish") from None
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            if self.handle is not None:
                self.handle.close()
            marker = Path(str(self.path) + ".run")
            if marker.exists():
                marker.unlink()
        except OSError:
            pass
