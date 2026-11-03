"""BASELINE: no page. A person who clicks into the folder sees only the files. Zero model calls."""


def build(meter):
    def page(kind, args):
        return {"text": ""}
    return page
