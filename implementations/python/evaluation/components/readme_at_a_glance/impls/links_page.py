"""A compact layout of mostly links: name, vision statement and links to everything else. Zero model calls."""
import glance_fixture


def build(meter):
    def page(kind, args):
        return glance_fixture.page(args["repo"], args["intent"], "links", bool(args.get("fresh")))
    return page
