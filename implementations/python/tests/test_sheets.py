"""The sheet sync: the pure merge, tab discovery and a full sync against a fake API."""
import json

import pytest

from esoi import sheets
from esoi.config import Config


def row(i, **kw):
    return dict(id=i, **kw)


def test_a_change_on_one_side_takes_that_side():
    header = ["id", "v"]
    base = {"1": sheets.row_hash(header, row("1", v="a"))}
    _, rows, log = sheets.merge(header, [row("1", v="a")], header, [row("1", v="b")], base, "R-", "id")
    assert rows == [row("1", v="b")] and "changed in sheet" in log[0]
    _, rows, log = sheets.merge(header, [row("1", v="c")], header, [row("1", v="a")], base, "R-", "id")
    assert rows == [row("1", v="c")] and "changed in CSV" in log[0]


def test_a_change_on_both_sides_prefers_the_sheet_and_prints_the_csv_version():
    header = ["id", "v"]
    base = {"1": sheets.row_hash(header, row("1", v="a"))}
    _, rows, log = sheets.merge(header, [row("1", v="c")], header, [row("1", v="s")], base, "R-", "id")
    assert rows == [row("1", v="s")] and "CONFLICT 1" in log[0] and '"v": "c"' in log[0]


def test_new_deleted_and_blank_id_rows():
    header = ["id", "v"]
    base = {"1": sheets.row_hash(header, row("1", v="a")), "2": sheets.row_hash(header, row("2", v="b"))}
    _, rows, log = sheets.merge(header, [row("1", v="a"), row("3", v="n")], header, [row("2", v="b"), row("", v="blank")], base, "R-", "id")
    ids = [r["id"] for r in rows]
    assert "3" in ids and "1" not in ids and "2" not in ids and "R-001" in ids
    assert any("deleted in sheet" in line for line in log) and any("deleted in CSV" in line for line in log)


def test_next_id_continues_the_numbering():
    assert sheets.next_id("P-", ["P-002", "P-010", "other"]) == "P-011"
    assert sheets.next_id("P-", []) == "P-001"


class FakeApi:
    def __init__(self, tabs):
        self.tabs = tabs
        self.formatted = []

    def ensure_tabs(self, wanted):
        for title in wanted:
            self.tabs.setdefault(title, ([], []))

    def read(self, title):
        return self.tabs[title]

    def write(self, title, header, rows):
        self.tabs[title] = (header, [dict(r) for r in rows])

    def format(self, titles, headers):
        self.formatted = titles


def config_for(tmp_path):
    (tmp_path / "t.csv").write_text("id,v\n1,a\n2,b\n")
    return Config(root=tmp_path, sheets={"tabs": {"Things": {"csv": "t.csv", "key": "id", "prefix": "T-"}}})


def test_first_sync_pushes_the_csv_and_records_the_state(tmp_path):
    cfg, api = config_for(tmp_path), FakeApi({})
    assert sheets.run_sync(cfg, api, "sync", say=lambda text: None) == 0
    assert [r["id"] for r in api.tabs["Things"][1]] == ["1", "2"] and api.formatted == ["Things"]
    assert set(json.loads((tmp_path / ".esoi_sync_state.json").read_text())["Things"]["rows"]) == {"1", "2"}


def test_a_sheet_edit_reaches_the_csv_on_the_next_sync(tmp_path):
    cfg, api = config_for(tmp_path), FakeApi({})
    sheets.run_sync(cfg, api, "sync", say=lambda text: None)
    api.tabs["Things"] = (["id", "v"], [dict(id="1", v="edited"), dict(id="2", v="b"), dict(id="", v="added")])
    sheets.run_sync(cfg, api, "sync", say=lambda text: None)
    text = (tmp_path / "t.csv").read_text()
    assert "1,edited" in text and "T-001,added" in text


def test_dry_run_writes_nothing(tmp_path):
    cfg, api = config_for(tmp_path), FakeApi({})
    lines = []
    assert sheets.run_sync(cfg, api, "sync", dry_run=True, say=lines.append) == 0
    assert api.tabs == {} and not (tmp_path / ".esoi_sync_state.json").exists() and lines[-1].startswith("dry run")


def test_a_missing_csv_is_skipped_not_read_as_all_deleted(tmp_path):
    cfg = Config(root=tmp_path, sheets={"tabs": {"Gone": {"csv": "gone.csv", "key": "id"}}})
    lines = []
    sheets.run_sync(cfg, FakeApi({}), "sync", say=lines.append)
    assert any("SKIPPED" in line for line in lines)


def test_duplicate_ids_stop_the_sync(tmp_path):
    cfg = config_for(tmp_path)
    (tmp_path / "t.csv").write_text("id,v\n1,a\n1,b\n")
    with pytest.raises(SystemExit):
        sheets.run_sync(cfg, FakeApi({}), "sync", say=lambda text: None)


def test_tabs_default_to_the_five_tracker_tabs_and_settings_come_from_the_environment(tmp_path, monkeypatch):
    cfg = Config(root=tmp_path)
    assert list(sheets.tabs_from(cfg)) == ["Problems", "Solutions", "Implementations", "Ideals", "Metrics"]
    with pytest.raises(SystemExit):
        sheets.settings(cfg)
    monkeypatch.setenv("ESOI_SHEET_ID", "abc")
    monkeypatch.setenv("ESOI_SHEETS_CREDENTIALS", "~/key.json")
    assert sheets.settings(cfg)[0] == "abc"


def test_check_compares_ids(tmp_path):
    cfg, api = config_for(tmp_path), FakeApi({})
    sheets.run_sync(cfg, api, "push", say=lambda text: None)
    assert sheets.run_check(cfg, api, say=lambda text: None) is True
    api.tabs["Things"] = (["id", "v"], [dict(id="9", v="x")])
    assert sheets.run_check(cfg, api, say=lambda text: None) is False
