"""BASELINE: plain term overlap, ``esoi.spec_index.term_overlap``. Zero model calls."""
from esoi import spec_index
from . import live


def build(meter):
    return live.runner(spec_index.term_overlap)
