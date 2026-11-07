"""CURRENT: the live at-a-glance layout of ``esoi.understanding.readable_records.readme``, with the full record below a divider. Zero model calls."""
from shared_fixtures.interface import glance_fixture
from esoi.understanding.readable_records.interface import readme


def build(meter):
    def page(kind, args):
        cfg, loaded, view = glance_fixture.load(args["repo"], bool(args.get("fresh")))
        return {"text": readme.render(loaded, glance_fixture.intent_of(view, args["intent"]), view, "glance")}
    return page
