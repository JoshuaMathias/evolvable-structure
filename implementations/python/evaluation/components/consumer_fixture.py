"""A synthetic library and a synthetic consumer of it, for the consumer-check cases. The library (``fixlib``) has one
port with one required method and one function; the consumer has one conforming sink, a registry, a solutions table,
a results table and one case file. Nothing real."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import repo_fixture
from esoi import consumer
from esoi.consumer import Options

LIBRARY_FILES = {
    "fixlib/__init__.py": '"""A fixture library."""\n',
    "fixlib/ports.py": ('"""The fixture port."""\nfrom typing import Protocol\n\n\nclass Sink(Protocol):\n'
                        '    """Takes an escalation."""\n\n    def escalate(self, item): ...\n'),
    "fixlib/api.py": '"""The fixture API."""\n\n\ndef run():\n    """Runs."""\n',
    "library_solutions.csv": "solution_id\nnotify-a-person\n",
}
SINK = '"""A fixture consumer sink."""\n\n\nclass Sink:\n    """Takes an escalation."""\n\n    def escalate(self, item):\n        return None\n'
REGISTRY = ("integration_id,module,symbol,lib_solution_id,lib_port,lib_symbol,kind,selected_by,metric,tests,status,gap,action,"
            "solution_id\nsink,consumer_sink,Sink,notify-a-person,Sink,,implementation,hand-wired,a live proof,"
            "tests/test_sink.py,done,,,escalate\n")
SOLUTIONS = ("solution_id,selected,metric_files,gap,metric_kind,invariant_reason,component,component_impl\n"
             "escalate,consumer_sink:Sink,case_files/cases.json,,,,,\n")
LIBRARY_DIR = Path(tempfile.mkdtemp(prefix="esoi_fixlib_"))
for rel, text in LIBRARY_FILES.items():
    repo_fixture.write(LIBRARY_DIR, rel, text)
sys.path.insert(0, str(LIBRARY_DIR))
OPTIONS = Options(library="fixlib", column_prefix="lib", port_modules=["fixlib.ports"], pin_name="fixlib",
                  solutions_csv=str(LIBRARY_DIR / "library_solutions.csv"))
TEMPLATE: list = []


def baseline_consumer(dest: Path) -> Path:
    root = Path(dest)
    repo_fixture.write(root, "consumer_sink.py", SINK)
    repo_fixture.write(root, "tests/test_sink.py", '"""Pins the sink."""\n')
    repo_fixture.write(root, "case_files/cases.json", "[]\n")
    repo_fixture.write(root, "registry.csv", REGISTRY)
    repo_fixture.write(root, "solutions.csv", SOLUTIONS)
    digest = consumer.cases_hash(["case_files/cases.json"], root)
    repo_fixture.write(root, "results.csv", "solution_id,cases,passed,git_sha,cases_sha\n"
                       f"escalate,1,1,abc1234,{digest}\n")
    return root


def fresh_consumer(edits: list) -> Path:
    if not TEMPLATE:
        base = Path(tempfile.mkdtemp(prefix="esoi_consumer_")) / "r"
        TEMPLATE.append(baseline_consumer(base))
    root = Path(tempfile.mkdtemp(prefix="esoi_consumer_case_")) / "r"
    shutil.copytree(TEMPLATE[0], root)
    repo_fixture.apply_edits(root, edits)
    return root


def run_check(edits: list) -> dict:
    root = fresh_consumer(edits)
    for name in [m for m in sys.modules if m == "consumer_sink"]:
        del sys.modules[name]
    try:
        report = consumer.check_consumer(root / "registry.csv", root, OPTIONS, solutions=root / "solutions.csv",
                                         results=root / "results.csv")
        problems = report.problems
    except Exception as exc:
        problems = [f"CRASH {type(exc).__name__}: {exc}"]
    return {"exit": 1 if problems else 0, "problems": problems}
