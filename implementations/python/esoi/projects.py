"""The local ESOI index: which projects on this machine (or online) ESOI is applied to, how they relate, and where to look.

It is the local counterpart of a skill index, in the way a user's ``.claude`` folder sits beside a skill. The folder
is ``$ESOI_HOME``, else ``~/.esoi/``:

    projects.csv        one row per project, each a top intent somewhere: the machine-readable index
    INDEX.md            generated from projects.csv between two markers; the user's own routing stays outside them
    projects/<id>.md    optional longer notes for one project, written by the user

A project row is ``project_id, name, vision_statement, location, kind, specifications, start_here, relations, notes``.
``location`` is a local path (``~`` allowed) or a URL; ``kind`` is ``repository``, ``folder``, ``file`` or ``board``;
``specifications`` and ``start_here`` are relative to a local ``location``; ``relations`` is ``;``-separated
``<kind>:<project_id>`` with kind ``uses``, ``used-by``, ``sub-intent-of``, ``example-of`` or ``related``.

The project's own top ``intent.csv`` is the single source of its name and vision statement: ``list``, ``index`` and
``where`` read them from it, and the ``name`` and ``vision_statement`` cells of a row are only for a project that has no
top intent record (a URL, a board, a project not yet migrated). ``check`` reports a row whose cells disagree with the
project's ``intent.csv``. ``used-by`` is derived from the ``uses`` of other rows, so only ``uses`` need be written.

Nothing here touches the network: a URL is listed, never fetched. Every function takes the index folder as an
argument; the command line is the one place that reads ``ESOI_HOME``. Standard library only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

from . import config as config_module
from .tables import SEP, ids, read_csv, render_csv

HOME_ENV = "ESOI_HOME"
COLUMNS = ["project_id", "name", "vision_statement", "location", "kind", "specifications", "start_here", "relations", "notes"]
KINDS = ["repository", "folder", "file", "board"]
RELATIONS = ["uses", "used-by", "sub-intent-of", "example-of", "related"]
START = "<!-- esoi-projects:start -->"
END = "<!-- esoi-projects:end -->"
URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
START_HERE_CANDIDATES = ["CLAUDE.md", "esoi/network.md", "structure/network.md", "docs/structure/network.md", "README.md"]
Row = Dict[str, str]


def resolve_home(env: Mapping[str, str], user_home: Path) -> Path:
    """The index folder: ``ESOI_HOME`` when set, else ``.esoi`` in the user's home directory."""
    chosen = env.get(HOME_ENV, "").strip()
    return Path(chosen).expanduser() if chosen else Path(user_home) / ".esoi"


def is_url(location: str) -> bool:
    return bool(URL.match(location))


def local_path(location: str) -> Optional[Path]:
    """The folder or file a local ``location`` names, or None for a URL."""
    return None if is_url(location) else Path(location).expanduser()


def projects_file(home: Path) -> Path:
    return Path(home) / "projects.csv"


def read_projects(home: Path) -> List[Row]:
    return [{c: r.get(c, "") for c in COLUMNS} for r in read_csv(projects_file(home))]


def write_projects(home: Path, rows: List[Row]) -> None:
    Path(home).mkdir(parents=True, exist_ok=True)
    projects_file(home).write_text(render_csv(COLUMNS, rows), encoding="utf-8")


def init(home: Path) -> List[str]:
    """Create the index folder, an empty ``projects.csv`` and ``INDEX.md``; nothing that exists is changed.
    Returns the paths created."""
    home = Path(home)
    made: List[str] = []
    (home / "projects").mkdir(parents=True, exist_ok=True)
    if not projects_file(home).exists():
        write_projects(home, [])
        made.append("projects.csv")
    if not (home / "INDEX.md").exists():
        index(home)
        made.append("INDEX.md")
    return made


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "project"


def guess_kind(location: str) -> str:
    if is_url(location):
        return "repository" if re.search(r"(github|gitlab|bitbucket)|\.git$", location, re.I) else "board"
    path = local_path(location)
    if path is not None and path.is_file():
        return "file"
    return "repository" if path is not None and (path / ".git").exists() else "folder"


