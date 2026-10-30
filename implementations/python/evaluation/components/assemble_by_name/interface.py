"""The assembly function. Every implementation is ONE function with this signature:

    assemble(kind: str, args: dict) -> dict

``kind`` is ``assemble`` (a throwaway package in a fresh scope; ``args`` as in ``assemble_fixture.package_case`` plus
``config`` (solutions, names, selections, options, selection_environ), ``register`` ([solution, name, "consumer:Class",
replace]), ``behind`` (the same, through ``esoi.runtime.register(..., replace=True)`` behind the assembler's back),
``override`` ({solution: name}), ``provided`` ({solution: "consumer:Class" | "object"}), ``threads`` and ``only_prepare``) or
``docs`` (``args['docs']`` is ``docstring`` or ``guide``: the examples in the docs are run).

It returns ``error`` (an exception class name, '' for none), ``text`` (its message), ``built`` ({solution: class name}),
``order`` (the solutions in build order), and three facts about the world afterwards: ``executed`` (a hostile file ran),
``path_same`` (``sys.path`` unchanged), ``arm_imports`` (times the default arm's module ran) and ``arm_loaded``.

The cases are the risks of a name-based assembly: a hostile name or snapshot, a hostile parent ``esoi.toml``, shadowing,
cycles and unmet needs, a Protocol that cannot be checked, concurrent assembles, and the docs' own examples. No model is called.
"""
