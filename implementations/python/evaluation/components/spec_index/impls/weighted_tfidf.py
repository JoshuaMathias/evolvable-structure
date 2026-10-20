"""CURRENT: field-weighted TF-IDF over the index, ``esoi.spec_index.weighted_tfidf``. Zero model calls."""
from esoi import spec_index
from . import live


def build(meter):
    return live.runner(spec_index.weighted_tfidf)
