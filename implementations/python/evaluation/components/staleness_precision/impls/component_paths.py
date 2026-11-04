"""The live staleness check under the rule `component_paths`: only the files the arm's solution and implementation own count. Zero model calls."""
import staleness_fixture
from esoi import staleness  # noqa: F401  (the live code under test)


def build(meter):
    def run(kind, args):
        return staleness_fixture.decide("component_paths", args["step"], args["component"])
    return run
