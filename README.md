# Evolvable Structure that Optimizes Intent (ESOI)

ESOI is Joshua Mathias's way to make sure what you intend actually happens, and keeps getting better. You put your
intent into words (a name and a vision) and a few short kinds of record (the problem, the ideal you want, the solution, the ways of doing it,
and how to measure them), try more than one way, and let a measurement pick the best. The structure stays steady while
the ways of doing things improve, and it changes with you when your intent does.

It works for anything with an intent and more than one way to serve it: a product, code, a course, a coaching program,
a team process, a personal schedule. You need no code to use it.

**[Read the guide on the wiki](https://github.com/JoshuaMathias/evolvable-structure/wiki)**

## Start here

1. **[What ESOI is](https://github.com/JoshuaMathias/evolvable-structure/wiki/What-ESOI-is)**: the idea in five minutes.
2. **[The ESOI steps](https://github.com/JoshuaMathias/evolvable-structure/wiki/The-ESOI-steps)**: what to do, in order,
   from your purpose to choosing by a measurement.
3. **[Apply ESOI by hand](https://github.com/JoshuaMathias/evolvable-structure/wiki/Apply-ESOI-by-hand)**: a first pass
   in about an hour, with fill-in templates and no tools.

The wiki is generated from [docs/](docs/README.md) in this repository, so the same pages are here too.

## Give the principles to an AI agent

The author's `evolvable-structure` skill carries the principles and the steps for Claude Code and similar agents.
[Install the skill](https://github.com/JoshuaMathias/evolvable-structure/wiki/Install-the-skill) as a plugin, a folder
download or with `esoi`.

## Check and measure with Python (optional)

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git#subdirectory=implementations/python"
esoi init            # scaffold a small example repository that already passes
esoi check           # run every structural rule
```

More in [Apply ESOI with the Python tools](https://github.com/JoshuaMathias/evolvable-structure/wiki/Apply-ESOI-with-the-Python-tools)
and [the package's README](implementations/python/README.md). It needs Python 3.11 or later and has no dependencies in
its core; Google Sheets sync is an optional extra (`esoi[sheets]`).

## What is in this repository

| Folder | What it holds |
|---|---|
| [`docs/`](docs/README.md) | The main feature: explanation, guides and templates, all non-code. The wiki is generated from it |
| [`skill/`](skill/) | The author's `evolvable-structure` skill as a self-contained folder and Claude Code plugin, generated from his own skill |
| [`implementations/python/`](implementations/python/) | The `esoi` package and command: checks, measuring, a leaderboard, a review tracker. One example implementation |
| [`examples/`](examples/) | Repositories that adopted ESOI, as short testimonials |
| [`structure/`](structure/) | ESOI applied to this repository: its top intent and its records |

## Contributing and licence

Only Joshua, or an AI acting on his own prompt, edits this repository; others open an issue or a pull request that
he reviews (see [CONTRIBUTING.md](CONTRIBUTING.md)). Edit pages in `docs/`, not on the wiki: the wiki is regenerated on
every push. Apache-2.0, see [LICENSE](LICENSE).
