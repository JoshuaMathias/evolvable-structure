"""BASELINE: the naive promotion. It never switches anything, and reports no rival, so a person has to notice, and edit the
records, the metric command and the reason by hand. Zero model calls."""


def build(meter):
    def promote(kind, args):
        return {"count": 0, "status": "none"} if kind == "decide" else {"applied": False, "selected": args["selected"],
                                                                         "command": "", "evidence": False}
    return promote
