"""Hierarchical defaults (esoi.hierarchy, Assembler(parent=...)), explain, reasons, circumstance entries and rule S35.

A throwaway parent package (``esoihub``: two solutions, two store arms, a snapshot with defaults) and a child (``esoichild``:
one arm of its own for the parent's store solution, a snapshot whose default differs) are written to a temporary folder. Nothing is
read from this repository's records, the process environment or the network.
"""
import json
import sys
import textwrap
from pathlib import Path

import pytest

from esoi import check, hierarchy, runtime
from esoi import config as config_module
from esoi import tables
from esoi.assemble import Assembler, AssemblyConfig, AssemblyError

STORE, INDEX = "hub-store", "hub-index"
HUB_SOLUTIONS = '''
import typing
from typing import runtime_checkable
from esoi import solution


@solution("hub-store")
@runtime_checkable
class Store(typing.Protocol):
    def get(self, key: str) -> str: ...


@solution("hub-index")
@runtime_checkable
class Index(typing.Protocol):
    def find(self, key: str) -> str: ...
'''
HUB_ARMS = '''
from esoi import implementation
from esoihub.solutions import Store


@implementation("hub-store", "memory")
class Memory:
    def get(self, key):
        return "memory:" + key


@implementation("hub-store", "disk")
class Disk:
    def get(self, key):
        return "disk:" + key


@implementation("hub-index", "plain")
class Plain:
    def __init__(self, store: Store):
        self.store = store

    def find(self, key):
        return self.store.get(key)
'''
CHILD_ARMS = '''
from esoi import implementation


@implementation("hub-store", "cached")
class Cached:
    def get(self, key):
        return "cached:" + key
'''


def write_pair(site: Path, child_default: str = "disk") -> None:
    hub = site / "esoihub"
    hub.mkdir(parents=True)
    (hub / "__init__.py").write_text("")
    (hub / "solutions.py").write_text(textwrap.dedent(HUB_SOLUTIONS))
    (hub / "arms.py").write_text(textwrap.dedent(HUB_ARMS))
    (hub / "esoi_selection.json").write_text(json.dumps({
        STORE: {"default": "memory", "modules": {"memory": "esoihub.arms", "disk": "esoihub.arms"}},
        INDEX: {"default": "plain", "modules": {"plain": "esoihub.arms"}}}))
    child = site / "esoichild"
    child.mkdir()
    (child / "__init__.py").write_text("")
    (child / "arms.py").write_text(textwrap.dedent(CHILD_ARMS))
    snapshot = {STORE: {"modules": {"cached": "esoichild.arms"}}}
    if child_default:
        snapshot[STORE]["default"] = child_default
    (child / "esoi_selection.json").write_text(json.dumps(snapshot))


@pytest.fixture
def pair(tmp_path):
    """``(hub, child)`` Assemblers; the child's own default for the store is ``disk`` and the hub's is ``memory``."""
    write_pair(tmp_path)
    sys.path.insert(0, str(tmp_path))
    hub = Assembler("esoihub", tmp_path / "esoihub", modules=("esoihub.solutions", "esoihub.arms"))
    child = Assembler("esoichild", tmp_path / "esoichild", modules=("esoichild.arms",), parent=hub)
    child.prepare()
    yield hub, child
    sys.path.remove(str(tmp_path))
    for name in [m for m in sys.modules if m.split(".")[0] in ("esoihub", "esoichild")]:
        sys.modules.pop(name)
    for key in [k for k in runtime.REGISTRY if k[0] in ("esoihub", "esoichild")]:
        runtime.REGISTRY.pop(key)


def test_one_line_builds_the_hubs_defaults_and_a_child_inherits_them(pair):
    hub, child = pair
    assert hub.assemble_defaults()[INDEX].find("k") == "memory:k"
    built = child.assemble_defaults()
    assert built[INDEX].find("k") == "disk:k"                                       # the child's default, injected into the hub's arm
    assert built.choice(STORE).layer == "esoichild default"
    assert built.choice(INDEX).layer == "esoihub default"                      # nothing differs here: inherited
    assert built.pending == {}


def test_the_layer_order_is_explicit_selections_environ_child_default_parent_default(pair):
    hub, child = pair
    environ = {runtime.env_name(STORE, "esoichild"): "memory"}
    order = [layer.layer for layer in child.explain(STORE, "cached", AssemblyConfig(
        selections={STORE: "disk"}, selection_environ=environ)).layers]
    assert order == ["explicit name", "consumer selections", "selection environ", "esoichild default", "esoihub default"]
    config = AssemblyConfig(selections={STORE: "disk"}, selection_environ=environ)
    assert child.choice(STORE, "cached", config).layer == "explicit name"
    assert child.choice(STORE, config=config).layer == "consumer selections"
    assert child.choice(STORE, config=AssemblyConfig(selection_environ=environ)).layer == "selection environ"
    assert child.choice(STORE).name == "disk" and hub.choice(STORE).name == "memory"


