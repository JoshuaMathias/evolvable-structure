"""Load an implementation (an arm) of a component: its wrapper, a module:function, or the one the code declares."""
from __future__ import annotations

import functools
import importlib
import inspect
import pkgutil
from typing import Any, Callable, Dict, List, Optional

from esoi.optimization.measurement_harness.call_meter import CallMeter
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry.config import Config


def declared_target(config: Config, component: str, name: str) -> Any:
    """The implementation of that name the code declares (``esoi.runtime.implementation_selection.declare``) for the solution this component measures, or None.
    Nothing is imported unless a solution measured by the component lists the name."""
    from esoi.runtime.implementation_selection import selection_cascade
    from esoi.runtime.implementation_selection import selection_registry
    from esoi.structure.intent_registry.registry import harness_arms, load
    found = {}
    for row in load(config).solutions:
        if any(comp == component for comp, _ in harness_arms(config, row.get("metric_command", ""))):
            try:
                found.update(selection_cascade.load_declared(config, row["solution_id"]))
            except selection_registry.SelectionError:
                continue
    return found.get(name.strip().lower())


def declared_build(config: Config, component: str, name: str) -> Optional[Callable]:
    """``build(meter)`` for an implementation the code declares (``esoi.runtime.implementation_selection.declare``) for the solution this component
    measures, or None when there is none of that name."""
    target = declared_target(config, component, name)
    if target is None:
        return None
    score = importlib.import_module(f"{component}.score")

    def build(meter: CallMeter, **params: Any) -> Callable:
        bound = functools.partial(check_parameters(target, params, name), **params) if params else target   # esoi.runtime.implementation_selection.variants
        if hasattr(score, "adapt"):
            return score.adapt(bound, meter)
        return lambda kind, args: bound(**args)
    return build


def arm_targets(config: Config, component: str, impl: str) -> List[Any]:
    """The objects whose ``REQUIRES`` describe an arm: its module and ``build``, the ``module:function`` it names, or the
    implementation the code declares. An arm that cannot be found is left to ``load_impl`` to report."""
    spec = variants.split(impl)[0]
    try:
        if ":" in spec:
            module, _, attr = spec.partition(":")
            loaded = importlib.import_module(module)
            return [getattr(loaded, attr), loaded]
        loaded = importlib.import_module(f"{component}.impls.{spec}")
        return [loaded, getattr(loaded, "build", None)]
    except (ImportError, AttributeError):
        target = declared_target(config, component, spec)
        return [target] if target is not None else []


def check_parameters(fn: Callable, params: Dict[str, Any], name: str) -> Callable:
    """``fn``, or ``RunError`` when it takes none of a variant's parameters by that name: an unknown key fails the arm once,
    loudly, instead of failing every case into a 0/N row."""
    try:
        accepted = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn
    if not any(p.kind is p.VAR_KEYWORD for p in accepted.values()):
        unknown = sorted(set(params) - set(accepted))
        if unknown:
            raise RunError(f"{name} takes no parameter {', '.join(unknown)} (it takes: {', '.join(accepted) or 'none'})")
    return fn


def load_impl(spec: str, component: str, config: Optional[Config] = None) -> Callable:
    """``--impl name`` -> ``<component>/impls/name.py``'s ``build``, else the implementation of that name the code
    declares (needs ``config``); ``module:function`` is also accepted. A variant (``name@key=value``, see ``esoi.runtime.implementation_selection.variants``)
    resolves ``name`` and passes the parameters to its ``build(meter, **params)``."""
    if ":" in spec:
        module, _, attr = spec.partition(":")
        return getattr(importlib.import_module(module), attr)
    spec, params = variants.split(spec)
    if params:
        build = load_impl(spec, component, config)
        return lambda meter: check_parameters(build, params, spec)(meter, **params)
    try:
        return importlib.import_module(f"{component}.impls.{spec}").build
    except ModuleNotFoundError as exc:
        if exc.name not in (f"{component}.impls.{spec}", f"{component}.impls"):
            raise   # the implementation exists but one of its own imports is missing: that is the finding
        declared = declared_build(config, component, spec) if config is not None else None
        if declared is not None:
            return declared
        try:
            known = sorted(m.name for m in pkgutil.iter_modules(importlib.import_module(f"{component}.impls").__path__))
        except ModuleNotFoundError:
            known = []
        raise RunError(f"{component} has no implementation {spec!r}; known: {', '.join(known) or 'none'} (an implementation "
                       "declared with @implementation is found through the records: `esoi records sync` writes them)") from exc
