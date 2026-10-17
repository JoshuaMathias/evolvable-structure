"""CURRENT: the live reader, ``esoi.template`` (``parse``, ``render_template_csv`` and ``stale_against_source``).
Zero model calls."""
import tempfile
from pathlib import Path

from esoi import template
from esoi.config import Config


def keys_of(rows):
    out = {}
    for row in rows:
        if row["group"] == "meta":
            continue
        out.setdefault(row["entity"], {"required": [], "interface": []})
        out[row["entity"]]["required" if row["group"] == "specify" else "interface"].append(row["field_key"])
    return out


def build(meter):
    def read(kind, args):
        rows, notes = template.parse(args["text"])
        if kind == "parse":
            return {"keys": keys_of(rows), "text": " | ".join(notes)}
        with tempfile.TemporaryDirectory(prefix="esoi_tpl_") as tmp:
            source = Path(tmp) / "SKILL.md"
            source.write_text(args["text"])
            config = Config(root=Path(tmp), template_source="SKILL.md")
            config.structure.mkdir(parents=True)
            committed = template.render_template_csv(rows)
            if args.get("committed") == "edited":
                committed = committed.replace("problem,", "problem_x,", 1)
            template.template_csv_path(config).write_text(committed)
            return {"stale": bool(template.stale_against_source(config))}
    return read
