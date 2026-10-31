"""CURRENT: ``esoi.spec_search.gated`` with no vector search and no judge. Zero model calls."""
from esoi import spec_search
from . import live


def build(meter):
    return live.runner(spec_search.gated)
