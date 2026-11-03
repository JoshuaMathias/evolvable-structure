"""CURRENT: the record tables only, the page as it was before the at-a-glance standard. Zero model calls."""
import glance_fixture


def build(meter):
    def page(kind, args):
        return glance_fixture.page(args["repo"], args["intent"], "full", bool(args.get("fresh")))
    return page
