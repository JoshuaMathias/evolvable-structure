"""The consumer check: options, ports, conformance, pins and the solution tables."""
import hashlib
import sys

from esoi import consumer
from esoi.consumer import Options


def library(tmp_path):
    root = tmp_path / "lib"
    (root / "libx").mkdir(parents=True)
    (root / "libx" / "__init__.py").write_text('"""Lib."""\n')
    (root / "libx" / "ports.py").write_text('"""Ports."""\nfrom typing import Protocol\n\n\nclass Sink(Protocol):\n    def escalate(self, item): ...\n')
    sys.path.insert(0, str(root))
    return Options(library="libx", column_prefix="lib", port_modules=["libx.ports"], pin_name="lib-x")


def write_registry(path, rows):
    cols = ["integration_id", "module", "symbol", "lib_solution_id", "lib_port", "lib_symbol", "kind", "selected_by", "metric",
            "tests", "status", "gap", "action"]
    path.write_text(",".join(cols) + "\n" + "".join(",".join(r.get(c, "") for c in cols) + "\n" for r in rows))


def test_required_columns_use_the_prefix():
    assert "qq_port" in Options(library="x", column_prefix="qq").required_columns


def test_options_come_from_the_config_table_or_the_flag(tmp_path):
    from esoi.config import Config
    cfg = Config(root=tmp_path, consumer={"library": "libx", "column_prefix": "z"})
    assert Options.from_config(cfg).column_prefix == "z"
    assert Options.from_config(Config(root=tmp_path), "other").library == "other"
    try:
        Options.from_config(Config(root=tmp_path))
    except ValueError as exc:
        assert "no library" in str(exc)


def test_a_conforming_implementation_passes_and_drift_is_named(tmp_path):
    options = library(tmp_path)
    (tmp_path / "good_sink.py").write_text("class Sink:\n    def escalate(self, item):\n        return None\n")
    (tmp_path / "bad_sink.py").write_text("class Sink:\n    def escalate(self, thing):\n        return None\n")
    (tmp_path / "t.py").write_text("")
    row = dict(integration_id="a", module="good_sink", symbol="Sink", lib_port="Sink", kind="implementation",
               selected_by="hand", metric="proof", tests="t.py", status="done")
    write_registry(tmp_path / "r.csv", [row, dict(row, integration_id="b", module="bad_sink")])
    report = consumer.check_consumer(tmp_path / "r.csv", tmp_path, options)
    assert any(p.startswith("C3 b") and "'item'" in p for p in report.problems)
    assert not any(p.startswith("C3 a") for p in report.problems)
    assert report.counts == {"implementation": 2}


def test_call_rows_must_resolve_and_duplicates_need_an_action(tmp_path):
    options = library(tmp_path)
    base = dict(module="", selected_by="hand", metric="proof", status="done")
    write_registry(tmp_path / "r.csv", [dict(base, integration_id="c", kind="call", lib_symbol="libx.ports:Nope"),
                                        dict(base, integration_id="d", kind="duplicate"),
                                        dict(base, integration_id="e", kind="call", lib_symbol="libx.ports:Sink")])
    problems = consumer.check_consumer(tmp_path / "r.csv", tmp_path, options).problems
    assert any(p.startswith("C4 c") for p in problems) and any(p.startswith("C5 d") for p in problems)
    assert not any(" e:" in p for p in problems)


def test_missing_columns_stop_the_check(tmp_path):
    (tmp_path / "r.csv").write_text("integration_id,module\nx,y\n")
    assert consumer.check_consumer(tmp_path / "r.csv", tmp_path, Options(library="libx")).problems[0].startswith("C1")


def test_read_pin_accepts_dashes_or_underscores(tmp_path):
    options = Options(library="lib_x", pin_name="lib-x")
    req = tmp_path / "requirements.txt"
    req.write_text("lib_x @ git+https://example.org/x.git@61d93e6e4eb09ae926b23ee704c91912cefbc331\n")
    assert consumer.read_pin(req, options) == "61d93e6e4eb09ae926b23ee704c91912cefbc331"
    assert consumer.read_pin(tmp_path / "none.txt", options) is None


def test_solution_and_result_tables(tmp_path):
    options = library(tmp_path)
    (tmp_path / "cases.json").write_text("[]")
    digest = consumer.cases_hash(["cases.json"], tmp_path)
    assert digest == hashlib.sha256(b"cases.json[]").hexdigest()[:12]
    (tmp_path / "t.py").write_text("")
    (tmp_path / "ok_sink.py").write_text("class Sink:\n    def escalate(self, item):\n        return None\n")
    row = dict(integration_id="a", module="ok_sink", symbol="Sink", lib_port="Sink", kind="implementation", selected_by="h",
               metric="p", tests="t.py", status="done")
    cols = ["integration_id", "module", "symbol", "lib_solution_id", "lib_port", "lib_symbol", "kind", "selected_by", "metric",
            "tests", "status", "gap", "action", "solution_id"]
    (tmp_path / "r.csv").write_text(",".join(cols) + "\n" + ",".join(row.get(c, "") if c != "solution_id" else "s" for c in cols) + "\n")
    (tmp_path / "s.csv").write_text("solution_id,selected,metric_files,component,component_impl\n"
                                    "s,x,cases.json,,\n")
    (tmp_path / "res.csv").write_text(f"solution_id,cases,passed,git_sha,cases_sha\ns,1,1,abc,{digest}\n")
    report = consumer.check_consumer(tmp_path / "r.csv", tmp_path, options, solutions=tmp_path / "s.csv", results=tmp_path / "res.csv")
    assert report.problems == []
    (tmp_path / "cases.json").write_text("[1]")
    report = consumer.check_consumer(tmp_path / "r.csv", tmp_path, options, solutions=tmp_path / "s.csv", results=tmp_path / "res.csv")
    assert any(p.startswith("C10") and "stale" in p for p in report.problems)


def test_the_library_solutions_come_from_the_default_folder_else_a_previous_one(tmp_path):
    assert consumer.library_solutions_csv(tmp_path) == tmp_path / "esoi" / "solutions.csv"
    (tmp_path / "docs" / "structure").mkdir(parents=True)
    (tmp_path / "docs" / "structure" / "solutions.csv").write_text("solution_id\n")
    assert consumer.library_solutions_csv(tmp_path) == tmp_path / "docs" / "structure" / "solutions.csv"
    (tmp_path / "esoi").mkdir()
    (tmp_path / "esoi" / "solutions.csv").write_text("solution_id\n")
    assert consumer.library_solutions_csv(tmp_path) == tmp_path / "esoi" / "solutions.csv"


def test_selection_may_name_a_snapshot_beside_the_library(tmp_path, monkeypatch):
    options = library(tmp_path)
    monkeypatch.setattr(consumer, "library_dir", lambda opts: tmp_path / "lib" / "libx")
    (tmp_path / "lib" / "libx" / "esoi_selection.json").write_text('{"call-a-model": {"default": "plain", "modules": {}}}')
    options.selection = "libx/esoi_selection.json"
    assert consumer.known_solution_ids(options) == ({"call-a-model"}, False)
    options.selection = "esoi_selection.json"
    assert consumer.known_solution_ids(options) == ({"call-a-model"}, False)
