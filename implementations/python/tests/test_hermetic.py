"""The environment guard for evaluations."""
import os

from esoi import hermetic
from esoi.config import Config


def test_matching_variables_are_removed_and_restored(monkeypatch):
    monkeypatch.setenv("APP_X", "1")
    monkeypatch.setenv("SECRET_KEY", "2")
    monkeypatch.setenv("KEEP", "3")
    with hermetic.hermetic_env(["APP_"], ["SECRET_KEY"], {"MODE": "offline"}):
        assert "APP_X" not in os.environ and "SECRET_KEY" not in os.environ
        assert os.environ["KEEP"] == "3" and os.environ["MODE"] == "offline"
    assert os.environ["APP_X"] == "1" and os.environ["SECRET_KEY"] == "2" and "MODE" not in os.environ


def test_from_config_reads_the_hermetic_table(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_X", "1")
    cfg = Config(root=tmp_path, hermetic={"prefixes": ["APP_"], "set": {"APP_MODE": "off"}})
    with hermetic.from_config(cfg, {"EXTRA": "e"}):
        assert "APP_X" not in os.environ and os.environ["APP_MODE"] == "off" and os.environ["EXTRA"] == "e"
