"""Fill an arm's constructor options from an environment mapping the consumer hands over, as the arm's ``ENVIRON`` declares."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from esoi.runtime.assemble_by_name.environment_needs import declarations


ENVIRON_ATTRIBUTE = "ENVIRON"                    # on an arm: {option name: variable name, or a tuple of variable names}
ENVIRON_REQUIRED_ATTRIBUTE = "ENVIRON_REQUIRED"  # on an arm: the declared options it cannot be built without


def environ_declared(target: Any) -> Dict[str, Tuple[str, ...]]:
    """``{option: (variable names, first present wins)}`` an arm declares as data in its ``ENVIRON`` attribute."""
    found = getattr(target, ENVIRON_ATTRIBUTE, None)
    out = ({option: ((names,) if isinstance(names, str) else tuple(names)) for option, names in found.items()}
           if isinstance(found, Mapping) else {})
    for item in declarations.declared(target):   # env(..., option=...) and an api's key(option=...) fill options too
        key = item.key if isinstance(item, declarations.Api) else item
        if isinstance(key, declarations.Env) and key.option and key.option not in out:
            out[key.option] = key.names
    return out


def environ_fill(target: Any, options: Mapping[str, Any], environ: Mapping[str, str]) -> Dict[str, str]:
    """``{option: variable name}`` for each declared option the explicit ``options`` leave out and the passed mapping supplies
    (a non-empty value). Explicit options always win. Only names are returned, never values."""
    return {option: next(v for v in names if str(environ.get(v) or "").strip())
            for option, names in environ_declared(target).items()
            if option not in options and any(str(environ.get(v) or "").strip() for v in names)}


def environ_lacking(target: Any, options: Mapping[str, Any], environ: Mapping[str, str]) -> Dict[Tuple[str, ...], Tuple[str, ...]]:
    """The required declared options that neither ``options`` nor the passed mapping supplies, with the variable names to set.
    An entry of ``ENVIRON_REQUIRED`` is an option name, or a tuple of option names of which any one suffices; the key of the
    result is that tuple of option names."""
    declared, filled = environ_declared(target), environ_fill(target, options, environ)
    out: Dict[Tuple[str, ...], Tuple[str, ...]] = {}
    for entry in getattr(target, ENVIRON_REQUIRED_ATTRIBUTE, ()):
        group = (entry,) if isinstance(entry, str) else tuple(entry)
        if any(option in options or option in filled for option in group):
            continue
        out[group] = tuple(dict.fromkeys(v for option in group for v in declared.get(option, ())))
    return out
