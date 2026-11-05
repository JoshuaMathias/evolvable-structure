"""``esoi.understanding.spec_search.spec_search.lexical_only``, the lexical top three. Zero model calls."""
from esoi.understanding.spec_search import spec_search
from . import live


def build(meter):
    return live.runner(spec_search.lexical_only)
