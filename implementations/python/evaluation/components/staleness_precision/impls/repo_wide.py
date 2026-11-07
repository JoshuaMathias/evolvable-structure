"""The live staleness check under the rule `repo_wide`, the whole repository counts (what the check did before the other rules). Zero model calls."""
from shared_fixtures.interface import staleness_fixture
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import staleness  # noqa: F401  (the live code under test)


def build(meter):
    def run(kind, args):
        return staleness_fixture.decide("repo_wide", args["step"], args["component"])
    return run
