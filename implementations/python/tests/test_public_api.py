"""The public API of esoi (esoi/__init__.py): every name a program that embeds the library imports resolves, so a module can move inside
the package without breaking a caller."""
import importlib

import esoi


def test_every_public_name_resolves():
    missing = []
    for name in esoi.__all__:
        try:
            getattr(esoi, name)
        except Exception as error:
            missing.append(f"{name}: {error}")
    assert missing == []


def test_flat_names_point_at_modules_that_hold_them():
    for name, (module, attribute) in esoi.PUBLIC.items():
        assert hasattr(importlib.import_module(module), attribute), f"{name} -> {module}:{attribute}"


def test_namespaces_hold_only_what_their_modules_define():
    for space, modules in esoi.NAMESPACES.items():
        built = getattr(esoi, space)
        for module, attributes in modules.items():
            for attribute in attributes:
                assert getattr(built, attribute) is getattr(importlib.import_module(module), attribute)


def test_the_selection_decorators_are_importable_by_name():
    from esoi import SelectionError, implementation, override, register, resolve, solution
    assert all(callable(item) for item in (implementation, override, register, resolve, solution)) and issubclass(SelectionError, Exception)


def test_an_unknown_name_is_an_attribute_error():
    try:
        esoi.no_such_name
    except AttributeError as error:
        assert "no_such_name" in str(error)
    else:
        raise AssertionError("an unknown name must raise AttributeError")
