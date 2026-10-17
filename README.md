# evolvable-structure

Evolvable Structure that Optimizes Intent (ESOI) is Joshua Mathias's way of turning an intention into a
structure that optimizes the fulfilling of that intent, while keeping the structure open to changes in the intent.
Intent is written down as five linked kinds of record (problems, ideals, solutions, implementations and metrics),
alternatives are compared by the metric the solution names as authoritative, and the best one is used automatically.
So people need only review metrics to steer, not implementations, though they can still review and improve
implementations and that still adds value.

This repository is mostly explanation and fill-in templates that need no code. Python is one example
implementation of the checking and measuring tools, and ESOI is applied to this repository too.

## Start here

1. **Read** [docs/explanation/](docs/explanation/): what ESOI is, the five intent types, the overall solution network
   and the detailed records, [when to split a solution](docs/explanation/when-to-split.md), choosing by metric, [when metrics are run](docs/explanation/when-metrics-are-run.md), and
   applying it beyond code.
2. **Fill in** [docs/templates/](docs/templates/): one template per intent type, an overall solution network,
   record headers, a repository standard, a review sheet layout and a metric run policy. They are generated from the author's own
   `SKILL.md`, so the questions are his words.
3. **Follow** [docs/guides/](docs/guides/): apply ESOI to a new project by hand first, then with tools.

## What is here

| Folder | What it holds |
|---|---|
| [`docs/`](docs/) | The main feature: explanation, guides and templates, all non-code |
| [`implementations/python/`](implementations/python/) | The `esoi` package and command: checks, measuring, a leaderboard, a review tracker. One example implementation |
| [`examples/`](examples/) | Repositories that adopted ESOI, as short testimonials |
| [`structure/`](structure/) | ESOI applied to this repository: its overall network and its detailed records |

## The Python implementation

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git#subdirectory=implementations/python"
esoi init            # scaffold a small example repository that already passes
esoi check           # run every structural rule
```

More in [implementations/python/README.md](implementations/python/README.md) and
[docs/guides/apply-with-tools.md](docs/guides/apply-with-tools.md). It needs Python 3.11 or later and has no
dependencies in its core; Google Sheets sync is an optional extra (`esoi[sheets]`).

## Contributing and licence

Only Joshua, or an AI acting on his own prompt, edits this repository; others open an issue or a pull request that
he reviews (see [CONTRIBUTING.md](CONTRIBUTING.md)). Apache-2.0, see [LICENSE](LICENSE).
