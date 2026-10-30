"""CURRENT: the library's own metric record: ``esoi.spec_slice``, ``esoi.metric_meter``, ``esoi.metric_results`` and
``esoi.iteration``, over a throwaway repository (see ``metric_record_fixture``). Zero model calls."""
import time

import metric_record_fixture as fixture
from esoi.iteration import MetricIteration
from esoi.metric_meter import BEFORE, OfflineArmMeter, RecordedRowMeter, read_value
from esoi.metric_results import FileMetricLedger, MetricResult, reconcile, render_line
from esoi.spec_slice import Chosen, RepoSliceSource, SpecSlice, lexical_choice, next_milestone, target_of


def chooser(name):
    def two_solutions(request, index):
        return Chosen(("greet-a-person", "project-purpose"))

    def raises(request, index):
        raise RuntimeError("boom")

    return {"two_solutions": two_solutions, "sure_first": lambda request, index: Chosen(("greet-a-person", "project-purpose"), sure=True),
            "raises": raises}.get(name, lexical_choice)


class Live:
    def milestone(self, world, args):
        step = next_milestone(args["cell"])
        value, token = target_of(step.text if step else "")
        return {"number": step.number if step else 0, "text": step.text if step else "", "target": value}

    def slice(self, world, args):
        source = RepoSliceSource(choose=chooser(args.get("chooser", "")), timeout_seconds=args.get("timeout", 3.0))
        found = source.slice_for(args["request"], world.folder)
        return {"solution_id": found.solution_id if found else "", "metric_id": found.metric_id if found else "",
                "milestone_number": found.milestone_number if found else 0}

    def reading(self, world, args):
        told = []
        done = read_value(fixture.fake_meters(args["meters"]), fixture.SLICE, when=args.get("when", BEFORE),
                          budget_seconds=args.get("budget", 5), announce=lambda: told.append(1))
        return {"value": done.value, "meter": done.meter, "note": done.note, "announced": len(told)}

    def arm(self, world, args):
        found = SpecSlice(root=str(world.root), solution_id=fixture.SLICE.solution_id, metric_id=fixture.SLICE.metric_id,
                          metric_command=fixture.SLICE.metric_command)
        environ = args.get("environ", fixture.default_environ())
        meter = RecordedRowMeter() if args["meter"] == "recorded_row" else OfflineArmMeter(environ, args.get("timeout"))
        started = time.monotonic()
        value = meter.measure(found)
        seen = world.spawned[0] if world.spawned else {"argv": [], "env": {}}
        return {"value": value, "spawned": len(world.spawned), "argv": seen["argv"][-4:],
                "leaked": sorted(k for k in seen["env"] if "KEY" in k or "TOKEN" in k), "seconds": round(time.monotonic() - started, 1)}

    def result(self, world, args):
        try:
            after = float("nan") if args.get("nan") else args.get("after")
            MetricResult(source=args["source"], run_id="r", metric_id="m", before=args.get("before"), after=after,
                         reason=args.get("reason", ""))
        except ValueError as error:
            return {"error": type(error).__name__}
        return {"error": ""}

    def reconcile(self, world, args):
        rows = [MetricResult(run_id="r", metric_id=row.get("metric_id", "m"), **{k: v for k, v in row.items() if k != "metric_id"})
                for row in args["rows"]]
        out = reconcile(rows, args["limit"]) if "limit" in args else reconcile(rows)
        return {"sources": [r.source for r in out], "disagrees": [r.disagrees for r in out],
                "values": [[r.before, r.after] for r in out], "line": render_line([r.to_dict() for r in out])}

    def iteration(self, world, args):
        ledger = FileMetricLedger(world.ledger_dir)
        meters = fixture.fake_meters(args.get("meters", []))
        source = RepoSliceSource() if args.get("source", True) else None
        run = MetricIteration(ledger, "r", source=source, meters=meters, measures=args.get("measures", True),
                              request=args["request"], working_dir=world.folder)
        block = run.begin()
        for row in args.get("worker", []):
            ledger.record(MetricResult(run_id="r", **row))
        done = run.finish(args.get("did_work", True))
        return {"rows": [[r.source, r.before, r.after] for r in done.results], "block": "NEXT PRIORITY" in block,
                "reads": [m.reads for m in meters]}


def build(meter):
    strategy = Live()
    return lambda kind, args: fixture.run_case(kind, args, strategy)
