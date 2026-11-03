"""ALTERNATIVE: a compact layout of mostly links (the rival `links` layout of ``esoi.readme``). Zero model calls."""
import glance_fixture
from esoi import readme


def build(meter):
    def page(kind, args):
        cfg, loaded, view = glance_fixture.load(args["repo"], bool(args.get("fresh")))
        return {"text": readme.render(loaded, glance_fixture.intent_of(view, args["intent"]), view, "links")}
    return page
