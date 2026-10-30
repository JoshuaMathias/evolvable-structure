"""CURRENT: the live assembler, ``esoi.assemble.Assembler``, over a throwaway package in a fresh scope (see
``assemble_fixture``). Zero model calls."""
import contextlib
import threading

import assemble_fixture as world
from esoi import runtime
from esoi.assemble import Assembler, AssemblyConfig


def configure(pkg, raw):
    environ = {key.replace("PKG", pkg.upper()): value for key, value in raw.get("selection_environ", {}).items()}
    return AssemblyConfig(solutions=tuple(raw.get("solutions", ())), names=raw.get("names", {}), selections=raw.get("selections", {}),
                          options=raw.get("options", {}), selection_environ=environ)


def strategy(pkg, site, consumer, args):
    parts = Assembler(pkg, site / pkg, (f"{pkg}.solutions",))
    parts.prepare()
    if args.get("only_prepare"):
        return {}
    for solution_id, name, ref, replace in args.get("register", []):
        parts.register(solution_id, name, getattr(consumer, ref.split(":")[1]), replace)
    for solution_id, name, ref in args.get("behind", []):
        runtime.register(solution_id, name, getattr(consumer, ref.split(":")[1]), scope=pkg, replace=True)
    provided = {sid: (object() if ref == "object" else getattr(consumer, ref.split(":")[1])())
                for sid, ref in args.get("provided", {}).items()}
    config = configure(pkg, args.get("config", {}))
    with contextlib.ExitStack() as stack:
        for solution_id, name in args.get("override", {}).items():
            stack.enter_context(runtime.override(solution_id, name, scope=pkg))
        if args.get("threads"):
            return threaded(parts, config, provided, args["threads"])
        system = parts.assemble(config, provided)
    return {"built": {sid: type(system[sid]).__name__ for sid in system.solutions()}, "order": system.solutions()}


def threaded(parts, config, provided, count):
    barrier, results, errors = threading.Barrier(count), [], []

    def work():
        barrier.wait()
        try:
            system = parts.assemble(config, provided)
            results.append({sid: type(system[sid]).__name__ for sid in system.solutions()})
        except Exception as error:
            errors.append(repr(error))
    threads = [threading.Thread(target=work) for _ in range(count)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    agree = all(r == results[0] for r in results) and len(results) == count
    return {"built": results[0] if results else {}, "agree": agree, "errors": errors}


def build(meter):
    def assemble(kind, args):
        return world.docs_case(args) if kind == "docs" else world.package_case(args, strategy)
    return assemble
