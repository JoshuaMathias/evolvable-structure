"""Build the on-disk world of one case: the project folders. Shared by every arm so they all face the same machine."""
import tempfile
from pathlib import Path

from esoi import tables


def make_world(projects):
    """Create each project's folder under a fresh root; returns the root. Nothing here is real."""
    root = Path(tempfile.mkdtemp(prefix="esoi_world_"))
    for project in projects:
        if not project.get("dir"):
            continue
        folder = root / project["dir"]
        (folder / "docs" / "structure").mkdir(parents=True)
        (folder / "esoi.toml").write_text('structure_dir = "docs/structure"\n')
        tables.write_csv(folder / "docs" / "structure" / "intent.csv",
                         ["intent_id", "name", "vision_statement", "implements", "opportunity"],
                         [dict(intent_id=project["id"], name=project["name"], vision_statement=project["vision"])])
        for rel, text in project.get("files", {}).items():
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            (folder / rel).write_text(text)
    return root
