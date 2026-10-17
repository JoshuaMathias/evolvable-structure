"""CURRENT: the live checker, ``esoi.check.check``, run over a synthetic fixture repository. Nothing is
reimplemented, only the repository under inspection is fake. A ``scale`` case generates a repository of hundreds of modules
and reports how long the check takes cold and with a warm cache. Zero model calls."""
import time

import repo_fixture
from esoi import check, config


def build(meter):
    def run(kind, args):
        if kind == "scale":
            root = repo_fixture.fresh_repo([])
            for i in range(args["modules"]):
                repo_fixture.write(root, f"demo/gen_{i}.py", f'"""Generated module {i}."""\nfrom demo import greet\nfrom demo.adapters import plain\n\n\ndef f():\n    return greet.greet("x")\n')
            cfg = config.load(root)
            cfg.layers = ["adapters", "core"]
            timings = []
            for _ in range(2):
                started = time.perf_counter()
                problems = check.check(cfg)
                timings.append(time.perf_counter() - started)
            return {"exit": 1 if problems else 0, "problems": problems, "cold_seconds": round(timings[0], 2),
                    "warm_seconds": round(timings[1], 2)}
        return repo_fixture.report(repo_fixture.fresh_repo(args.get("edits", [])), args.get("strict", False))
    return run
