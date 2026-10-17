"""Selection tables and the resolver."""
import pytest

from esoi.select import Selector, load_table

TABLE = {"pick": {"default": "counter", "implementations": {
    "counter": "collections:Counter", "ordered": {"target": "collections:OrderedDict", "config": "dataclasses:dataclass"},
    "broken": "no.such.module:Thing"}}}


def test_default_explicit_and_override_precedence():
    s = Selector(TABLE)
    assert s.resolve("pick").__name__ == "Counter"
    assert s.resolve("pick", "ordered").__name__ == "OrderedDict"
    assert s.resolve("pick", overrides={"pick": "ordered"}).__name__ == "OrderedDict"
    assert s.resolve("pick", "counter", overrides={"pick": "ordered"}).__name__ == "Counter"


def test_unknown_names_fail_loudly_with_the_choices():
    s = Selector(TABLE)
    with pytest.raises(ValueError, match="choices: broken, counter, ordered"):
        s.resolve("pick", "ordred")
    with pytest.raises(ValueError, match="known: \\['pick'\\]"):
        s.resolve("ghost")


def test_targets_load_lazily_and_a_chosen_broken_target_fails():
    s = Selector(TABLE)
    assert s.resolve("pick", "counter")
    with pytest.raises(ModuleNotFoundError):
        s.resolve("pick", "broken")


def test_config_class_and_none():
    s = Selector(TABLE)
    assert s.resolve_config("pick", "ordered").__name__ == "dataclass"
    assert s.resolve_config("pick", "counter") is None


def test_register_adds_and_can_become_the_default():
    s = Selector(TABLE)
    s.register("pick", "Chain", "collections:ChainMap", default=True)
    assert s.default_name("pick") == "chain" and s.resolve("pick").__name__ == "ChainMap"
    assert "chain" in s.names("pick")
    assert Selector(TABLE).default_name("pick") == "counter"


def test_load_table_by_file_path_and_by_module(tmp_path):
    (tmp_path / "table.py").write_text('SELECTION = {"x": {"default": "a", "implementations": {"a": "collections:deque"}}}\n')
    assert Selector(load_table("table.py:SELECTION", tmp_path)).resolve("x").__name__ == "deque"
