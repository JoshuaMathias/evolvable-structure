"""Record and replay of model calls: an opt-in cassette store for the call meter.

A cassette is a folder holding ``calls.jsonl``, one JSON line per model call: the key (a sha256 of the model, the method,
the arguments that affect the output), the response and what the call originally cost (tokens, dollars, seconds). A later
call with the same key returns the stored response without calling the provider and counts as REPLAYED in the meter
(``calls_replayed`` and the ``replayed_*`` totals), so a row's real spend is only the new calls.

It is off unless asked for (``esoi run ... --cassette DIR`` or ``[harness] cassette = "DIR"`` in the configuration). The file
is plain text and diffable, and holds no request text and no key: only the hash of the request. Whether a repository
commits its cassettes is its own choice; esoi only offers the mechanism. ``esoi cassette stats [DIR]`` lists entries, hits,
misses and size.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

CALLS_FILE = "calls.jsonl"
COUNTS_FILE = "counts.json"
IGNORED_PARAMETERS = ("timeout", "request_id", "metadata", "user", "stream_callback")   # never change what the model says


class CassetteMiss(RuntimeError):
    """A ``--cassette-only`` run needed a model call the cassette does not hold."""


class Uncacheable(ValueError):
    """The call's arguments cannot be turned into a stable key (an object with no JSON form)."""


def request_key(model: Optional[str], method: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    """The sha256 of everything that affects the output: the model, the method, positional and keyword arguments (system,
    messages, parameters). Parameters named in ``IGNORED_PARAMETERS`` are left out. Raises ``Uncacheable`` for an argument with no JSON form."""
    body = {"model": model or "", "method": method, "args": list(args),
            "kwargs": {k: v for k, v in sorted(kwargs.items()) if k not in IGNORED_PARAMETERS}}
    try:
        text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise Uncacheable(str(exc)) from exc
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Cassette:
    """The store: loads ``calls.jsonl`` on open, appends a line per recorded call, keeps hit and miss counts in ``counts.json``."""

    def __init__(self, folder: Path, only: bool = False):
        self.folder = Path(folder)
        self.only = only
        self.entries: Dict[str, Dict[str, Any]] = {}
        path = self.folder / CALLS_FILE
        if path.is_file():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    self.entries[entry["key"]] = entry
                except (ValueError, KeyError, TypeError) as exc:
                    raise ValueError(f"{path} line {number} is not a cassette entry ({exc})") from exc

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.entries.get(key)

    def put(self, key: str, method: str, model: Optional[str], response: Any, usage: Dict[str, Any]) -> bool:
        """Record one call. A response that does not survive a JSON round trip is not recorded (returns False)."""
        try:
            if json.loads(json.dumps(response)) != response:
                return False
        except (TypeError, ValueError):
            return False
        entry = {"key": key, "method": method, "model": model or "", "response": response, "usage": usage}
        self.folder.mkdir(parents=True, exist_ok=True)
        with open(self.folder / CALLS_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        self.entries[key] = entry
        return True

    def count(self, what: str) -> None:
        """Add one ``hits`` or ``misses`` to the counters beside the calls (``counts.json``, safe to leave out of version control)."""
        counts = read_counts(self.folder)
        counts[what] = counts.get(what, 0) + 1
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / COUNTS_FILE).write_text(json.dumps(counts, sort_keys=True) + "\n", encoding="utf-8")


def read_counts(folder: Path) -> Dict[str, int]:
    path = Path(folder) / COUNTS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"hits": int(data.get("hits", 0)), "misses": int(data.get("misses", 0))}
    except (OSError, ValueError, TypeError, AttributeError):
        return {"hits": 0, "misses": 0}


def stats(folder: Path) -> Dict[str, Any]:
    """Entries, size in bytes, hits and misses seen so far, and what the stored calls originally cost."""
    folder = Path(folder)
    path = folder / CALLS_FILE
    opened = Cassette(folder) if path.is_file() else None
    entries = list(opened.entries.values()) if opened else []
    usage = [e.get("usage", {}) for e in entries]
    return {"folder": str(folder), "entries": len(entries), "bytes": path.stat().st_size if path.is_file() else 0,
            **read_counts(folder), "stored_tokens_in": sum(int(u.get("tokens_in", 0)) for u in usage),
            "stored_tokens_out": sum(int(u.get("tokens_out", 0)) for u in usage),
            "stored_cost_usd": round(sum(float(u.get("cost_usd", 0)) for u in usage), 6)}


def run_cli(argv: list, config_cassette: str = "", root: Optional[Path] = None, say: Callable[[str], None] = print) -> int:
    """``esoi cassette stats [DIR]``: DIR defaults to ``[harness] cassette``."""
    if not argv or argv[0] != "stats":
        say("usage: esoi cassette stats [DIR]")
        return 2
    chosen = argv[1] if len(argv) > 1 else config_cassette
    if not chosen:
        say("esoi cassette: name a folder, or set [harness] cassette in the configuration")
        return 2
    folder = Path(chosen)
    if not folder.is_absolute() and root is not None and not folder.exists():
        folder = Path(root) / folder
    found = stats(folder)
    say(f"{found['folder']}: {found['entries']} entries, {found['bytes']} bytes, {found['hits']} hits, {found['misses']} misses; "
        f"stored calls originally cost {found['stored_tokens_in']} in / {found['stored_tokens_out']} out tokens, ${found['stored_cost_usd']}")
    return 0


def timed(call: Callable[[], Any]) -> Tuple[Any, float]:
    started = time.time()
    result = call()
    return result, round(time.time() - started, 3)
