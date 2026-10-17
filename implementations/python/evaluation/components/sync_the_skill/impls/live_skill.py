"""CURRENT: the live generator and checker, ``esoi.skill`` (``build_copy``, ``sync``, ``check``, ``scan``, ``install``). Zero model calls."""
import tempfile
from pathlib import Path

from esoi import skill
from esoi.config import Config


def write_tree(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def config_for(root, args, copy="copy"):
    table = {"dir": copy, "include": args["include"], "substitute": args.get("substitute", [])}
    return Config(root=root, skill=table)


def run_sync(root, args):
    write_tree(root / "src", args["source"])
    config = config_for(root, args)
    try:
        wanted = skill.build_copy(root / "src", skill.settings_from(config))
    except skill.SkillError as exc:
        return {"files": [], "text": str(exc)}
    return {"files": sorted(wanted), "text": wanted.get("SKILL.md", "")}


def run_drift(root, args):
    write_tree(root / "src", args["source"])
    config = config_for(root, args)
    messages = []
    skill.sync(config, str(root / "src"), say=messages.append)
    change, copy = args["change"], root / "copy"
    if change == "source-edited":
        (root / "src" / "SKILL.md").write_text(args["source"]["SKILL.md"] + "\nA new sentence.\n", encoding="utf-8")
    elif change == "copy-edited":
        (copy / "SKILL.md").write_text((copy / "SKILL.md").read_text(encoding="utf-8") + "\nA hand edit.\n", encoding="utf-8")
    elif change == "copy-extra-file":
        (copy / "extra.md").write_text("not from the source\n", encoding="utf-8")
    elif change == "copy-missing-file":
        next(p for p in sorted(copy.rglob("*.md")) if p.name != "SKILL.md").unlink()
    return {"stale": skill.sync(config, str(root / "src"), check=True, say=messages.append) == 1}


def run_leak(root, args):
    terms = []
    if args.get("denylist"):
        (root / "deny.txt").write_text("\n".join(args["denylist"]), encoding="utf-8")
        terms = skill.load_denylist(str(root / "deny.txt"))
    found = skill.scan(args["files"], terms, args.get("private_dirs", []))
    return {"kinds": sorted({f.kind for f in found})}


def run_install(root, args):
    source = root / "bundled" / "evolvable-structure"
    write_tree(source, {"SKILL.md": "---\nname: x\n---\nbody\n"})
    home = root / "home"
    project = root / "project"
    target = (project / ".claude" / "skills" if args.get("where") == "project" else home) / "evolvable-structure"
    if args["existing"] != "none":
        write_tree(target, {"SKILL.md": "---\nname: x\n---\nbody\n" if args["existing"] == "same" else "something else\n"})
    messages = []
    code = skill.install(project=str(project) if args.get("where") == "project" else None,
                         dest=None if args.get("where") == "project" else str(home), source=str(source),
                         force=args.get("force", False), say=messages.append)
    return {"exit": code, "installed": (target / "SKILL.md").read_text(encoding="utf-8").startswith("---"), "text": " ".join(messages)}


def build(meter):
    def act(kind, args):
        with tempfile.TemporaryDirectory(prefix="esoi_skill_") as tmp:
            return {"sync": run_sync, "drift": run_drift, "leak": run_leak, "install": run_install}[kind](Path(tmp), args)
    return act
