"""CURRENT: the live selector. ``esoi.select.Selector`` over a table of standard-library classes, and ``esoi.runtime`` (the
declared layer: decorators, registration, and the cascade of per call, context, environment, deployment and project
default) over a throwaway project folder whose records hold the project default. Zero model calls."""
import contextlib
import importlib
import itertools
import os
import tempfile
from pathlib import Path
from unittest import mock

from esoi import runtime, tables
from esoi.select import Selector

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


def declared_case(args):
    tag = next(counter)
    sid = f"case-{tag}-{args['solution']}"
    runtime.forget(sid)
    runtime.PROJECTS.clear()
    for name, target in args.get("registered", {}).items():
        runtime.register(sid, name, target)
    for name, target in args.get("decorated", {}).items():
        module, _, attr = target.partition(":")
        runtime.implementation(sid, name)(getattr(importlib.import_module(module), attr))
    interface = runtime.solution(sid)(lambda value: None) if args.get("interface") else None
    env = {runtime.env_name(sid): args["env"]} if args.get("env") else {}
    with tempfile.TemporaryDirectory(prefix="esoi_runtime_") as tmp:
        root = Path(tmp)
        project_folder(root, sid, args, tag)
        env[runtime.ROOT_ENV] = str(root)
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.dict(os.environ, env))
        if args.get("context"):
            stack.enter_context(runtime.override(sid, args["context"]))
        with stack:
            try:
                picked = runtime.choose(sid, args.get("using"))
                found = runtime.resolve(sid, args.get("using"))
                out = {"resolved": found.__name__, "chosen": picked.name, "layer": picked.layer,
                       "names": runtime.names(sid), "layers": [found[0] for found in runtime.explain(sid, args.get("using"))]}
                if interface is not None:
                    out["interface_chosen"] = interface.chosen(args.get("using")).name
                return out
            except Exception as exc:
                return {"error": type(exc).__name__, "text": str(exc).replace(sid, args["solution"])}
            finally:
                runtime.forget(sid)
                runtime.PROJECTS.clear()


def build(meter):
    def select(kind, args):
        try:
            return declared_case(args) if kind == "declared" else table_case(args)
        except Exception as exc:
            return {"error": type(exc).__name__, "text": str(exc)}
    return select
