"""CURRENT: ``esoi.understanding.spec_search.spec_search.gated`` with no vector search and no judge. Zero model calls."""
from esoi.understanding.spec_search import spec_search
from . import live


def build(meter):
    return live.runner(spec_search.gated)
