"""Read facts from an arm's own code: its builder, package version, option hash, Protocol members and declaration identity."""
from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import typing
from typing import Any, Mapping, Set


def builder_of(target: Any) -> Any:
    """The callable that builds an arm: a class's ``__init__``, or the function itself."""
    if inspect.isclass(target):
        return None if target.__init__ is object.__init__ else target.__init__
    return target if inspect.isfunction(target) else None


def package_version(target: Any) -> str:
    top = str(getattr(target, "__module__", None) or type(target).__module__).split(".")[0]
    try:
        return importlib.metadata.version(top)
    except importlib.metadata.PackageNotFoundError:
        return "unversioned"


def config_hash(options: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(options, sort_keys=True, default=str).encode()).hexdigest()[:8]


def protocol_members(protocol: Any) -> Set[str]:
    """The names a Protocol class requires of an object: its methods and annotated attributes, own and inherited."""
    members: Set[str] = set()
    for klass in protocol.__mro__:
        if klass in (typing.Protocol, typing.Generic, object) or not getattr(klass, "_is_protocol", False):
            continue
        members |= {n for n in vars(klass) if not (n.startswith("__") and n.endswith("__")) and not n.startswith("_abc_")
                    and n not in ("_is_protocol", "_is_runtime_protocol")}
        members |= set(klass.__dict__.get("__annotations__", {}))
    return members


def same_declaration(one: Any, other: Any) -> bool:
    """The same object, or the same definition imported again (a reloaded module declares its arm anew)."""
    return one is other or (getattr(one, "__module__", 0) == getattr(other, "__module__", 1)
                            and getattr(one, "__qualname__", 0) == getattr(other, "__qualname__", 1))
