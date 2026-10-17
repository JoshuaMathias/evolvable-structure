"""CURRENT: the live checker, ``esoi.check.check``, run over a synthetic fixture repository. Nothing is
reimplemented, only the repository under inspection is fake. Zero model calls."""
import repo_fixture
from esoi import check  # noqa: F401  (the live code under test)


def build(meter):
    def run(kind, args):
        return repo_fixture.report(repo_fixture.fresh_repo(args.get("edits", [])))
    return run
