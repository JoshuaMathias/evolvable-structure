from esoi.structure.intent_registry.import_base import import_base


def test_a_relative_import_resolves_against_the_package_of_the_importing_file():
    assert import_base(["a", "b", "c"], 1, "m") == "a.b.c.m"
    assert import_base(["a", "b", "c"], 2, "m") == "a.b.m"
    assert import_base(["a", "b", "c"], 3, None) == "a"
    assert import_base(["a", "b", "c"], 0, "x.y") == "x.y"


def test_an_import_deeper_than_its_package_stops_at_the_top_instead_of_wrapping_around():
    assert import_base(["a", "b", "c"], 5, "m") == "m"
    assert import_base(["a", "b", "c"], 4, None) == ""