def test_a_child_chooses_among_its_own_names_and_its_parents_and_nothing_else(pair):
    hub, child = pair
    assert child.names(STORE) == ["cached", "disk", "memory"] and hub.names(STORE) == ["disk", "memory"]
    assert child.resolve(STORE, "cached").__name__ == "Cached" and child.resolve(STORE, "memory").__name__ == "Memory"
    with pytest.raises(AssemblyError, match="unknown implementation 'tape'"):
        child.choice(STORE, config=AssemblyConfig(selections={STORE: "tape"}))
    with pytest.raises(AssemblyError, match="unknown implementation 'cached'"):
        hub.choice(STORE, "cached")                                                  # the parent does not see the child's arm


def test_a_child_default_that_is_not_listed_fails_naming_the_scope(tmp_path):
    write_pair(tmp_path, child_default="tape")
    sys.path.insert(0, str(tmp_path))
    try:
        hub = Assembler("esoihub", tmp_path / "esoihub", modules=("esoihub.solutions", "esoihub.arms"))
        child = Assembler("esoichild", tmp_path / "esoichild", modules=("esoichild.arms",), parent=hub)
        with pytest.raises(AssemblyError, match="default 'tape' of 'hub-store' in scope 'esoichild'"):
            child.choice(STORE)
        assert child.choice(STORE, "memory").name == "memory"                         # a higher layer still wins
    finally:
        sys.path.remove(str(tmp_path))
        for name in [m for m in sys.modules if m.split(".")[0] in ("esoihub", "esoichild")]:
            sys.modules.pop(name)
        for key in [k for k in runtime.REGISTRY if k[0] in ("esoihub", "esoichild")]:
            runtime.REGISTRY.pop(key)


def test_explain_lists_every_layer_across_the_child_and_the_parent_and_names_the_winner(pair):
    _, child = pair
    explained = child.explain(STORE, config=AssemblyConfig(selections={STORE: "cached"}, reasons={STORE: ["slow-disk-problem"]}))
    assert explained.winner.layer == "consumer selections" and explained.parent_default == "memory"
    assert [(l.layer, l.name) for l in explained.layers] == [
        ("consumer selections", "cached"), ("esoichild default", "disk"), ("esoihub default", "memory")]
    text = str(explained)
    assert "hub-store: cached (layer: consumer selections)" in text and "-> consumer selections: cached; reasons: slow-disk-problem" in text
    assert "esoihub default: memory [the packaged snapshot]" in text and "overrides the parent default memory" in text
    plain = child.explain(INDEX)
    assert plain.winner.inherited and not plain.overrides_parent


def test_a_reason_is_recorded_in_the_choice_and_the_reason_line(pair):
    _, child = pair
    config = AssemblyConfig(solutions=(INDEX,), selections={STORE: "cached"}, reasons={STORE: ["slow-disk-problem", "unconfirmed: for Joshua to confirm."]})
    built = child.assemble(config)
    assert built.choice(STORE).reasons == ("slow-disk-problem", "unconfirmed: for Joshua to confirm.")
    assert "reasons: slow-disk-problem; unconfirmed: for Joshua to confirm." in built.reason_by_solution[STORE]
    assert built.explain(STORE).winner.reasons == built.choice(STORE).reasons
    assert child.choice(STORE).reasons == ()


def test_overrides_lists_what_differs_from_the_parent_and_whether_a_record_id_justifies_it(pair):
    hub, child = pair
    assert hub.overrides() == []
    found = child.overrides()                                                        # the child's own default differs
    assert [(o.solution_id, o.chosen, o.parent_default, o.layer, o.justified) for o in found] == [
        (STORE, "disk", "memory", "esoichild default", False)]
    chosen = AssemblyConfig(selections={STORE: "memory"})
    assert child.overrides(chosen) == []                                             # choosing the parent's default overrides nothing
    only_text = child.overrides(AssemblyConfig(selections={STORE: "cached"}, reasons={STORE: ["unconfirmed: later."]}))
    assert only_text[0].reasons == ("unconfirmed: later.",) and not only_text[0].justified
    assert child.overrides(AssemblyConfig(selections={STORE: "cached"}, reasons={STORE: ["slow-disk-problem"]}))[0].justified


def test_reasons_are_validated(pair):
    _, child = pair
    for bad in (["Not an id!"], ["unconfirmed:"], [""]):
        with pytest.raises(AssemblyError, match="reasons for 'hub-store'"):
            child.assemble(AssemblyConfig(solutions=(STORE,), selections={STORE: "cached"}, reasons={STORE: bad}))
    with pytest.raises(AssemblyError, match="no arm for it"):
        child.assemble(AssemblyConfig(solutions=(STORE,), reasons={STORE: ["slow-disk-problem"]}))


