"""CURRENT: the live consumer check, ``esoi.consumer.check_consumer``, over a synthetic library and consumer.
Zero model calls."""
import consumer_fixture
from esoi import consumer  # noqa: F401  (the live code under test)


def build(meter):
    def check(kind, args):
        return consumer_fixture.run_check(args.get("edits", []))
    return check
