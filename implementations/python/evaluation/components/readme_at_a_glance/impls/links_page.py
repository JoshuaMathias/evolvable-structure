"""ALTERNATIVE: a compact layout of mostly links (the rival `links` layout of ``esoi.understanding.readable_records.readme``). Zero model calls."""
from shared_fixtures.interface import glance_fixture
from esoi.understanding.readable_records.interface import readme_render


def build(meter):
    def page(kind, args):
        cfg, loaded, view = glance_fixture.load(args["repo"], bool(args.get("fresh")))
        return {"text": readme_render(loaded, glance_fixture.intent_of(view, args["intent"]), view, "links")}
    return page
