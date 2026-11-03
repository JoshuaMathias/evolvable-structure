"""The records of the top intent all in the structure folder (``esoi records gather``): the layout before records beside the code. Zero model calls."""
import navigable_fixture
from esoi import besidecode  # noqa: F401  (the layout is made by the library's own placement)


def build(meter):
    def layout(kind, args):
        root, digest = navigable_fixture.layout(args["repo"], "esoi_folder", bool(args.get("fresh")))
        return {"root": str(root), "digest": digest, "arm": "esoi_folder"}
    return layout
