"""CURRENT: the live selector. ``esoi.runtime.implementation_selection.select.Selector`` over a table of standard-library classes, and ``esoi.runtime.implementation_selection.declare`` (the
declared layer: decorators, registration, and the cascade of per call, context, environment, deployment and project
default) over a throwaway project folder whose records hold the project default. Zero model calls."""
import contextlib
import importlib
import itertools
import os
import tempfile
from pathlib import Path
from unittest import mock

from esoi.runtime.implementation_selection import declare
from esoi.runtime.implementation_selection import selection_cascade
from esoi.runtime.implementation_selection import selection_registry
from esoi.structure.intent_registry import tables
from esoi.runtime.implementation_selection.select import Selector

counter = itertools.count(1)


def table_case(args):
    selector = Selector(args["table"], args.get("defaults"))
    for extra in args.get("register", []):
        selector.register(args["solution"], extra["name"], extra["target"], default=extra.get("default", False))
    name = selector.chosen_name(args["solution"], args.get("name"), args.get("overrides"))
    if args.get("config"):
        found = selector.resolve_config(args["solution"], args.get("name"), overrides=args.get("overrides"))
        return {"resolved": found.__name__ if found else None, "chosen": name, "names": selector.names(args["solution"])}
    found = selector.resolve(args["solution"], args.get("name"), overrides=args.get("overrides"))
    return {"resolved": found.__name__, "chosen": name, "names": selector.names(args["solution"])}


def project_folder(root, sid, args, tag):
    """A legacy-layout project: ``esoi.toml`` (with a ``[selection]`` table when the case has a deployment choice),
    a ``solutions.csv`` whose ``selected`` is the project default, and a recorded module for a lazily imported one."""
    lines = ['structure_dir = "specs"', 'python_path = ["."]']
    if args.get("deployment"):
        lines += ["", "[selection]", f'{sid} = "{args["deployment"]}"']
    (root / "esoi.toml").write_text("\n".join(lines) + "\n")
    (root / "specs").mkdir()
    tables.write_csv(root / "specs" / "solutions.csv", ["solution_id", "selected", "implementations"],
                     [{"solution_id": sid, "selected": args.get("records_default", ""), "implementations": ""}])
    rows = []
    lazy = args.get("lazy_module")
    if lazy:
        package = f"lazy_{tag}"
        (root / package).mkdir()
        (root / package / "__init__.py").write_text("")
        (root / package / "mod.py").write_text(lazy["source"].replace("SID", sid))
        rows.append({"implementation_id": f"{sid}:{lazy['name']}", "solution_id": sid, "filepath": f"{package}/mod.py"})
    tables.write_csv(root / "specs" / "implementations.csv", ["implementation_id", "solution_id", "filepath"], rows)


def case_outcome(sid: str, args: dict, interface) -> dict:
    """What the cascade chooses for the declared case: the resolved implementation, the chosen one, its layer, the names and the layers."""
    picked = selection_cascade.choose(sid, args.get("using"))
    found = declare.resolve(sid, args.get("using"))
    out = {"resolved": found.__name__, "chosen": picked.name, "layer": picked.layer,
           "names": selection_cascade.names(sid), "layers": [found[0] for found in selection_cascade.explain(sid, args.get("using"))]}
    if interface is not None:
        out["interface_chosen"] = interface.chosen(args.get("using")).name
    return out


def declared_case(args):
    tag = next(counter)
    sid = f"case-{tag}-{args['solution']}"
    selection_registry.forget(sid)
    selection_registry.PROJECTS.clear()
    for name, target in args.get("registered", {}).items():
        declare.register(sid, name, target)
    for name, target in args.get("decorated", {}).items():
        module, _, attr = target.partition(":")
        declare.implementation(sid, name)(getattr(importlib.import_module(module), attr))
    interface = declare.solution(sid)(lambda value: None) if args.get("interface") else None
    env = {selection_cascade.env_name(sid): args["env"]} if args.get("env") else {}
    with tempfile.TemporaryDirectory(prefix="esoi_runtime_") as tmp:
        root = Path(tmp)
        project_folder(root, sid, args, tag)
        env[selection_registry.ROOT_ENV] = str(root)
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.dict(os.environ, env))
        if args.get("context"):
            stack.enter_context(declare.override(sid, args["context"]))
        with stack:
            try:
                return case_outcome(sid, args, interface)
            except Exception as exc:
                return {"error": type(exc).__name__, "text": str(exc).replace(sid, args["solution"])}
            finally:
                selection_registry.forget(sid)
                selection_registry.PROJECTS.clear()


def build(meter):
    def select(kind, args):
        try:
            return declared_case(args) if kind == "declared" else table_case(args)
        except Exception as exc:
            return {"error": type(exc).__name__, "text": str(exc)}
    return select
