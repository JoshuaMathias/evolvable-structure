"""Per-module facts and the cache that makes a second `esoi check` fast."""
import json

from esoi import tables
from esoi.rules import modulefacts

SOURCE = '''"""A module."""
import os
import pkg.sub.thing
from pkg import other
from . import sibling
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.hidden import nothing


def read():
    return os.environ.get("X")
'''


def test_scan_reads_the_docstring_imports_and_environment_in_one_pass(tmp_path):
    path = tmp_path / "m.py"
    path.write_text(SOURCE)
    facts = modulefacts.scan(path)
    assert facts.docstring and facts.parsed and facts.lines == len(SOURCE.splitlines())
    assert [i[2] for i in facts.imports] == ["pkg", None, "typing"]
    assert [p[1] for p in facts.plain] == ["os", "pkg.sub.thing"]
    assert facts.env == [13]
    assert "hidden" not in json.dumps(facts.__dict__)


def test_a_module_that_does_not_parse_is_reported_as_such(tmp_path):
    path = tmp_path / "bad.py"
    path.write_text("def (\n")
    assert modulefacts.scan(path).parsed is False
    assert modulefacts.scan(tmp_path / "missing.py").parsed is False


def test_the_cache_reuses_unchanged_files_and_rereads_changed_ones(tmp_path):
    (tmp_path / "m.py").write_text('"""A."""\n')
    cache = modulefacts.Cache(tmp_path)
    assert cache.get("m.py").docstring and cache.dirty
    cache.save()
    assert (tmp_path / ".esoi_cache" / "modules.json").exists()
    again = modulefacts.Cache(tmp_path)
    assert again.get("m.py").docstring and not again.dirty
    (tmp_path / "m.py").write_text("x = 1\nmore = 2\n")
    assert not again.get("m.py").docstring and again.dirty


def test_a_disabled_cache_writes_nothing(tmp_path):
    (tmp_path / "m.py").write_text('"""A."""\n')
    cache = modulefacts.Cache(tmp_path, enabled=False)
    cache.get("m.py")
    cache.save()
    assert not (tmp_path / ".esoi_cache").exists()


def test_memo_is_kept_until_its_key_changes(tmp_path):
    cache = modulefacts.Cache(tmp_path)
    calls = []
    assert cache.memo("scan", "k1", lambda: calls.append(1) or {"v": 1}) == {"v": 1}
    assert cache.memo("scan", "k1", lambda: calls.append(1) or {"v": 2}) == {"v": 1}
    assert cache.memo("scan", "k2", lambda: calls.append(1) or {"v": 3}) == {"v": 3} and len(calls) == 2
    cache.save()
    assert modulefacts.Cache(tmp_path).memo("scan", "k2", lambda: {"v": 9}) == {"v": 3}


def test_prefetch_scans_many_cold_modules_in_parallel(tmp_path):
    names = [f"m{i}.py" for i in range(modulefacts.PARALLEL_FROM + 5)]
    for name in names:
        (tmp_path / name).write_text('"""A."""\nimport os\n')
    cache = modulefacts.Cache(tmp_path)
    cache.prefetch(names)
    assert all(cache.fresh(n) for n in names) and cache.get(names[0]).docstring


def test_the_cache_folder_is_never_a_repository_file(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / ".esoi_cache").mkdir()
    (tmp_path / ".esoi_cache" / "modules.json").write_text("{}")
    assert tables.repo_files(tmp_path) == ["a.txt"]


def test_ctx_memo_is_invalidated_by_a_change_to_a_named_file(cfg):
    from esoi import check
    ctx = check.build_context(cfg)
    calls = []
    first = ctx.memo("n", ["demo/*.py"], lambda: calls.append(1) or ["a"])
    assert ctx.memo("n", ["demo/*.py"], lambda: calls.append(1) or ["b"]) == first and len(calls) == 1
    (cfg.root / "demo" / "greet.py").write_text('"""Changed."""\n')
    assert ctx.memo("n", ["demo/*.py"], lambda: calls.append(1) or ["c"]) == ["c"]
