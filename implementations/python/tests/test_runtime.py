"""Declarations in code and the selection cascade (esoi.runtime), end to end over a scaffolded project."""
import importlib
import sys

import pytest

from esoi import implementation, override, runtime, solution
from esoi.runtime import SelectionError


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """No records, no environment: the cascade sees only what a test gives it."""
    monkeypatch.setenv(runtime.ROOT_ENV, str(tmp_path))
    runtime.PROJECTS.clear()
    yield tmp_path
    runtime.PROJECTS.clear()


def test_declare_call_swap_by_name_context_and_environment(isolated, monkeypatch):
    @solution("t-greet")
    def greet(name): ...

    @implementation("t-greet", "plain")
    def plain(name):
        return f"hi {name}"

    @implementation("t-greet", "loud")
    def loud(name):
        return f"HI {name}"

    try:
        monkeypatch.setenv(runtime.env_name("t-greet"), "plain")
        assert greet("a") == "hi a"
        assert greet("a", using="loud") == "HI a"
        with override("t-greet", "loud"):
            assert greet("a") == "HI a" and greet.chosen().layer == "context"
        assert greet.chosen().layer == "environment" and greet.names() == ["loud", "plain"]
        with pytest.raises(SelectionError, match="unknown implementation 'nope'.*named by the call layer.*choices: loud, plain"):
            greet("a", using="nope")
    finally:
        runtime.forget("t-greet")


def test_no_layer_naming_one_fails_loudly(isolated):
    @solution("t-none")
    def none(): ...

    try:
        with pytest.raises(SelectionError, match="no implementation is selected"):
            none()
    finally:
        runtime.forget("t-none")


def test_the_scaffold_example_runs_its_declared_implementation_from_the_records(repo, monkeypatch):
    monkeypatch.delenv(runtime.ROOT_ENV, raising=False)
    monkeypatch.syspath_prepend(str(repo))
    runtime.PROJECTS.clear()
    sys.modules.pop("demo", None)
    sys.modules.pop("demo.greet", None)
    module = importlib.import_module("demo.greet")
    try:
        assert module.greet("Ada") == "Hello, Ada!"
        picked = module.greet.chosen()
        assert (picked.name, picked.layer) == ("greet", "project")
        monkeypatch.setenv(runtime.env_name("greet-a-person"), "ghost")
        with pytest.raises(SelectionError, match="named by the environment layer"):
            module.greet("Ada")
    finally:
        runtime.forget("greet-a-person")
        runtime.PROJECTS.clear()
        sys.modules.pop("demo.greet", None)
        sys.modules.pop("demo", None)


def test_a_snapshot_stands_in_for_the_records_in_a_shipped_package(tmp_path, monkeypatch):
    package = tmp_path / "shipped"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "mod.py").write_text('from esoi import implementation, solution\n\n\n@solution("t-snap")\ndef snap(): ...\n\n\n'
                                    '@implementation("t-snap", "only")\ndef only():\n    return "ran"\n')
    (tmp_path / runtime.SNAPSHOT_NAME).write_text('{"t-snap": {"default": "only", "modules": {"only": "shipped.mod"}}}')
    monkeypatch.delenv(runtime.ROOT_ENV, raising=False)
    monkeypatch.syspath_prepend(str(tmp_path))
    runtime.PROJECTS.clear()
    module = importlib.import_module("shipped.mod")
    try:
        assert module.snap() == "ran" and module.snap.chosen().layer == "project"
    finally:
        runtime.forget("t-snap")
        runtime.PROJECTS.clear()
        sys.modules.pop("shipped.mod", None)
        sys.modules.pop("shipped", None)