def home_relative(path: Path) -> str:
    """A path as ``~/...`` when it lies under the user's home directory, so the index holds no machine-specific prefix."""
    try:
        return "~/" + path.resolve().relative_to(Path.home().resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def project_config(root: Path) -> Optional[config_module.Config]:
    """The configuration kept in ``root`` itself (``esoi.toml``, else ``[tool.esoi]`` in ``pyproject.toml``), or None
    when ``root`` has none or it does not load. A configuration of a parent folder is not this project's."""
    found = config_module.find(root)
    if found is None or found.parent != Path(root).resolve():
        return None
    try:
        return config_module.load(found)
    except config_module.ConfigError:
        return None


def structure_of(root: Path) -> Tuple[str, Optional[Path]]:
    """(specifications entry, the folder holding the top intent) for a local project: the structure folder its
    configuration names, else ``esoi``, ``structure`` or ``docs/structure``, else nothing."""
    loaded = project_config(root)
    if loaded is not None:
        return (loaded.source.name if loaded.source else config_module.CONFIG_NAME, loaded.structure)
    try:
        folder, _ = config_module.resolve_structure_dir(root)
    except config_module.ConfigError:
        return ("", None)
    if config_module.holds_specifications(root / folder):
        return (folder + "/", root / folder)
    return ("", None)


def describe(root: Path) -> Tuple[str, str]:
    """(name, vision statement) of the project at ``root``, read from its top ``intent.csv``; empty strings when it has
    none. A project without a top intent record (a legacy one) states its name in the index instead; nothing is guessed
    from its other records."""
    _, folder = structure_of(root)
    if folder is None:
        return ("", "")
    intent = read_csv(folder / "intent.csv")
    return (intent[0].get("name", ""), intent[0].get("vision_statement", "")) if intent else ("", "")


def resolve(rows: List[Row]) -> List[Row]:
    """The rows with name and vision statement read from each local project's top ``intent.csv`` where it has one
    (an empty cell of the intent leaves the row's own); the rows are copied."""
    out = []
    for row in rows:
        row = dict(row)
        root = local_path(row["location"])
        if root is not None and root.is_dir():
            name, vision = describe(root)
            row["name"], row["vision_statement"] = name or row["name"], vision or row["vision_statement"]
        out.append(row)
    return out


def add(home: Path, location: str, project_id: str = "", name: str = "", vision: str = "", kind: str = "",
        specifications: str = "", start_here: str = "", relations: str = "", notes: str = "",
        replace: bool = False) -> Row:
    """Add (or with ``replace`` update) one project. The specifications and first file are found in the project when it
    is a local folder. Its name and vision statement stay in its own top ``intent.csv`` and are left out of the row; a
    project without one (a URL, a board, a legacy project) gets them from the flags, the name defaulting to the folder
    name."""
    home = Path(home)
    path = local_path(location)
    if path is not None and path.exists():
        path = path.resolve()
    stored = location if is_url(location) else home_relative(path) if path is not None and path.exists() else location
    own_name, own_vision, guessed_spec, guessed_start = "", "", "", ""
    if path is not None and path.is_dir():
        own_name, own_vision = describe(path)
        guessed_spec = structure_of(path)[0]
        guessed_start = next((c for c in START_HERE_CANDIDATES if (path / c).exists()), "")
    base = path.name if path is not None and path.name else location.rstrip("/").rsplit("/", 1)[-1]
    # a project that has a top intent record keeps its name and vision there, so the row holds them only when given
    row = {"project_id": project_id or slug(name or own_name or base),
           "name": name or ("" if own_name else base), "vision_statement": vision,
           "location": stored, "kind": kind or guess_kind(location), "specifications": specifications or guessed_spec,
           "start_here": start_here or guessed_start, "relations": relations, "notes": notes}
    rows = read_projects(home)
    same = [i for i, r in enumerate(rows) if r["project_id"] == row["project_id"]]
    if same and not replace:
        raise ValueError(f"project {row['project_id']!r} is already in the index (use --replace to update it)")
    if same:
        rows[same[0]] = row
    else:
        rows.append(row)
    write_projects(home, rows)
    return row


def check(home: Path) -> List[str]:
    """Problems found in the index: bad or repeated ids, unknown kinds, relations that do not resolve, and local
    locations, specifications or start files that do not exist. URLs are not fetched, so they are only listed."""
    home = Path(home)
    if not projects_file(home).exists():
        return [f"{projects_file(home).name}: not found in {home.name} (run `esoi projects init`)"]
    rows = read_projects(home)
    known = [r["project_id"] for r in rows]
    bad: List[str] = []
    sources = {r["project_id"]: describe(root) for r in rows
               if (root := local_path(r["location"])) is not None and root.is_dir()}
    for ident in sorted({i for i in known if known.count(i) > 1}):
        bad.append(f"{ident}: project_id appears more than once")
    for r in rows:
        ident = r["project_id"]
        if not ident:
            bad.append("a row has no project_id")
            continue
        own_name, own_vision = sources.get(ident, ("", ""))
        for column, source in (("name", own_name), ("vision_statement", own_vision)):
            if source and r[column].strip() and r[column].strip() != source.strip():
                bad.append(f"{ident}: {column} {r[column].strip()!r} disagrees with the top intent.csv of the project "
                           f"({source.strip()!r}); empty the cell, the intent.csv is the source")
        if not r["name"].strip() and not own_name.strip():
            bad.append(f"{ident}: name is empty (the project has no top intent.csv with one)")
        for column in ("location", "kind"):
            if not r[column].strip():
                bad.append(f"{ident}: {column} is empty")
        if r["kind"] and r["kind"] not in KINDS:
            bad.append(f"{ident}: kind {r['kind']!r} is not one of {', '.join(KINDS)}")
        for entry in ids(r["relations"]):
            kind, _, target = entry.partition(":")
            if kind not in RELATIONS:
                bad.append(f"{ident}: relation {entry!r} has kind {kind!r}, not one of {', '.join(RELATIONS)}")
            elif target not in known:
                bad.append(f"{ident}: relation {entry!r} names {target!r}, which is not a project in the index")
            elif target == ident:
                bad.append(f"{ident}: relation {entry!r} names the project itself")
        root = local_path(r["location"])
        if root is None:
            continue
        if not root.exists():
            bad.append(f"{ident}: location {r['location']} does not exist")
            continue
        for column in ("specifications", "start_here"):
            if r[column].strip() and root.is_dir() and not (root / r[column]).exists():
                bad.append(f"{ident}: {column} {r[column]!r} does not exist under {r['location']}")
    return bad


def relations_of(rows: List[Row]) -> List[Tuple[str, str, str]]:
    """Every ``(project, kind, target)`` the rows state, plus the ``used-by`` that follows from another row's ``uses``,
    each once, so a relation need only be written on one side."""
    found: List[Tuple[str, str, str]] = []
    for r in rows:
        for entry in ids(r["relations"]):
            kind, _, target = entry.partition(":")
            found.append((r["project_id"], kind, target))
            if kind == "uses":
                found.append((target, "used-by", r["project_id"]))
    return list(dict.fromkeys(found))


def render_block(rows: List[Row]) -> str:
    """The generated part of INDEX.md: a table of the projects and how they relate."""
    lines = [START, "", "Generated from `projects.csv` by `esoi projects index`; edit the CSV, not this block.", ""]
    if not rows:
        lines += ["No projects yet. Add one with `esoi projects add <path-or-url>`.", ""]
    else:
        lines += ["| Project | Vision | Kind | Location | Start here | Specifications |", "|---|---|---|---|---|---|"]
        for r in rows:
            def cell(key: str) -> str:
                return r[key].replace("|", "/").replace("\n", " ")
            lines.append(f"| `{r['project_id']}` {cell('name')} | {cell('vision_statement')} | {cell('kind')} | "
                         f"{cell('location')} | {cell('start_here')} | {cell('specifications')} |")
        lines.append("")
        related = relations_of(rows)
        if related:
            lines += ["How they relate:", ""]
            lines += [f"- `{ident}` {kind} `{target}`" for ident, kind, target in related]
            lines.append("")
        notes = [r for r in rows if r["notes"].strip()]
        if notes:
            lines += ["What differs when applying ESOI:", ""]
            lines += [f"- `{r['project_id']}`: {r['notes'].strip()}" for r in notes]
            lines.append("")
    lines.append(END)
    return "\n".join(lines)


NEW_INDEX = """# ESOI index

Where ESOI is applied on this machine. The table between the markers is generated; write your own routing (which skills or
playbooks to read for a kind of task in a project) above or below it, where `esoi projects index` leaves it alone.

"""


def index(home: Path) -> Path:
    """Write ``INDEX.md``: replace the block between the markers and keep every other line. A file without the
    markers gets the block appended; no file gets a short header and the block."""
    home = Path(home)
    path = home / "INDEX.md"
    block = render_block(resolve(read_projects(home)))
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if START in text and END in text:
            head, _, rest = text.partition(START)
            tail = rest.partition(END)[2]
            text = head + block + tail
        else:
            text = text.rstrip("\n") + "\n\n" + block + "\n"
    else:
        text = NEW_INDEX + block + "\n"
    home.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def where(home: Path, target: Path) -> Optional[Row]:
    """The project that contains ``target`` (the deepest one when several do), or None. Its name and vision statement
    come from its top ``intent.csv`` where it has one."""
    target = Path(target).resolve()
    best: Optional[Row] = None
    depth = -1
    rows = read_projects(home)
    for r in rows:
        root = local_path(r["location"])
        if root is None or not root.exists():
            continue
        root = root.resolve()
        if target == root or root in target.parents:
            if len(root.parts) > depth:
                best, depth = r, len(root.parts)
    if best is None:
        return None
    resolved = resolve([best])[0]
    derived = [f"{kind}:{target}" for owner, kind, target in relations_of(rows) if owner == best["project_id"]]
    resolved["relations"] = SEP.join(dict.fromkeys(derived))
    return resolved


def render_where(row: Row) -> List[str]:
    """The lines ``esoi projects where`` prints for a project: what it is, and where to start."""
    root = local_path(row["location"])
    base = root if root is not None else Path(".")

    def full(entry: str) -> str:
        return str(base / entry) if entry and root is not None else entry
    lines = [f"{row['project_id']}: {row['name']}", f"  vision: {row['vision_statement']}", f"  location: {row['location']}"]
    if row["start_here"]:
        lines.append(f"  start here: {full(row['start_here'])}")
    if row["specifications"]:
        lines.append(f"  specifications: {full(row['specifications'])}")
    if row["relations"]:
        lines.append(f"  relations: {row['relations'].replace(SEP, ', ')}")
    if row["notes"]:
        lines.append(f"  notes: {row['notes']}")
    return lines


def render_list(rows: List[Row]) -> List[str]:
    return [f"{r['project_id']}  {r['kind']}  {r['location']}  {r['name']}" for r in rows]
