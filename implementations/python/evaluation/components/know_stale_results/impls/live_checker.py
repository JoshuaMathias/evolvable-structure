"""CURRENT: the live checker, ``esoi.structure.structure_check.check.check`` (rules S10, S16, S20), run over a synthetic fixture repository, in
strict mode when the case says so. Zero model calls."""
from shared_fixtures.interface import repo_fixture

from esoi.structure.structure_check.interface import check_all  # noqa: F401  (the live code this arm measures, through the fixture)


def build(meter):
    def run(kind, args):
        return repo_fixture.report(repo_fixture.fresh_repo(args.get("edits", [])), args.get("strict", False))
    return run
