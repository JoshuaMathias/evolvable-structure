"""CURRENT: the live checker, ``esoi.check.check`` (rules S10, S16, S20), run over a synthetic fixture repository, in
strict mode when the case says so. Zero model calls."""
import repo_fixture
from esoi import check  # noqa: F401  (the live code under test)


def build(meter):
    def run(kind, args):
        return repo_fixture.report(repo_fixture.fresh_repo(args.get("edits", [])), args.get("strict", False))
    return run
