"""Configuration: file discovery, the pyproject table, unknown keys, nested layers, module paths."""
import pytest

from esoi import config


def test_defaults_follow_the_package_name(tmp_path):
    cfg = config.from_mapping({"package": "mylib"}, tmp_path)
    assert cfg.package_dir == "mylib" and cfg.code_paths == ["mylib"] and cfg.live_imports == ["mylib"]
    assert cfg.results == "evaluation/components/results.csv"


def test_load_reads_esoi_toml_and_finds_it_from_a_subfolder(tmp_path):
    (tmp_path / "esoi.toml").write_text('package = "mylib"\nmax_lines = 10\n')
    (tmp_path / "a" / "b").mkdir(parents=True)
    cfg = config.load(start=tmp_path / "a" / "b")
    assert cfg.max_lines == 10 and cfg.root == tmp_path.resolve()


def test_load_reads_the_tool_table_of_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.esoi]\npackage = "mylib"\n')
    assert config.load(tmp_path).package == "mylib"


def test_a_pyproject_without_the_table_is_not_a_config(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    with pytest.raises(config.ConfigError):
        config.load(tmp_path)


def test_an_unknown_key_is_an_error(tmp_path):
    with pytest.raises(config.ConfigError, match="pakage"):
        config.from_mapping({"pakage": "x"}, tmp_path)


def test_layers_may_share_a_rank(tmp_path):
    cfg = config.from_mapping({"layers": ["core", ["cli", "tools"]]}, tmp_path)
    assert cfg.layer_rank == {"core": 0, "cli": 1, "tools": 1}
    assert {"core", "cli", "tools", "docs"} <= cfg.component_layers


def test_a_layer_listed_twice_is_an_error(tmp_path):
    with pytest.raises(config.ConfigError):
        config.from_mapping({"layers": ["core", "core"]}, tmp_path)


def test_module_path_maps_the_package_to_its_folder(tmp_path):
    cfg = config.from_mapping({"package": "mylib", "package_dir": "src/mylib"}, tmp_path)
    assert cfg.module_path("mylib.core.thing") == "src/mylib/core/thing.py"
    assert cfg.module_path("other.mod") == "other/mod.py"


def test_template_source_comes_from_the_override_then_the_environment_then_the_config(tmp_path, monkeypatch):
    cfg = config.from_mapping({"template_source": "from_config.md"}, tmp_path)
    assert cfg.template_source_path() == tmp_path.resolve() / "from_config.md"
    monkeypatch.setenv(config.TEMPLATE_ENV, "from_env.md")
    assert cfg.template_source_path().name == "from_env.md"
    assert cfg.template_source_path("given.md").name == "given.md"
    monkeypatch.delenv(config.TEMPLATE_ENV)
    assert config.from_mapping({}, tmp_path).template_source_path() is None


def test_the_default_folder_is_esoi_and_structure_folders_work_when_configured(tmp_path):
    assert config.from_mapping({}, tmp_path).structure_dir == "esoi" == config.DEFAULT_STRUCTURE_DIR
    assert config.from_mapping({"structure_dir": "docs/structure"}, tmp_path).structure == tmp_path.resolve() / "docs" / "structure"


def test_selection_is_a_legacy_table_string_or_a_table_of_deployment_choices(tmp_path):
    legacy = config.from_mapping({"selection": "pkg/table.py:SELECTION"}, tmp_path)
    assert legacy.selection_table == "pkg/table.py:SELECTION" and legacy.selection_choices == {}
    both = config.from_mapping({"selection": {"table": "pkg/table.py:SELECTION", "greet-a-person": "loud"}}, tmp_path)
    assert both.selection_table == "pkg/table.py:SELECTION" and both.selection_choices == {"greet-a-person": "loud"}
    assert config.from_mapping({}, tmp_path).selection_table == ""
