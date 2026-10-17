"""BASELINE: a checker that only does file coverage (every file belongs to exactly one component, every glob
matches a file). The naive alternative the full check is measured against. Zero model calls."""
import repo_fixture
from esoi.tables import glob_re, ids, read_csv, repo_files


def coverage(root):
    files = repo_files(root)
    owners = {f: [] for f in files}
    problems = []
    for r in read_csv(root / "docs/structure/components.csv"):
        for pattern in ids(r["path"]):
            hit = [f for f in files if glob_re(pattern).match(f)]
            if not hit:
                problems.append(f"S1 {r['component_id']}: path pattern {pattern!r} matches no file")
            for f in hit:
                owners[f].append(r["component_id"])
    problems += [f"S1 {f}: belongs to no component" for f, o in owners.items() if not o]
    problems += [f"S1 {f}: belongs to several components" for f, o in owners.items() if len(set(o)) > 1]
    return problems


def build(meter):
    def run(kind, args):
        problems = coverage(repo_fixture.fresh_repo(args.get("edits", [])))
        return {"exit": 1 if problems else 0, "problems": problems}
    return run
