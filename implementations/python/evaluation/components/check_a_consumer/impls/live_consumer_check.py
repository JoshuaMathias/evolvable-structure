"""CURRENT: the live consumer check, ``esoi.runtime.consumer_check.consumer.check_consumer``, over a synthetic library and consumer.
Zero model calls."""
from shared_fixtures.interface import consumer_fixture
from esoi.runtime.consumer_check.interface import consumer


def build(meter):
    def check(kind, args):
        return consumer_fixture.run_check(args.get("edits", []))
    return check
