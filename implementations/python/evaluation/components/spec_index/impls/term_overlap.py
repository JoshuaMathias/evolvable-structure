"""Plain term overlap, ``esoi.understanding.spec_search.spec_index.term_overlap``. Zero model calls."""
from esoi.understanding.spec_search import spec_index
from . import live


def build(meter):
    return live.runner(spec_index.term_overlap)
