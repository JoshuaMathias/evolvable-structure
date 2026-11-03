"""The at-a-glance layout: the summary a reader needs first, then the full record below a divider. Zero model calls."""
import glance_fixture


def build(meter):
    def page(kind, args):
        return glance_fixture.page(args["repo"], args["intent"], "glance", bool(args.get("fresh")))
    return page
