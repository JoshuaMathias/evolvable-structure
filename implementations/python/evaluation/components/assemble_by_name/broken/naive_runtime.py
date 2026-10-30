"""BASELINE: plain ``esoi.runtime`` with a loop that builds what it resolves, injecting needs by type. It has no name pattern,
no build-order check, no cycle or unmet-need message, no safe loading, no frozen layers, and the records are found by walking
up from the package. Zero model calls."""
import importlib
import typing

import assemble_fixture as world
from esoi import runtime


def strategy(pkg, site, consumer, args):
    importlib.import_module(f"{pkg}.solutions")
    raw = args.get("config", {})
    for solution_id, name, ref, replace in args.get("register", []):
        runtime.register(solution_id, name, getattr(consumer, ref.split(":")[1]), scope=pkg, replace=replace)
    provided = {sid: (object() if ref == "object" else getattr(consumer, ref.split(":")[1])()) for sid, ref in args.get("provided", {}).items()}
    built = {}

    def solution_of(interface):
        return next((sid for (scope, sid), entry in runtime.REGISTRY.items() if scope == pkg and entry.interface is interface), None)

    def make(solution_id):
        if solution_id in built:
            return built[solution_id]
        if solution_id in provided:
            built[solution_id] = provided[solution_id]
            return built[solution_id]
        name = raw.get("names", {}).get(solution_id) or raw.get("selections", {}).get(solution_id)
        target = runtime.resolve(solution_id, name, scope=pkg)
        needs = {p: solution_of(h) for p, h in typing.get_type_hints(target.__init__).items() if p != "return" and solution_of(h)}
        kwargs = {p: make(sid) for p, sid in needs.items()}
        built[solution_id] = target(**kwargs, **raw.get("options", {}).get(solution_id, {}))
        return built[solution_id]

    for solution_id in raw.get("solutions") or [sid for scope, sid in runtime.REGISTRY if scope == pkg and sid in ("toy-store",)]:
        make(solution_id)
    return {"built": {sid: type(obj).__name__ for sid, obj in built.items()}, "order": list(built)}


def build(meter):
    def assemble(kind, args):
        return world.docs_case(args) if kind == "docs" else world.package_case(args, strategy)
    return assemble
