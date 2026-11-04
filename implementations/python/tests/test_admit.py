"""Admission of a technology that does not fit (goal: the structure accommodates a newly found technology, or says exactly which
justified change it needs). Three worked examples run through `esoi admit`, `esoi records sync`, `esoi select`, `esoi lock` and
`esoi leaderboard` over the scaffolded repository; docs/how-to/admit-a-technology-that-does-not-fit.md describes them."""
import json
import os
import sys

import pytest

from conftest import forget_demo_package
from esoi import cli, tables

BASE = '''"""The memory seats of the example: a model call, a search and a card store, each with one arm."""
import typing

from esoi import implementation, solution


@solution("model-call", kind="event", entry="complete", example="hello")
class ModelCall(typing.Protocol):
    """Answer a prompt with text."""

    def complete(self, prompt: str) -> str: ...


@solution("card-store", kind="event", entry="keep", example="a note")
class CardStore(typing.Protocol):
    """Keep a note and give back its id."""

    def keep(self, note: str) -> str: ...


@solution("search", kind="event", entry="find", example="note")
class Search(typing.Protocol):
    """The notes that match a query, best first."""

    def find(self, query: str) -> typing.List[str]: ...


@implementation("model-call", "hosted-api")
class HostedApi:
    def complete(self, prompt):
        return "hosted: " + prompt


@implementation("card-store", "file-cards")
class FileCards:
    def keep(self, note):
        return "card-1"


@implementation("search", "bm25")
class Bm25:
    def find(self, query):
        return [query]
'''
INIT = '''"""demo: the example package."""
from pathlib import Path

from esoi.assemble import Assembler
from esoi.entry import runner

here = Path(__file__).resolve().parent
ASSEMBLER = Assembler("demo", here, modules=("demo.greet", "demo.memory"), records=here.parent)
run = runner(ASSEMBLER)
'''


def run(repo, *argv):
    cwd = os.getcwd()
    os.chdir(repo)
    sys.path.insert(0, str(repo))      # the package under test is importable the way `esoi lock --package demo` finds it
    try:
        return cli.main(list(argv))
    finally:
        sys.path.remove(str(repo))
        os.chdir(cwd)


def rows(repo, name):
    return tables.read_csv(repo / "esoi" / name)


def structural(repo, capsys):
    """The lines `esoi check` reports that are neither the text only a person writes (R2 and R3 on a new record) nor a generated page
    that `esoi check --write-docs` rewrites (S8 READMEs and diagrams, S17 tracker, S39 diagram)."""
    capsys.readouterr()
    run(repo, "check")
    lines = [line for line in capsys.readouterr().out.splitlines() if line[:1] == "S"]
    return [line for line in lines if not (line.startswith("S26 R2") or line.startswith("S26 R3")
                    or line.split()[0] in ("S8", "S17", "S39"))]


@pytest.fixture()
def base(repo, capsys):
    (repo / "demo" / "memory.py").write_text(BASE)
    (repo / "demo" / "__init__.py").write_text(INIT)
    assert run(repo, "records", "sync") == 0
    forget_demo_package(repo)
    capsys.readouterr()
    return repo


def selected(repo, solution_id):
    return next(r["selected"] for r in rows(repo, "solutions.csv") if r["solution_id"] == solution_id)


def lock_of(repo):
    forget_demo_package(repo)
    path = repo / "esoi.lock.json"
    assert run(repo, "lock", "--package", "demo", "--file", str(path)) == 0
    return json.loads(path.read_text())


def test_a_local_model_server_is_one_more_arm_of_the_solution_it_serves(base, capsys):
    """Example 1: same interface, same seat: no change to the specification."""
    before = [r for r in rows(base, "solutions.csv") if r["solution_id"] == "model-call"]
    with open(base / "demo" / "memory.py", "a") as handle:
        handle.write('''

@implementation("model-call", "local-server")
class LocalServer:
    def complete(self, prompt):
        return "local: " + prompt
''')
    assert run(base, "records", "sync") == 0
    forget_demo_package(base)
    ids = {r["implementation_id"]: r for r in rows(base, "implementations.csv")}
    assert ids["model-call:local-server"]["filepath"] == "demo/memory.py"
    after = [r for r in rows(base, "solutions.csv") if r["solution_id"] == "model-call"]
    assert {k: v for k, v in after[0].items() if k != "implementations"} == {k: v for k, v in before[0].items() if k != "implementations"}
    assert "local-server" in after[0]["implementations"]
    assert structural(base, capsys) == []
    capsys.readouterr()
    assert run(base, "select", "model-call") == 0
    assert "model-call: hosted-api" in capsys.readouterr().out          # admitting an arm never switches the default
    assert "model-call" in json.dumps(lock_of(base))


