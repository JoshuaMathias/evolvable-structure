"""esoi: Evolvable Structure that Optimizes Intent (ESOI) as a library and a command.

An adopting repository keeps its intent as records (problems, ideals, solutions, implementations, metrics),
its placement as components, and its measurements as a results log. This package checks them against each
other (``esoi check``), runs and records evaluations (``esoi run``), ranks implementations
(``esoi leaderboard``), resolves a selection table at run time (``esoi.select``) and builds a review
tracker (``esoi tracker``). Everything specific to a repository is configuration (``esoi.toml``).

In code, declare a solution once where it lives and call it::

    from esoi import solution, implementation, override

    @solution("greet-a-person")
    def greet(name): ...

    @implementation("greet-a-person", "plain")
    def plain(name): return f"Hello, {name}!"

    greet("Ada")                      # the project default, from the records
    greet("Ada", using="loud")        # this call only
    with override("greet-a-person", "loud"): ...   # a block

See ``esoi.runtime`` for the cascade (call, context, environment, deployment, project).
"""
from .runtime import SelectionError, implementation, override, register, resolve, solution

__version__ = "0.2.0"
