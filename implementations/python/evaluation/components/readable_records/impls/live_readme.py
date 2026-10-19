"""CURRENT: the live README generator, ``esoi.readme.render`` as written by ``esoi check --write-docs`` and checked by rule
S8, over throwaway projects. Zero model calls."""
import repo_fixture
from esoi import config


def page(root, folder):
    path = root / folder / "README.md"
    return path.read_text() if path.is_file() else ""


def build(meter):
    def readable(kind, args):
        root = repo_fixture.fresh_repo(args.get("edits", []))
        if kind == "readme":
            return {"text": page(root, "esoi")}
        if kind == "sub":
            return {"text": page(root, "esoi/voices")}
        found = [p for p in repo_fixture.report(root)["problems"] if p.startswith("S8 ") and "README.md" in p]
        return {"stale": len(found), "text": "\n".join(found)}
    return readable
