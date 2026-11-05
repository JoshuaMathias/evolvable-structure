"""The errors an assembly raises: ``AssemblyError`` for any failure to resolve or build, ``LockError`` for a lock that cannot be used."""
from __future__ import annotations


class AssemblyError(ValueError):
    """An assembly error. The message names the solution id, scope, layer, the available names and a remedy."""


class LockError(AssemblyError):
    """A lock that cannot be used: unreadable, of another schema, or naming an arm that no longer exists. The message names the
    solution, the locked arm, the lock and the remedy (``esoi lock --update --solution <id>``)."""