def test_a_reranker_is_a_new_solution_and_a_stage_of_a_composite_arm(base, capsys):
    """Example 2: a stage, not a replacement. A new solution `rerank` (recorded), and an arm of `search` that uses it."""
    assert run(base, "admit", "search", "BM25 then rerank", "--uses", "rerank", "--why", "orders the top hits by relevance") == 2
    assert "do not exist" in capsys.readouterr().err
    with open(base / "demo" / "memory.py", "a") as handle:
        handle.write('''

@solution("rerank", kind="event", entry="order", example="note")
class Rerank(typing.Protocol):
    """Put matches in order of relevance."""

    def order(self, hits: typing.List[str]) -> typing.List[str]: ...


@implementation("rerank", "cross-encoder")
class CrossEncoder:
    def order(self, hits):
        return sorted(hits)
''')
    assert run(base, "records", "sync") == 0
    assert run(base, "admit", "search", "BM25 then rerank", "--uses", "rerank", "--why", "orders the top hits by relevance") == 0
    assert run(base, "admit", "search", "--changed", "add the solution rerank that search arms may build on",
               "--why", "ordering the hits has its own definition of best, precision at the top") == 0
    assert "no arm yet" in capsys.readouterr().out
    row = next(r for r in rows(base, "implementations.csv") if r["implementation_id"] == "search:bm25-then-rerank")
    assert row["uses_solution_ids"] == "rerank" and row["filepath"] == ""
    note = next(r for r in rows(base, "solutions.csv") if r["solution_id"] == "search")["knowledge"]
    assert "add the solution rerank that search arms may build on. Because ordering the hits has its own definition of best" in note
    run(base, "leaderboard")
    assert "NOT MEASURED  search: BM25 then rerank" in capsys.readouterr().out      # the gap is visible
    with open(base / "demo" / "memory.py", "a") as handle:
        handle.write('''

@implementation("search", "bm25-then-rerank")
class Bm25ThenRerank:
    def __init__(self, rerank: Rerank):
        self.rerank = rerank

    def find(self, query):
        return self.rerank.order([query])
''')
    assert run(base, "records", "sync") == 0
    forget_demo_package(base)
    row = next(r for r in rows(base, "implementations.csv") if r["implementation_id"] == "search:bm25-then-rerank")
    assert row["filepath"] == "demo/memory.py" and row["uses_solution_ids"] == "rerank"      # sync turned the candidate into an arm
    capsys.readouterr()
    run(base, "leaderboard")
    assert "NOT MEASURED  search" not in capsys.readouterr().out
    assert structural(base, capsys) == []
    capsys.readouterr()
    assert run(base, "select", "search") == 0 and "search: bm25" in capsys.readouterr().out
    lock_of(base)


def test_an_end_to_end_memory_product_is_measured_one_seat_up(base, capsys):
    """Example 3: it spans card-store and search, so no single seat fits. A parent solution `remember` is added and recorded; the
    assembled arm uses the two seats, the product is its rival with no arm yet, and nothing below changes."""
    with open(base / "demo" / "memory.py", "a") as handle:
        handle.write('''

@solution("remember", kind="event", entry="recall", example="note")
class Remember(typing.Protocol):
    """Keep what was said and bring back what matches."""

    def recall(self, query: str) -> typing.List[str]: ...


@implementation("remember", "assembled")
class Assembled:
    def __init__(self, store: CardStore, search: Search):
        self.store, self.search = store, search

    def recall(self, query):
        return self.search.find(query)
''')
    below = {sid: [r for r in rows(base, "solutions.csv") if r["solution_id"] == sid] for sid in ("card-store", "search")}
    assert run(base, "records", "sync") == 0
    assert run(base, "admit", "remember", "--changed", "add the solution remember above card-store and search",
               "--why", "a product that keeps and recalls is compared as a whole, which neither seat can score") == 0
    assert run(base, "admit", "remember", "Agent memory product", "--why", "keeps, summarizes and recalls in one hosted service") == 0
    capsys.readouterr()
    assert run(base, "admit", "remember", "Agent memory product", "--why", "again") == 2
    assert "already recorded" in capsys.readouterr().err
    assert {sid: [r for r in rows(base, "solutions.csv") if r["solution_id"] == sid] for sid in below} == below   # no change below
    assert run(base, "admit", "remember", "Product", "--why", "") == 2
    capsys.readouterr()
    assert run(base, "admit", "nothing", "X", "--why", "y") == 2          # fits no solution: the message names the justified change needed
    message = capsys.readouterr().err
    assert "needs a new one" in message and "--changed" in message
    run(base, "leaderboard")
    assert "NOT MEASURED  remember: Agent memory product" in capsys.readouterr().out
    forget_demo_package(base)
    assert structural(base, capsys) == []
    capsys.readouterr()
    assert run(base, "select", "remember") == 0 and "remember: assembled" in capsys.readouterr().out
    lock_of(base)
