"""BASELINE: a freshness check that accepts any result that has a row: it never notices other cases, uncommitted code or
code that changed since the result was recorded. Zero model calls."""
import repo_fixture
from esoi.tables import read_csv


def build(meter):
    def run(kind, args):
        root = repo_fixture.fresh_repo(args.get("edits", []))
        rows = read_csv(root / "evaluation/components/results.csv")
        problems = [] if rows else ["S10 greet-a-person: selected live has no row in the results log"]
        return {"exit": 1 if problems else 0, "problems": problems}
    return run