def test_a_conditional_entry_applies_only_when_the_callers_circumstances_hold(pair):
    _, child = pair
    entries = ["cached@size=large,tier=1", "memory@size=small"]
    pick = lambda facts: child.choice(STORE, config=AssemblyConfig(selections={STORE: entries}, circumstances=facts))
    assert (pick({"size": "large", "tier": 1}).name, pick({"size": "large", "tier": 1}).when) == ("cached", "size=large,tier=1")
    assert pick({"size": "small"}).name == "memory"
    assert pick({"size": "large"}).name == "disk"                                    # tier not given: nothing applies, the default does
    assert pick({}).layer == "esoichild default"
    explained = child.explain(STORE, config=AssemblyConfig(selections={STORE: entries}, circumstances={"size": "large"}))
    assert [l.skipped for l in explained.layers[:2]] == ["circumstance tier=1 not met (tier not given)", "circumstance size=small not met"]
    assert "skip consumer selections: cached when size=large,tier=1 (circumstance tier=1 not met (tier not given))" in str(explained)


def test_a_conditional_value_may_come_from_the_name_or_the_environ_and_a_typo_fails(pair):
    _, child = pair
    facts = {"size": "large"}
    assert child.choice(STORE, "cached@size=large", AssemblyConfig(circumstances=facts)).name == "cached"
    environ = {runtime.env_name(STORE, "esoichild"): "memory@size=large"}
    assert child.choice(STORE, config=AssemblyConfig(selection_environ=environ, circumstances=facts)).layer == "selection environ"
    assert child.choice(STORE, config=AssemblyConfig(selection_environ=environ)).name == "disk"
    for bad in ("cached@", "cached@size", "cached@Size=large", "cached@size=large,size=small", "tape@size=large"):
        with pytest.raises(AssemblyError):
            child.choice(STORE, bad, AssemblyConfig(circumstances=facts))


def test_without_a_parent_nothing_changes_and_explain_still_works(pair):
    hub, _ = pair
    explained = hub.explain(STORE, config=AssemblyConfig(selections={STORE: "disk"}))
    assert [l.layer for l in explained.layers] == ["consumer selections", "esoihub default"]
    assert explained.parent_default == "" and not explained.overrides_parent and hub.overrides() == []
    assert hub.choice(STORE) == runtime.Choice("memory", "esoihub default", "the packaged snapshot")


def test_the_parent_is_prepared_with_the_child_and_a_provided_object_is_checked_against_the_parents_protocol(pair):
    _, child = pair
    class Bad:
        pass
    with pytest.raises(AssemblyError, match="does not satisfy Store"):
        child.assemble(AssemblyConfig(solutions=(STORE,)), provided={STORE: Bad()})


# rule S35

def with_parent(cfg, parent_default="shout"):
    """The scaffolded repository, now built on a parent whose default for its one solution is ``parent_default``."""
    (cfg.root / "parent.json").write_text(json.dumps({"greet-a-person": {"default": parent_default, "modules": {}}}))
    (cfg.root / "esoi.toml").write_text((cfg.root / "esoi.toml").read_text() + '\n[parent]\nsnapshot = "parent.json"\n')
    return config_module.load(cfg.root)


def s35(cfg):
    return [line for line in check.check(cfg) if line.startswith("S35")]


def test_s35_is_silent_without_a_parent_and_when_the_default_is_the_parents(cfg):
    assert s35(cfg) == []
    assert s35(with_parent(cfg, "greet")) == []                                      # the repository selects greet


def test_s35_flags_an_override_without_a_cited_reason_and_accepts_a_record_id_or_a_waiver(cfg):
    cfg = with_parent(cfg)
    found = s35(cfg)
    assert len(found) == 1 and found[0].startswith("S35 greet-a-person: selected is greet but the parent's default is shout")
    (cfg.structure / "overrides.csv").write_text("solution_id,reason_ids\ngreet-a-person,greeting-by-hand\n")
    assert s35(cfg) == []                                                            # an id of this repository's own problem
    (cfg.structure / "overrides.csv").write_text("solution_id,reason_ids\ngreet-a-person,no-such-record\n")
    assert "cites no-such-record" in s35(cfg)[0]
    (cfg.structure / "overrides.csv").unlink()
    tables.write_csv(cfg.structure / "waivers.csv", ["rule", "path", "reason"], tables.read_csv(cfg.structure / "waivers.csv") + [
        {"rule": "S35", "path": "greet-a-person", "reason": "The decision to adopt the parent's default is pending."}])
    assert s35(cfg) == []
    assert not any(line.startswith("S9") for line in check.check(cfg))               # the waiver was used


def test_s35_reports_a_parent_that_cannot_be_read_and_can_be_disabled(cfg):
    cfg = with_parent(cfg)
    (cfg.root / "parent.json").write_text("{")
    assert "[parent] in the configuration cannot be read" in s35(cfg)[0]
    cfg.disable.append("S35")
    assert s35(cfg) == []
    assert "S35" in __import__("esoi.rules", fromlist=["summaries"]).summaries(cfg)


def test_overrides_csv_and_the_parents_defaults_are_read_by_the_hierarchy_module(cfg):
    cfg = with_parent(cfg)
    assert hierarchy.parent_defaults(cfg) == {"greet-a-person": "shout"}
    (cfg.structure / "overrides.csv").write_text("solution_id,reason_ids\ngreet-a-person,a;b\ngreet-a-person,c\n")
    assert hierarchy.read_overrides(cfg) == {"greet-a-person": ("a", "b", "c")}
