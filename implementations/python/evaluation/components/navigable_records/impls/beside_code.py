"""CURRENT: each record in the folder that holds its code, with the READMEs the library generates (``esoi records place``). Zero model calls."""
import navigable_fixture
from esoi import besidecode  # noqa: F401  (the layout is made by the library's own placement)


def build(meter):
    def layout(kind, args):
        root, digest = navigable_fixture.layout(args["repo"], "beside_code", bool(args.get("fresh")))
        return {"root": str(root), "digest": digest, "arm": "beside_code"}
    return layout
