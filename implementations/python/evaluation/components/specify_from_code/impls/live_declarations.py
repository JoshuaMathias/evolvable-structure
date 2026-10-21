"""CURRENT: the live declarations, ``esoi.declarations.scan``, ``drift`` and ``sync``, and ``esoi.newsolution.create``,
over throwaway projects. Zero model calls."""
import json
import py_compile
import tempfile
from pathlib import Path

import repo_fixture
from esoi import check, config, declarations, newsolution, registry, tables
from esoi.config import Config


def scan(args):
    with tempfile.TemporaryDirectory(prefix="esoi_scan_") as tmp:
        root = Path(tmp)
        for rel, source in args["files"].items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(source)
        found = declarations.scan(Config(root=root, package="pkg"), sorted(args["files"]))
    return {"solutions": sorted(found.solutions), "implementations": sorted(i.implementation_id for i in found.implementations.values()),
            "ports": {k: v.port for k, v in found.solutions.items() if v.port},
            "parameters": {k: v.parameters for k, v in found.solutions.items()},
            "outputs": {k: v.outputs for k, v in found.solutions.items()}}


def s30(root):
    cfg = config.load(root)
    return [p for p in check.check(cfg) if p.startswith("S30 ")]


def sync_once(root, intent=None):
    cfg = config.load(root)
    return declarations.sync(cfg, registry.load(cfg), declarations.scan(cfg), intent)


def sync(args):
    root = repo_fixture.fresh_repo(args.get("edits", []))
    before = s30(root)
    changes = sync_once(root)
    cfg = config.load(root)
    sid = args.get("solution") or (sorted(declarations.scan(cfg).solutions) or [""])[0]
    row = next((r for r in tables.read_csv(cfg.structure / "solutions.csv") if r["solution_id"] == sid), {})
    out = {"before_count": len(before), "after_count": len(s30(root)), "changes": len(changes), "second": len(sync_once(root)),
           "row": {k: row.get(k, "") for k in ("name", "parameters", "outputs", "selected", "implementations")}}
    keep = args.get("keep")
    if keep:
        out["kept"] = next(r for r in tables.read_csv(root / keep["path"]) if r[keep["key_col"]] == keep["key"])[keep["col"]] == keep["value"]
    return out


def new(args):
    root = repo_fixture.fresh_repo([])
    cfg = config.load(root)
    written = newsolution.create(cfg, args["id"], args.get("intent"))
    refused = False
    try:
        newsolution.create(cfg, args["id"], args.get("intent"))
    except ValueError:
        refused = True
    check.write_docs(config.load(root), say=lambda text: None)
    problems = repo_fixture.report(root)["problems"]
    module = next(w for w in written if w.endswith(".py") and "/impls/" not in w and not w.endswith("score.py") and "__init__" not in w)
    cases = next(w for w in written if w.endswith("cases.json"))
    py_compile.compile(str(root / module), doraise=True)
    json.loads((root / cases).read_text())
    return {"files": sorted(written), "text_only": all("not filled" in p or "no row in the results log" in p for p in problems),
            "valid": True, "refused": refused, "problems": problems}


def build(meter):
    def specify(kind, args):
        return {"scan": scan, "sync": sync, "new": new}[kind](args)
    return specify
