"""Every reader of Python source shares one parse per file and one walk per tree, so a check that asks many questions of the same files reads them once."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

from shared_fixtures import repo_fixture
from esoi.structure.intent_registry import config, parsed_source
from esoi.structure.structure_check import check


def test_a_file_is_parsed_once_and_again_only_after_it_changes(tmp_path):
    path = tmp_path / "module.py"
    path.write_text("x = 1\n")
    parsed_source.TREES.clear()
    before = parsed_source.STATS["parses"]
    first = parsed_source.tree_of(path)
    assert parsed_source.tree_of(path) is first
    assert parsed_source.STATS["parses"] - before == 1
    path.write_text("x = 1\ny = 2\n")
    assert len(parsed_source.tree_of(path).body) == 2
    assert parsed_source.STATS["parses"] - before == 2


def test_a_file_that_cannot_be_read_or_parsed_has_no_tree(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def (:\n")
    assert parsed_source.tree_of(broken) is None
    assert parsed_source.tree_of(tmp_path / "missing.py") is None


def test_a_tree_is_walked_once_in_the_order_ast_walk_gives(tmp_path):
    path = tmp_path / "module.py"
    path.write_text("import os\n\n\ndef f(a):\n    return os.path.join(a, 'b')\n")
    tree = parsed_source.tree_of(path)
    nodes = parsed_source.nodes_of(tree)
    assert nodes is parsed_source.nodes_of(tree)
    assert list(nodes) == list(ast.walk(tree))


def test_one_check_parses_no_file_twice():
    root = repo_fixture.fresh_repo([])
    parsed_source.TREES.clear()
    before = parsed_source.STATS["parses"]
    check.check_all(config.load(root))
    files = len(list(root.rglob("*.py")))
    assert 0 < parsed_source.STATS["parses"] - before <= files
