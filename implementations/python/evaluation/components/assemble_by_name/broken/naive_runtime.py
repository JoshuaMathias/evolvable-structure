"""BASELINE: plain ``esoi.runtime.implementation_selection.declare`` with a loop that builds what it resolves, injecting needs by type. It has no name pattern,
no build-order check, no cycle or unmet-need message, no safe loading, no frozen layers, and the records are found by walking
up from the package. Zero model calls."""
import importlib
import typing

import assemble_fixture as world
from esoi.runtime.implementation_selection import declare
from esoi.runtime.implementation_selection import selection_registry


def strategy(pkg, site, consumer, args):
    importlib.import_module(f"{pkg}.solutions")
    raw = args.get("config", {})
    for solution_id, name, ref, replace in args.get("register", []):
        declare.register(solution_id, name, getattr(consumer, ref.split(":")[1]), scope=pkg, replace=replace)
    provided = world.provided_instances(args, consumer)
    built = {}

    def solution_of(interface):
        return next((sid for (scope, sid), entry in selection_registry.REGISTRY.items() if scope == pkg and entry.interface is interface), None)

    def make(solution_id):
        if solution_id in built:
            return built[solution_id]
        if solution_id in provided:
            built[solution_id] = provided[solution_id]
            return built[solution_id]
        name = raw.get("names", {}).get(solution_id) or raw.get("selections", {}).get(solution_id)
        target = declare.resolve(solution_id, name, scope=pkg)
        needs = {p: solution_of(h) for p, h in typing.get_type_hints(target.__init__).items() if p != "return" and solution_of(h)}
        kwargs = {p: make(sid) for p, sid in needs.items()}
        built[solution_id] = target(**kwargs, **raw.get("options", {}).get(solution_id, {}))
        return built[solution_id]

    for solution_id in raw.get("solutions") or [sid for scope, sid in selection_registry.REGISTRY if scope == pkg and sid in ("toy-store",)]:
        make(solution_id)
    return {"built": {sid: type(obj).__name__ for sid, obj in built.items()}, "order": list(built)}


build = world.arm_builder(strategy)
