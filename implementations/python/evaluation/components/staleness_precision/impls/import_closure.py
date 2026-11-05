"""The live staleness check under the rule `import_closure`: only the files the arm's module imports, found from the source, count. Zero model calls."""
import staleness_fixture
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import staleness  # noqa: F401  (the live code under test)


def build(meter):
    def run(kind, args):
        return staleness_fixture.decide("import_closure", args["step"], args["component"])
    return run
