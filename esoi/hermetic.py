"""A guard for evaluations that drive live code: no shell or deployment setting reaches the run.

Environment variables from a deployed lane, or credentials in a developer's shell, would change what a case
measures or let it reach a live service. ``hermetic_env`` removes every variable that starts with one of the
configured prefixes or is named in ``names``, sets ``extra`` on top, and restores the environment on exit. The
configuration lives in the ``[hermetic]`` table of the repository's config:

    [hermetic]
    prefixes = ["MYAPP_"]
    names = ["API_KEY", "DATABASE_URL"]
    set = { MYAPP_MODE = "offline" }
"""
from __future__ import annotations

import contextlib
import os
from typing import Dict, Iterable, Iterator, Optional

from .config import Config


@contextlib.contextmanager
def hermetic_env(prefixes: Iterable[str] = (), names: Iterable[str] = (),
                 extra: Optional[Dict[str, str]] = None) -> Iterator[None]:
    """Scrub matching variables for the block, set ``extra`` on top, restore on exit."""
    prefixes, names = tuple(prefixes), set(names)
    saved = dict(os.environ)
    for name in [n for n in os.environ if n.startswith(prefixes) or n in names]:
        del os.environ[name]
    os.environ.update(extra or {})
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def from_config(config: Config, extra: Optional[Dict[str, str]] = None):
    """``hermetic_env`` with the repository's ``[hermetic]`` settings (``set`` is applied, then ``extra``)."""
    table = config.hermetic
    return hermetic_env(table.get("prefixes", ()), table.get("names", ()), {**table.get("set", {}), **(extra or {})})
