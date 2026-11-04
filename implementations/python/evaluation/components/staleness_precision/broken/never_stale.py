"""BASELINE: a freshness check that never calls a result stale, so it never re-runs anything and keeps every result whose code
changed (every false-fresh). Zero model calls."""


def build(meter):
    return lambda kind, args: {"stale": False, "why": ""}
