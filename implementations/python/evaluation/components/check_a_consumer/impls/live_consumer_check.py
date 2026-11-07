"""CURRENT: the live consumer check, ``esoi.runtime.consumer_check.consumer.check_consumer``, over a synthetic library and consumer.
Zero model calls."""
from shared_fixtures.interface import consumer_fixture

from esoi.runtime.consumer_check.interface import check_consumer  # noqa: F401  (the live code this arm measures, through the fixture)


def build(meter):
    def check(kind, args):
        return consumer_fixture.run_check(args.get("edits", []))
    return check
