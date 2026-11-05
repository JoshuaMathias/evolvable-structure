"""CURRENT: the live checker, ``esoi.structure.structure_check.check.check`` (rules S10, S16, S20), run over a synthetic fixture repository, in
strict mode when the case says so. Zero model calls."""
import repo_fixture
from esoi.structure.structure_check import check


def build(meter):
    def run(kind, args):
        return repo_fixture.report(repo_fixture.fresh_repo(args.get("edits", [])), args.get("strict", False))
    return run
