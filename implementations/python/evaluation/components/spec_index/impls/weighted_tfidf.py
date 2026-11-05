"""CURRENT: field-weighted TF-IDF over the index, ``esoi.understanding.spec_search.spec_index.weighted_tfidf``. Zero model calls."""
from esoi.understanding.spec_search import spec_index
from . import live


def build(meter):
    return live.runner(spec_index.weighted_tfidf)
