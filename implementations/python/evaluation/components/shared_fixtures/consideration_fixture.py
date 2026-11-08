"""A small synthetic repository for Solution Consideration and Solution Relevance (no real data, public-repo safe).

Its shape is the case that motivated generated prompts: an outside tool with a strong reputation was admitted as an arm of a card
builder and measured, and it lost (3 of 63 against 43 of 63). The loss is held only in the results log and a finding, never in the
solution's own row, so a pass that reads the solution alone cannot see it.

``write_repo(dest)`` writes the repository and returns its root: a top intent with one solution (Recall), a sub-intent that implements
it with two children (Card Builder, which delegates to Card Store), a results log, and a findings file declared in
``[[consider.records]]``.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List

TOML = '''package = "toy"
structure_dir = "esoi"
results = "esoi/results.csv"

[consider]
budget = 6000

[[consider.records]]
file = "registry/findings.csv"
kind = "finding"
'''

INTENT = ["intent_id", "name", "vision_statement", "implements", "opportunities", "solution_coherence", "solution_diagram"]
SOLUTION = ["solution_id", "name", "description", "purpose", "approach", "out_of_scope", "milestones", "knowledge", "inputs", "outputs",
            "problem_ids", "ideal_ids", "metric_ids", "implementations", "selected", "delegates_to"]
IMPLEMENTATION = ["implementation_id", "solution_id", "filepath", "name", "description", "advantages", "disadvantages", "uses_solution_ids"]
METRIC = ["metric_id", "name", "purpose", "record", "cascading_conditionals", "solution_ids", "command"]
PROBLEM = ["problem_id", "name", "problem", "why_it_matters", "solution_ids", "ideal_ids"]
IDEAL = ["ideal_id", "name", "principle", "hints_of_measurement", "problem_ids"]
RESULT = ["date", "component", "impl", "cases", "passed", "dev", "heldout", "model_calls", "tokens_in", "tokens_out", "cost_usd",
          "seconds", "git_sha", "cases_sha", "model", "details", "sample", "balanced"]
FINDING = ["finding_id", "solution_id", "candidate", "rating", "summary"]
KNOWLEDGE = ["knowledge_id", "claim", "kind", "source", "solution_ids", "status", "status_by", "recorded", "expiration"]
# Knowledge of Card Builder: each case of the knowledge kind needs one item, and the others (a contradicted theory, an expired
# guess, a vendor claim) would mislead a pass that was handed all of them.
KNOWLEDGE_ROWS = [
    {"knowledge_id": "k-cb-1", "claim": "Graph groups lost to import cards on the file-finding cases.", "kind": "evidence",
     "source": "result:card_builder/graph_groups@2026-01-02", "solution_ids": "card-builder", "status": "active", "recorded": "2026-01-02"},
    {"knowledge_id": "k-cb-2", "claim": "Cards must carry the words people search for, not only file names.", "kind": "perspective",
     "source": 'person:the maintainer, 2026-01-03: "a card nobody can find by its words is no card"', "solution_ids": "card-builder",
     "status": "active", "recorded": "2026-01-03"},
    {"knowledge_id": "k-cb-3", "claim": "Import graphs exist only for code; a folder of prose needs another builder.", "kind": "assumption",
     "source": "a best guess by the maintainer", "solution_ids": "card-builder", "status": "active", "recorded": "2026-01-01"},
    {"knowledge_id": "k-cb-4", "claim": "A card per file is an index of files, not a set of cards.", "kind": "lesson", "source": "mistake:M-1",
     "solution_ids": "card-builder", "status": "active", "recorded": "2026-01-01"},
    {"knowledge_id": "k-cb-5", "claim": "Graph tools group files better than import graphs do.", "kind": "theory",
     "source": "url:https://example.org/graph-tools grade D", "solution_ids": "card-builder", "status": "contradicted", "status_by": "k-cb-1",
     "recorded": "2025-12-01"},
    {"knowledge_id": "k-cb-6", "claim": "A vendor study reports that topic cards halve reading time.", "kind": "evidence",
     "source": "url:https://example.org/vendor-study grade D", "solution_ids": "card-builder", "status": "active", "recorded": "2025-11-01"},
    {"knowledge_id": "k-cb-7", "claim": "The store will stay under one hundred cards.", "kind": "best guess", "source": "an estimate at design time",
     "solution_ids": "card-builder;card-store", "status": "active", "recorded": "2025-01-01", "expiration": "2025-06-30"},
]


def table(columns: List[str], rows: List[Dict[str, str]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


FILES = {
    "esoi/intent.csv": table(INTENT, [{"intent_id": "toy", "name": "Toy Notes", "vision_statement": "Notes are found when needed.",
                                       "solution_coherence": "Recall finds the notes a request needs."}]),
    "esoi/solutions.csv": table(SOLUTION, [{
        "solution_id": "recall", "name": "Recall", "purpose": "Give a request the notes it needs.", "approach": "Build cards, keep them, pick some.",
        "implementations": "composition", "selected": "composition", "metric_ids": ""}]),
    "esoi/implementations.csv": table(IMPLEMENTATION, [{"implementation_id": "recall:composition", "solution_id": "recall",
                                                        "name": "Composition", "description": "The recall parts in order."}]),
    "esoi/recall_parts/intent.csv": table(INTENT, [{
        "intent_id": "recall_parts", "name": "Recall Parts", "vision_statement": "Every note has a card.", "implements": "recall:composition",
        "solution_coherence": "Card Builder groups files into cards and hands them to Card Store, which keeps them for recall.",
        "solution_diagram": "Card Builder -> Card Store (cards)"}]),
    "esoi/recall_parts/solutions.csv": table(SOLUTION, [
        {"solution_id": "card-builder", "name": "Card Builder", "purpose": "Propose the cards a folder of files needs.",
         "approach": "Group files that belong together and describe each group.",
         "inputs": "A folder.", "outputs": "Cards.", "problem_ids": "prob-no-cards", "ideal_ids": "ideal-cards", "metric_ids": "metric-card-builder",
         "implementations": "import_cards;graph_groups", "selected": "import_cards", "delegates_to": "card-store"},
        {"solution_id": "card-store", "name": "Card Store", "purpose": "Keep cards and find them again.", "approach": "Store cards by id.",
         "inputs": "A card.", "outputs": "The card's id.", "implementations": "local_store", "selected": "local_store"}]),
    "esoi/recall_parts/implementations.csv": table(IMPLEMENTATION, [
        {"implementation_id": "card-builder:import_cards", "solution_id": "card-builder", "name": "Import cards",
         "description": "Files that import each other are one card."},
        {"implementation_id": "card-builder:graph_groups", "solution_id": "card-builder", "name": "Graph groups",
         "description": "An outside graph tool's communities of files, one card each."},
        {"implementation_id": "card-store:local_store", "solution_id": "card-store", "name": "Local store", "description": "A file per card."}]),
    "esoi/recall_parts/metrics.csv": table(METRIC, [{
        "metric_id": "metric-card-builder", "name": "Cards that hold the needed file", "purpose": "Whether the cards serve a task.",
        "record": "Cases passed of 63.", "solution_ids": "card-builder",
        "command": "esoi run card_builder --impl import_cards; esoi run card_builder --impl graph_groups"}]),
    "esoi/recall_parts/problems.csv": table(PROBLEM, [{"problem_id": "prob-no-cards", "name": "No cards", "problem": "Files have no cards.",
                                                       "why_it_matters": "Recall returns nothing.", "solution_ids": "card-builder", "ideal_ids": "ideal-cards"}]),
    "esoi/recall_parts/ideals.csv": table(IDEAL, [{"ideal_id": "ideal-cards", "name": "Current cards", "principle": "Cards cover the files.",
                                                   "hints_of_measurement": "The needed file is in the first cards.", "problem_ids": "prob-no-cards"}]),
    "esoi/results.csv": table(RESULT, [
        {"date": "2026-01-02", "component": "card_builder", "impl": "graph_groups", "cases": "63", "passed": "3", "model_calls": "0",
         "cost_usd": "0.0", "seconds": "50", "git_sha": "aaaaaaa", "cases_sha": "c1", "model": "none", "details": "top1=0/63", "balanced": "0.32"},
        {"date": "2026-01-02", "component": "card_builder", "impl": "import_cards", "cases": "63", "passed": "43", "model_calls": "0",
         "cost_usd": "0.0", "seconds": "40", "git_sha": "aaaaaaa", "cases_sha": "c1", "model": "none", "details": "top1=20/63", "balanced": "0.78"}]),
    "esoi/recall_parts/knowledge.csv": table(KNOWLEDGE, KNOWLEDGE_ROWS),
    "registry/findings.csv": table(FINDING, [
        {"finding_id": "F-1", "solution_id": "card-builder", "candidate": "Graph groups", "rating": "0.85",
         "summary": "A popular graph tool; strongest candidate by reputation."},
        {"finding_id": "F-2", "solution_id": "card-builder", "candidate": "Graph groups", "rating": "0.2",
         "summary": "Lost on our cases: 3 of 63 against 43 of 63 (esoi/results.csv)."}]),
}


def write_repo(dest: Path) -> Path:
    """Write the repository under ``dest`` and return its root."""
    root = Path(dest)
    (root / "esoi.toml").parent.mkdir(parents=True, exist_ok=True)
    (root / "esoi.toml").write_text(TOML, encoding="utf-8")
    for name, text in FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root
