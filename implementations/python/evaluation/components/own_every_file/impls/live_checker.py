"""CURRENT: the live checker, ``esoi.structure.structure_check.check.check``, run over a synthetic fixture repository (the same fixture as
check_the_structure); the cases here are the subset that concerns this solution. Zero model calls."""
import repo_fixture
from esoi.structure.structure_check import check


def build(meter):
    def run(kind, args):
        return repo_fixture.report(repo_fixture.fresh_repo(args.get("edits", [])), args.get("strict", False))
    return run
