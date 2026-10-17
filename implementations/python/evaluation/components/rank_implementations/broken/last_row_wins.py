"""BASELINE: the naive ranking. The last row recorded is the winner, no case file hash is compared, nothing is
flagged as unverified, and every selected implementation is called a win. Zero model calls."""


def build(meter):
    def run(kind, args):
        if kind == "rank":
            order = [r["impl"] for r in reversed(args["rows"])]
            return {"ranked": order, "beats": [order[0]] if order[0] != args["selected"] else [], "unverified": []}
        if kind == "verdict":
            return {"verdict": "WIN", "text": "", "arms": {}}
        last = args["rows"][-1]["impl"]
        return {"exit": 0, "text": f"{last} wins", "beats": [last] if last != args["selected"] else [], "incomparable": []}
    return run
