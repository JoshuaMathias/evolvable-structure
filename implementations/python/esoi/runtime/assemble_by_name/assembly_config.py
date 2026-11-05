"""What a consumer hands the assembler at startup: the manifest, names, selections, options, environments, lock and circumstances."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class AssemblyConfig:
    """What a consumer hands the assembler, once, at startup.

    ``solutions`` is the manifest of solution ids the consumer uses (empty: every solution that has a default arm or is
    provided). ``names`` are explicit names per solution id and ``selections`` the consumer's own selections (they live on
    this object, never process-wide). ``options`` are the non-solution constructor arguments per solution id.
    ``selection_environ`` is the only environment ``esoi`` ever sees: a consumer that wants an
    ``ESOI_SELECT_<SCOPE>_<SOLUTION_ID>`` choice puts exactly that variable here, and nothing else is accepted.
    A name in ``names``, ``selections`` or ``selection_environ`` may be ``name@key=value,...`` (or, in the first two, a list of
    such entries): it then applies only when every ``key=value`` holds in ``circumstances``, the caller's own mapping.
    ``consumer_environ`` is a mapping the consumer hands over (usually its own process environment, passed explicitly): an arm that
    declares ``ENVIRON = {option: variable name or tuple of names}`` has those options filled from it, unless ``options`` gives
    them; ``ENVIRON_REQUIRED`` names the declared options without which it cannot be built (a tuple entry: any one of them) (it then stays pending, naming the
    variables). Only variable names appear in reasons and ``pending``, never values.
    ``lock`` is a path to an ``esoi.lock.json`` or the mapping it holds (``esoi.runtime.implementation_selection.lock``): it names the arm to keep per solution
    and sits between ``selection_environ`` and the package defaults, so a consumer who locked is not moved by a new release
    until the lock is updated. Leave it ``None`` to follow the latest selections (the default).
    ``reasons`` is ``{solution_id: [record id or "unconfirmed: text", ...]}`` for the ``selections`` of the same solution: why
    it differs from a parent's default (shown by ``explain``, recorded in the ``Choice``).
    """
    solutions: Tuple[str, ...] = ()
    names: Mapping[str, str] = field(default_factory=dict)
    selections: Mapping[str, str] = field(default_factory=dict)
    options: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    selection_environ: Mapping[str, str] = field(default_factory=dict)
    reasons: Mapping[str, Sequence[str]] = field(default_factory=dict)
    circumstances: Mapping[str, Any] = field(default_factory=dict)
    consumer_environ: Mapping[str, str] = field(default_factory=dict)
    lock: Any = None
