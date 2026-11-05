"""The errors a run raises: it cannot start as asked, an offline run tried a model command, or an arm is pending on the network."""
from __future__ import annotations


class RunError(ValueError):
    """The run cannot start as asked (no such implementation, no case selected); the message says what to change."""


class OfflineViolation(RuntimeError):
    """An offline run tried to start a model command."""


class PendingNetwork(RunError):
    """The arm declares a network requirement and ``ESOI_OFFLINE=1`` is set: it is pending, not failed, and nothing was started."""
