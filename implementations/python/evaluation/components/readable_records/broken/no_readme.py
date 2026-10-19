"""BASELINE: no generated page. The reader opens five files and reconciles their ids by hand, and nothing notices when a
hand-written page stops agreeing with them. Zero model calls."""


def build(meter):
    def readable(kind, args):
        return {"stale": 0, "text": ""}
    return readable
