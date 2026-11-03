"""CURRENT: the live at-a-glance layout of ``esoi.readme``, with the full record below a divider. Zero model calls."""
import glance_fixture
from esoi import readme


def build(meter):
    def page(kind, args):
        cfg, loaded, view = glance_fixture.load(args["repo"], bool(args.get("fresh")))
        return {"text": readme.render(loaded, glance_fixture.intent_of(view, args["intent"]), view, "glance")}
    return page
