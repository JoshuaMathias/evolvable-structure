"""CURRENT: the live selector, ``esoi.select.Selector``, over a table of standard-library classes. Zero model calls."""
from esoi.select import Selector


def build(meter):
    def select(kind, args):
        selector = Selector(args["table"])
        try:
            for extra in args.get("register", []):
                selector.register(args["solution"], extra["name"], extra["target"], default=extra.get("default", False))
            name = selector.chosen_name(args["solution"], args.get("name"), args.get("overrides"))
            if args.get("config"):
                found = selector.resolve_config(args["solution"], args.get("name"), overrides=args.get("overrides"))
                return {"resolved": found.__name__ if found else None, "chosen": name, "names": selector.names(args["solution"])}
            found = selector.resolve(args["solution"], args.get("name"), overrides=args.get("overrides"))
            return {"resolved": found.__name__, "chosen": name, "names": selector.names(args["solution"])}
        except Exception as exc:
            return {"error": type(exc).__name__, "text": str(exc)}
    return select
