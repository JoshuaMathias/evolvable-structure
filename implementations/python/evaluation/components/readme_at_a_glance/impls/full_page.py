"""ALTERNATIVE: the record tables only, the page as it was before the at-a-glance standard (the rival `full` layout of ``esoi.understanding.readable_records.readme``). Zero model calls."""
import glance_fixture
from esoi.understanding.readable_records import readme


def build(meter):
    def page(kind, args):
        cfg, loaded, view = glance_fixture.load(args["repo"], bool(args.get("fresh")))
        return {"text": readme.render(loaded, glance_fixture.intent_of(view, args["intent"]), view, "full")}
    return page
