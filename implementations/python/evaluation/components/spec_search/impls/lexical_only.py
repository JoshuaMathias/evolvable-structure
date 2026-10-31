"""BASELINE: ``esoi.spec_search.lexical_only``, the lexical top three. Zero model calls."""
from esoi import spec_search
from . import live


def build(meter):
    return live.runner(spec_search.lexical_only)
