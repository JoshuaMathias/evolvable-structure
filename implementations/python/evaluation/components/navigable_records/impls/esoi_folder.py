"""ALTERNATIVE: the records of the top intent all in the structure folder (``esoi records gather``), the layout before records beside the code. Zero model calls."""
from shared_fixtures.interface import navigable_fixture
from esoi.structure.intent_registry import besidecode


def build(meter):
    def layout(kind, args):
        root, digest = navigable_fixture.layout(args["repo"], "esoi_folder", bool(args.get("fresh")))
        return {"root": str(root), "digest": digest, "arm": "esoi_folder"}
    return layout
