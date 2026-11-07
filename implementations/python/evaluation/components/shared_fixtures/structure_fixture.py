"""Small projects for the Structure Quality cases, written into a temporary folder from text: generic shapes of structural incidents and clean
exemplars. Nothing here names an adopter, a person or a machine path, and nothing calls a model. ``project(name)`` returns the folder of one shape
(built once per process); ``consumers`` and ``stage`` for a shape come from ``SHAPES``.

Each shape is a function that returns ``{relative path: text}``. The clean exemplar has four units, each a folder with an ``interface.py`` (a
Protocol, two arms that define its method, an ``__all__`` of the one name the other units use), an engine module of distinct small functions, an
``implementations.csv`` and one contract test over its arms. The other shapes change one thing in it, so a difference in a score is that change.
"""
from __future__ import annotations

import atexit
import os
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

UNITS = ["ledger", "planner", "mailer", "catalog"]
CACHE: Dict[str, Path] = {}

# Twelve function bodies that differ in structure (so none is a copy of another), three for each unit.
BODIES = [
    "    total = 0\n    for item in items:\n        if item > limit:\n            total += item * rate\n        else:\n            total -= item\n    return total\n",
    "    groups = {}\n    for key, value in pairs:\n        groups.setdefault(key, []).append(value)\n    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}\n",
    "    ordered = sorted(rows, key=lambda row: (row[1], row[0]))\n    first, rest = ordered[0], ordered[1:]\n    return first, [r for r in rest if r[1] != first[1]]\n",
    "    parts = []\n    for index, word in enumerate(words):\n        parts.append(word.upper() if index % 2 else word.lower())\n    return '-'.join(parts[:size])\n",
    "    if depth <= 0:\n        return [seed]\n    left = grow(seed * 2, depth - 1)\n    right = grow(seed * 2 + 1, depth - 1)\n    return left + right\n",
    "    count = 0\n    while value > 1:\n        value = value // 2 if value % 2 == 0 else value * 3 + 1\n        count += 1\n    return count\n",
    "    try:\n        left, right = text.split(sep, 1)\n    except ValueError:\n        return text, ''\n    return left.strip(), right.strip()\n",
    "    return [(a, b) for a in first for b in second if a != b and (a + b) % modulus == 0]\n",
    "    window = values[start:stop:step]\n    if not window:\n        return 0.0\n    mean = sum(window) / len(window)\n    return sum((v - mean) ** 2 for v in window) / len(window)\n",
    "    seen = set()\n    out = []\n    for name in names:\n        folded = name.casefold()\n        if folded not in seen:\n            seen.add(folded)\n            out.append(name)\n    return out\n",
    "    best, best_gap = None, None\n    for candidate in options:\n        gap = abs(candidate - target)\n        if best_gap is None or gap < best_gap:\n            best, best_gap = candidate, gap\n    return best\n",
    "    lookup = dict(zip(keys, range(len(keys))))\n    return [lookup[k] for k in order if k in lookup] or [-1]\n",
]
SIGNATURES = ["items, limit, rate", "pairs", "rows", "words, size", "seed, depth", "value", "text, sep", "first, second, modulus", "values, start, stop, step",
              "names", "options, target", "keys, order"]
FUNCTIONS = [("tally", 0), ("collect", 1), ("pick", 2), ("label", 3), ("grow", 4), ("steps", 5), ("divide", 6), ("pairing", 7), ("spread", 8), ("unique", 9),
             ("nearest", 10), ("positions", 11)]


def function_text(index: int, name: str = "") -> str:
    base, body = FUNCTIONS[index]
    name = name or base
    return f"def {name}({SIGNATURES[index]}):\n{BODIES[index].replace('grow(', name + '(') if base == 'grow' else BODIES[index]}"


def engine(unit: str, which: List[int]) -> str:
    return f'"""The work of {unit}."""\n\n\n' + "\n\n".join(function_text(i) for i in which) + "\n"


OPERATORS = ["+", "-", "*", "//", "%", "**", "|", "&", "^", "<<", ">>"]


STATEMENTS = ["data = data {op} {k}", "data = ({op} data) if data else {k}", "data = min(data {op} {k}, {k})", "data = [data {op} {k}][0]",
              "data = data {op} {k} if {k} else data", "data = abs(data) {op} {k}"]


def chain(n: int, shift: int) -> str:
    """Statements drawn from a seeded sequence per unit and arm, so no run of thirty tokens is shared between two interfaces."""
    chooser = random.Random(n * 10 + shift)
    out = []
    for i in range(9 + n):
        form = chooser.choice(STATEMENTS)
        op = chooser.choice(OPERATORS if "({op} data)" not in form else ["-", "~"])
        out.append("        " + form.format(op=op, k=i + n) + "\n")
    return "".join(out)


def bases(count: int) -> str:
    return "(" + ", ".join(["object"] * count) + ")" if count else ""


def interface(unit: str, n: int = 0) -> str:
    cls = unit.capitalize()
    extras = "".join(f", extra_{i}" for i in range(n))
    kwargs = "".join(f", note_{i}={i}" for i in range(n)) + ("" if n % 2 else ', example="."')
    head = ["[", "(", "{", "["][n % 4]
    return (f'"""The interface of {cls}: one Protocol and two arms."""\nfrom typing import Protocol\n\n'
            f"from esoi.runtime.implementation_selection.declare import implementation, solution\n\n"
            f'__all__ = ["{cls}Doing"]\n\n\n@solution("{unit}", kind="evaluate", entry="run"{kwargs})\nclass {cls}Doing(Protocol):\n'
            f'    """What {unit} does."""\n\n    def run(self, data{extras}): ...\n\n\n'
            f'@implementation("{unit}", "plain"{", weight=1" * (n % 3)})\nclass Plain{bases(n % 4)}:\n    """The plain way."""\n\n    def run(self, data{extras}):\n{chain(n, 0)}        return data\n\n\n'
            f'@implementation("{unit}", "careful"{", weight=2" * ((n + 1) % 3)})\nclass Careful{bases((n + 2) % 4)}:\n    """The careful way."""\n\n    def run(self, data{extras}):\n{chain(n, 5)}        return list(data)\n')


def implementations_csv(unit: str) -> str:
    desc = {"ledger": "records each amount against an account and reports balances by period",
            "planner": "orders tasks by their dates and reports what is due next",
            "mailer": "writes each message for its recipient and reports delivery",
            "catalog": "lists each item with its price and reports what is in stock"}[unit]
    return ("implementation_id,solution_id,filepath,name,description,advantages,disadvantages,sub_intent,uses_solution_ids\n"
            f"{unit}:plain,{unit},app/{unit}/interface.py::Plain,Plain,{unit} {desc} the plain way,,,,\n"
            f"{unit}:careful,{unit},app/{unit}/interface.py::Careful,Careful,{unit} {desc} the careful way,,,,\n")


def contract_test(unit: str) -> str:
    return (f'"""One contract run against every arm of {unit}."""\nimport pytest\n\nARMS = ["plain", "careful"]\n\n\n'
            f'@pytest.mark.parametrize("arm", ARMS)\ndef test_{unit}_keeps_its_data(arm):\n    assert arm and "{unit}"\n')


def exemplar(long_function: bool = False) -> Dict[str, str]:
    files: Dict[str, str] = {}
    for n, unit in enumerate(UNITS):
        others = UNITS[(n + 1) % len(UNITS)]
        files[f"app/{unit}/__init__.py"] = ""
        files[f"app/{unit}/engine.py"] = engine(unit, [3 * n, 3 * n + 1, 3 * n + 2])
        files[f"app/{unit}/interface.py"] = interface(unit, n)
        files[f"app/{unit}/implementations.csv"] = implementations_csv(unit)
        files[f"app/{unit}/solutions.csv"] = f"solution_id,name\n{unit},{unit.capitalize()}\n"
        files[f"tests/test_{unit}.py"] = contract_test(unit)
    # one unit reads another through its interface only, so the flow is written and called
    files["app/ledger/use.py"] = '"""Ledger reads planner through its entry point."""\nfrom app.planner.interface import PlannerDoing\n\n\ndef ask(planner: PlannerDoing):\n    return planner.run([1], 2)\n'
    files["app/planner/use.py"] = '"""Planner reads mailer through its entry point."""\nfrom app.mailer.interface import MailerDoing\n\n\ndef ask(mailer: MailerDoing, more):\n    return [mailer.run(item, 1, 2) for item in more]\n'
    files["app/mailer/use.py"] = '"""Mailer reads catalog through its entry point."""\nfrom app.catalog.interface import CatalogDoing\n\n\ndef ask(catalog: CatalogDoing):\n    first = catalog.run(3, 1, 2, 3)\n    return first or None\n'
    if long_function:
        lines = "".join(f"    step_{i} = tidy(data, {i}) if data else {i}\n" for i in range(1, 121))
        files["app/catalog/bulk.py"] = f'"""One long routine."""\n\n\ndef tidy(data, n):\n    return data\n\n\ndef everything(data):\n{lines}    return data\n'
    return files


def tiny_split() -> Dict[str, str]:
    """The same project as ``exemplar(long_function=True)`` with the long routine cut into many tiny files, each reloading its own context, and
    the other units reaching those files directly instead of the entry point."""
    files = exemplar(False)
    for i in range(1, 41):
        files[f"app/catalog/parts_{i // 10}/step_{i}.py"] = (f'"""Part {i} of the routine."""\n\n\ndef step_{i}(data):\n    context = dict(data or {{}})\n    context.setdefault("seen", [])\n'
                                                f'    context["seen"].append({i})\n    value = context.get("value", 0) + {i}\n    context["value"] = value\n    return context\n')
    files["app/ledger/use.py"] = '"""Ledger reaches into the parts of catalog."""\n' + "".join(f"from app.catalog.parts_{i // 10}.step_{i} import step_{i}\n" for i in range(1, 6)) + \
        "from app.planner.engine import tally\nfrom app.mailer.engine import label\n\n\ndef ask(data):\n    return tally(data, 1, 2), label(['a'], 1)\n"
    files["app/planner/use.py"] = '"""Planner reaches into catalog and mailer."""\n' + "".join(f"from app.catalog.parts_{i // 10}.step_{i} import step_{i}\n" for i in range(6, 11)) + \
        "from app.mailer.engine import divide\n\n\ndef ask(data):\n    return divide('a=b', '=')\n"
    return files


def flat_tree() -> Dict[str, str]:
    files = exemplar(False)
    for i in range(1000):
        files[f"app/catalog/generated/part_{i}.py"] = f'"""Part {i}."""\nVALUE_{i} = {i}\n'
    return files


def long_solution_list() -> Dict[str, str]:
    files = exemplar(False)
    rows = "".join(f"    {{'id': {i}, 'name': 'record {i}', 'tags': [{i}, {i + 1}]}},\n" for i in range(74))
    body = "".join(f"    value_{{k}} = apply(value, {{k}}) if value else {{k}}\n" for k in range(1, 161))
    functions = "".join(f"def solution_{n}(value):\n" + body.replace("{k}", "{k}") .replace("{k}", "7") + "    return value\n\n\n" for n in range(33))
    files["app/catalog/solutions_list.py"] = f'"""A list of solutions and one function each."""\nRECORDS = [\n{rows}]\n\n\ndef apply(value, k):\n    return value\n\n\n{functions}'
    return files


def stripped_interfaces(count: int = 4) -> Dict[str, str]:
    """A merge that left every arm of the first ``count`` solutions with no method: the arms keep their decorator and name only."""
    files = exemplar(False)
    for n, unit in enumerate(UNITS[:count]):
        cls = unit.capitalize()
        text = interface(unit, n)
        for arm, marker in (("Plain", "        return data\n"), ("Careful", "        return list(data)\n")):
            start = text.index(f"class {arm}")
            end = text.index(marker, start) + len(marker)
            decorator_end = text.index(":\n", start) + 2
            text = text[:decorator_end] + f'    """The {arm.lower()} way."""\n    pass\n' + text[end:]
        files[f"app/{unit}/interface.py"] = text
    return files


def protocol_folder(layered: bool) -> Dict[str, str]:
    """``exemplar`` plus one folder, ``app/stack``, that declares three Protocols, each with one arm. ``layered``: the store's arm takes the cache
    as a constructor need and the cache's arm takes the backend (one job in layers); otherwise the three arms need nothing of each other (three jobs)."""
    files = exemplar(False)
    layers = [("store", "cache", "put"), ("cache", "backend", "keep"), ("backend", "", "write")]
    parts = ['"""One folder, three Protocols."""\nimport typing\n\nfrom esoi.runtime.implementation_selection import declare\n\n\n']
    for k, (name, below, verb) in enumerate(layers):
        cls, lower = name.capitalize(), below.capitalize()
        parts.append(f'@declare.solution("{name}", kind="evaluate", entry="{verb}")\nclass {cls}Doing(typing.Protocol):\n    """What the {name} does."""\n\n    def {verb}(self, item): ...\n\n\n')
        init = f"    def __init__(self, below: {lower}Doing):\n        self.below = below\n\n" if layered and below else ""
        work = f"        item = item + {k + 7}\n        return self.below.{layers[k + 1][2]}(item)\n" if layered and below else f"        item = item * {k + 3}\n        return item - {k + 11}\n"
        parts.append(f'@declare.implementation("{name}", "own")\nclass {cls}Own:\n    """The {name}\'s own way."""\n\n{init}    def {verb}(self, item):\n{work}\n\n')
    files["app/stack/__init__.py"] = ""
    files["app/stack/interface.py"] = "".join(parts).rstrip("\n") + "\n"
    files["app/stack/solutions.csv"] = "solution_id,name\nstore,Store\ncache,Cache\nbackend,Backend\n"
    return files


def stripped_members() -> Dict[str, str]:
    """A merge that kept each arm's one main method and dropped the rest of the interface: the Protocol declares a second member the arms never define."""
    files = exemplar(False)
    for n, unit in enumerate(UNITS):
        text = interface(unit, n)
        text = text.replace("    def run(self, data" + "".join(f", extra_{i}" for i in range(n)) + "): ...\n", "    def run(self, data" + "".join(f", extra_{i}" for i in range(n)) + "): ...\n\n    def describe(self): ...\n", 1)
        files[f"app/{unit}/interface.py"] = text
    return files


def mismatched_parameters() -> Dict[str, str]:
    """A merge that kept the method names of the interface but not its parameters: every arm takes ``payload`` where the Protocol passes ``data``."""
    files = exemplar(False)
    for n, unit in enumerate(UNITS):
        text = interface(unit, n)
        head, _, rest = text.partition("@implementation")
        files[f"app/{unit}/interface.py"] = head + "@implementation" + rest.replace("def run(self, data", "def run(self, payload")
    return files


def arms_of_no_solution() -> Dict[str, str]:
    """A merge that renamed the solutions and left the arms declaring the old ids."""
    files = exemplar(False)
    for n, unit in enumerate(UNITS):
        text = interface(unit, n)
        files[f"app/{unit}/interface.py"] = text.replace(f'@implementation("{unit}"', f'@implementation("{unit}-before-the-merge"')
    return files


def library_names_consumer() -> Dict[str, str]:
    files = exemplar(False)
    files["app/ledger/engine.py"] += '\n\ndef label_for(account):\n    return f"shopfront {account}"  # the library knows its shop\n\n\ndef report():\n    shopfront = 1\n    return shopfront\n'
    return files


def due_arithmetic_copied() -> Dict[str, str]:
    files = exemplar(False)
    arithmetic = ("def is_due(last, every, now):\n    gap = now - last\n    periods = gap // every\n    remainder = gap - periods * every\n"
                  "    if remainder == 0 and periods >= 1:\n        return True\n    return gap >= every * 1.5\n")
    for unit in UNITS + ["billing", "reminders"]:
        files[f"app/{unit}/due.py"] = f'"""Due dates in {unit}."""\n\n\n{arithmetic}'
        files.setdefault(f"app/{unit}/__init__.py", "")
    return files


def import_cycle() -> Dict[str, str]:
    files = exemplar(False)
    files["app/catalog/use.py"] = '"""Catalog reads ledger, which reads catalog."""\nfrom app.ledger.interface import LedgerDoing\n\n\ndef ask(ledger: LedgerDoing):\n    return ledger.run([4])\n'
    files["app/planner/use.py"] = '"""Planner reads ledger."""\nfrom app.ledger.interface import LedgerDoing\n\n\ndef ask(ledger: LedgerDoing):\n    return ledger.run([5])\n'
    files["app/ledger/use.py"] = ('"""Ledger reads planner and catalog."""\nfrom app.planner.interface import PlannerDoing\nfrom app.catalog.interface import CatalogDoing\n\n\n'
                                  "def ask(planner: PlannerDoing, catalog: CatalogDoing):\n    return planner.run([1]), catalog.run([2])\n")
    return files


def no_contract() -> Dict[str, str]:
    files = exemplar(False)
    for unit in UNITS:
        files.pop(f"tests/test_{unit}.py")
    return files


def unused_exports() -> Dict[str, str]:
    files = exemplar(False)
    for unit in UNITS:
        cls = unit.capitalize()
        files[f"app/{unit}/interface.py"] = files[f"app/{unit}/interface.py"].replace(f'__all__ = ["{cls}Doing"]', f'__all__ = ["{cls}Doing", "Plain", "Careful", "Spare{cls}"]')
    return files


def cochange_hidden() -> Dict[str, str]:
    """Two units that no import joins, whose files the history shows changing together (the history is written by ``add_history``)."""
    files = exemplar(False)
    for name in ("app/ledger/use.py", "app/planner/use.py", "app/mailer/use.py"):
        files.pop(name)
    return files


def front_door_and_entries() -> Dict[str, str]:
    """Every way to reach another unit that is declared: the package's front door (``__init__.py`` and ``api.py``) importing entries and a helper,
    a unit's own ``__init__.py`` re-export, a module that declares an ``@implementation``, a name taken from the front door that is an entry, and a ``run`` call."""
    files = exemplar(False)
    files["app/__init__.py"] = "from app.ledger.interface import LedgerDoing\nfrom app.planner.interface import PlannerDoing\n"
    files["app/api.py"] = ('"""The public API."""\nfrom app.catalog.engine import tally\nfrom app.mailer.interface import MailerDoing\n'
                           'from app.planner.interface import PlannerDoing\n\n__all__ = ["MailerDoing", "PlannerDoing", "tally"]\n')
    files["app/catalog/__init__.py"] = "from app.catalog.engine import tally\n"
    files["app/mailer/arms.py"] = ('"""A declared arm in its own file."""\nfrom esoi.runtime.implementation_selection.declare import implementation\n\n\n'
                                   '@implementation("mailer", "terse")\nclass Terse:\n    """The terse way."""\n\n    def run(self, data, extra_0, extra_1):\n        return data\n')
    files["app/ledger/use.py"] = ('"""Ledger reads through declared entries only."""\nfrom app.api import PlannerDoing\nfrom app.catalog import tally\n'
                                  'from app.mailer.arms import Terse\n\n\ndef ask(planner: PlannerDoing):\n    return planner.run([1], 2), tally([1], 2, 3), Terse().run(1, 2, 3), run("mailer")\n')
    return files


def reach_into_internals() -> Dict[str, str]:
    """A unit imports an engine module of another unit, which is not its entry."""
    files = exemplar(False)
    files["app/ledger/use.py"] = '"""Ledger reaches into the planner engine."""\nfrom app.planner.engine import pick\n\n\ndef ask(rows):\n    return pick(rows)\n'
    return files


def reach_in_behind_the_front_door() -> Dict[str, str]:
    """The same reach-in with the import moved behind a re-export in the front door: the exported name is not a declared entry, so it still counts."""
    files = exemplar(False)
    files["app/api.py"] = '"""The public API."""\nfrom app.planner.engine import pick\n\n__all__ = ["pick"]\n'
    files["app/ledger/use.py"] = '"""Ledger reads the planner through the front door."""\nfrom app.api import pick\n\n\ndef ask(rows):\n    return pick(rows)\n'
    return files


KERNEL = ('"""Settings and errors every unit shares."""\n\n\nclass SettingsError(Exception):\n    """A setting that cannot be read."""\n\n\n'
          'class Settings:\n    """The settings of one run."""\n\n    def __init__(self, values):\n        self.values = dict(values)\n\n\n'
          'def load_settings(values=None):\n    if values is not None and not isinstance(values, dict):\n        raise SettingsError(values)\n    return Settings(values or {})\n')
SETTINGS_USE = ["    found = load_settings(values)\n    return found.values.get(key) if isinstance(found, Settings) else None\n",
                "    found = load_settings(values)\n    return isinstance(found, Settings) and key in found.values\n",
                "    try:\n        return len(load_settings(values).values) > key\n    except SettingsError:\n        return False\n",
                "    if not isinstance(values, dict):\n        raise SettingsError(values)\n    return sorted(load_settings({key: values}).values)\n"]


def foundation_kernel(reaches_up: bool = False) -> Dict[str, str]:
    """A small configuration and error module with no imports, imported by every unit, each name taken by two or more units: a shared kernel.
    ``reaches_up``: the same module imports a solution's engine, so it depends on a solution and is not a kernel."""
    files = exemplar(False)
    files["app/common/config.py"] = KERNEL if not reaches_up else KERNEL.replace('"""\n\n\n', '"""\nfrom app.planner.engine import label\n\n\n', 1) + \
        "\n\ndef labelled(words):\n    return label(words, 2)\n"
    taken = ["Settings, load_settings", "Settings, load_settings", "SettingsError, load_settings", "SettingsError, load_settings"]
    for n, unit in enumerate(UNITS):
        files[f"app/{unit}/setup.py"] = (f'"""How {unit} reads its settings."""\nfrom app.common.config import {taken[n]}\n\n\n'
                                         f"def setting_of_{unit}(values, key):\n{SETTINGS_USE[n]}")
    return files


def kernel_dump() -> Dict[str, str]:
    """Each unit's own engine moved into one foundation module that every unit imports, so the imports look like a shared kernel; every name is taken by one unit."""
    files = exemplar(False)
    files["app/common/shared.py"] = '"""Everything in one place."""\n\n\n' + "\n\n".join(function_text(i) for i in range(12)) + "\n"
    for n, unit in enumerate(UNITS):
        names = [FUNCTIONS[i][0] for i in (3 * n, 3 * n + 1, 3 * n + 2)]
        files[f"app/{unit}/engine.py"] = (f'"""The work of {unit}, kept in the shared module."""\nfrom app.common.shared import {", ".join(names)}\n\n\n'
                                          f"def run_{unit}(data):\n    return {names[0]}, {names[1]}, {names[2]}, data\n")
    return files


EXTRA_MEMBERS = ["describe", "validate", "export", "reset"]


def fat_interface(stubbed: bool) -> Dict[str, str]:
    """Each Protocol gains four members beyond ``run``. ``stubbed``: the arms meet them with ``pass``, ``...`` or ``raise NotImplementedError``;
    otherwise the arms implement them and the callers still use only ``run``."""
    files = exemplar(False)
    stubs = ["        pass\n", "        ...\n", "        raise NotImplementedError\n", '        """Nothing yet."""\n']
    for n, unit in enumerate(UNITS):
        text = interface(unit, n)
        protocol_end = text.index("\n\n\n@implementation")
        text = text[:protocol_end] + "".join(f"\n\n    def {m}(self): ..." for m in EXTRA_MEMBERS) + text[protocol_end:]
        for arm, marker in (("Plain", "        return data\n"), ("Careful", "        return list(data)\n")):
            end = text.index(marker, text.index(f"class {arm}")) + len(marker)
            if stubbed:
                added = "".join(f"\n    def {m}(self):\n{stubs[k]}" for k, m in enumerate(EXTRA_MEMBERS))
            else:
                added = "".join(f"\n    def {m}(self):\n        return '{unit} {arm.lower()} {m} {k * 7 + n}'\n" for k, m in enumerate(EXTRA_MEMBERS))
            text = text[:end] + added + text[end:]
        files[f"app/{unit}/interface.py"] = text
    return files


def star_re_export() -> Dict[str, str]:
    """A reach-in into the planner's engine moved behind ``import *`` in the planner's own ``__init__.py``."""
    files = exemplar(False)
    files["app/planner/__init__.py"] = "from app.planner.engine import *\n"
    files["app/ledger/use.py"] = '"""Ledger reads the planner through its package."""\nfrom app.planner import label\n\n\ndef ask(words):\n    return label(words, 1)\n'
    return files


def explicit_re_exports() -> Dict[str, str]:
    """The planner's ``__init__.py`` re-exports every engine function by name and the ledger uses one of them."""
    files = exemplar(False)
    files["app/planner/__init__.py"] = "from app.planner.engine import label, grow, steps\n"
    files["app/ledger/use.py"] = ('"""Ledger reads planner through its entry point and one re-exported function."""\nfrom app.planner import label\n'
                                  'from app.planner.interface import PlannerDoing\n\n\ndef ask(planner: PlannerDoing):\n    return planner.run([1], 2), label(["a"], 1)\n')
    return files


CHAIN = ["front", "middle", "back"]


def split_into_many() -> Dict[str, str]:
    """The catalog solution split into a chain of four solution folders: three of them only hand each call on to the next."""
    files = exemplar(False)
    for k, piece in enumerate(CHAIN):
        unit = f"catalog_{piece}"
        nxt = f"catalog_{CHAIN[k + 1]}" if k + 1 < len(CHAIN) else "catalog"
        cls, next_cls = unit.title().replace("_", ""), nxt.title().replace("_", "")
        files[f"app/{unit}/__init__.py"] = ""
        files[f"app/{unit}/solutions.csv"] = f"solution_id,name\n{unit},{cls}\n"
        files[f"app/{unit}/implementations.csv"] = (
            "implementation_id,solution_id,filepath,name,description,advantages,disadvantages,sub_intent,uses_solution_ids\n"
            f"{unit}:plain,{unit},app/{unit}/interface.py::Plain,Plain,{unit} hands the listing on the plain way,,,,\n"
            f"{unit}:careful,{unit},app/{unit}/interface.py::Careful,Careful,{unit} hands the listing on the careful way,,,,\n")
        arms = "".join(f'@implementation("{unit}", "{arm.lower()}")\nclass {arm}:\n    """The {arm.lower()} way."""\n\n    def __init__(self, following: {next_cls}Doing):\n'
                       f"        self.following = following\n\n    def run(self, data, extra_0, extra_1, extra_2):\n        return self.following.run(data, extra_0, extra_1, extra_2)\n\n\n"
                       for arm in ("Plain", "Careful"))
        files[f"app/{unit}/interface.py"] = (f'"""The interface of {cls}: one Protocol and two arms."""\nfrom typing import Protocol\n\n'
                                             f"from app.{nxt}.interface import {next_cls}Doing\n"
                                             f"from esoi.runtime.implementation_selection.declare import implementation, solution\n\n"
                                             f'__all__ = ["{cls}Doing"]\n\n\n@solution("{unit}", kind="evaluate", entry="run")\nclass {cls}Doing(Protocol):\n'
                                             f'    """What {unit} does."""\n\n    def run(self, data, extra_0, extra_1, extra_2): ...\n\n\n{arms}')
        files[f"tests/test_{unit}.py"] = contract_test(unit)
    files["app/mailer/use.py"] = ('"""Mailer reads the catalog chain through its entry point."""\nfrom app.catalog_front.interface import CatalogFrontDoing\n\n\n'
                                  "def ask(catalog: CatalogFrontDoing):\n    first = catalog.run(3, 1, 2, 3)\n    return first or None\n")
    return files


def deleted_hard_code() -> Dict[str, str]:
    """``real_structure`` with its long routine deleted and nothing put in its place: what a static score cannot see."""
    files = exemplar(True)
    files.pop("app/catalog/bulk.py")
    return files


SHAPES = {
    "clean_exemplar": (exemplar, {}),
    "real_structure": (lambda: exemplar(True), {}),
    "tiny_split": (tiny_split, {}),
    "flat_tree": (flat_tree, {}),
    "long_solution_list": (long_solution_list, {}),
    "stripped_interfaces": (stripped_interfaces, {}),
    "one_solution_off_its_interface": (lambda: stripped_interfaces(1), {}),
    "two_solutions_off_their_interfaces": (lambda: stripped_interfaces(2), {}),
    "three_solutions_off_their_interfaces": (lambda: stripped_interfaces(3), {}),
    "layered_protocols": (lambda: protocol_folder(True), {}),
    "unrelated_protocols": (lambda: protocol_folder(False), {}),
    "stripped_members": (stripped_members, {}),
    "mismatched_parameters": (mismatched_parameters, {}),
    "arms_of_no_solution": (arms_of_no_solution, {}),
    "library_names_consumer": (library_names_consumer, {"consumers": ("shopfront",)}),
    "due_arithmetic_copied": (due_arithmetic_copied, {}),
    "import_cycle": (import_cycle, {}),
    "front_door_and_entries": (front_door_and_entries, {}),
    "reach_into_internals": (reach_into_internals, {}),
    "reach_in_behind_the_front_door": (reach_in_behind_the_front_door, {}),
    "no_contract": (no_contract, {}),
    "unused_exports": (unused_exports, {}),
    "cochange_hidden": (cochange_hidden, {"history": "hidden"}),
    "cochange_explained": (exemplar, {"history": "explained"}),
    "foundation_kernel": (foundation_kernel, {}),
    "kernel_reaches_up": (lambda: foundation_kernel(reaches_up=True), {}),
    "kernel_dump": (kernel_dump, {}),
    "stub_arms": (lambda: fat_interface(stubbed=True), {}),
    "unused_members": (lambda: fat_interface(stubbed=False), {}),
    "star_re_export": (star_re_export, {}),
    "explicit_re_exports": (explicit_re_exports, {}),
    "split_into_many": (split_into_many, {}),
    "deleted_hard_code": (deleted_hard_code, {}),
}


def add_history(root: Path, kind: str) -> None:
    """A git history of eight commits in which ``ledger/engine.py`` and ``mailer/engine.py`` always change together (``explained``: they also import each other's entry point)."""
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
    run = lambda *args: subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)
    run("init", "-q")
    if kind == "explained":
        (root / "app/ledger/use.py").write_text('"""Ledger reads mailer."""\nfrom app.mailer.interface import MailerDoing\n\n\ndef ask(m: MailerDoing):\n    return m.run([1])\n')
    run("add", "-A")
    run("commit", "-q", "-m", "start")
    for n in range(8):
        for unit in ("ledger", "mailer"):
            with (root / f"app/{unit}/engine.py").open("a") as handle:
                handle.write(f"\nSTAMP_{n} = {n}\n")
        run("add", "-A")
        run("commit", "-q", "-m", f"change {n}")


def history_checkout(ref: str) -> Path:
    """A throwaway worktree of this library's own repository at one commit (a case from git history), removed when the process ends."""
    repo = Path(__file__).resolve().parents[5]
    found = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], capture_output=True, text=True)
    if found.returncode != 0:
        raise ValueError(f"commit {ref} is not in this clone (a git-history case needs the full history)")
    folder = scratch_root() / f"history_{len(CACHE)}" / "tree"
    folder.parent.mkdir()
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(folder), found.stdout.strip()], capture_output=True, text=True, check=True)
    atexit.register(lambda: (subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(folder)], capture_output=True, text=True),
                             subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True, text=True)))
    return folder


SCRATCH: List[tempfile.TemporaryDirectory] = []


def scratch_root() -> Path:
    """The one temporary folder of this process, where every shape and checkout is written; it is deleted when the process ends (also after an error)."""
    if not SCRATCH:
        SCRATCH.append(tempfile.TemporaryDirectory(prefix="esoi_sq_"))
    return Path(SCRATCH[0].name)


def project(name: str) -> Path:
    """The folder of one shape, written once per process under the temporary directory; ``git:<commit>`` is this library's own history at that commit."""
    if name.startswith("git:") and name not in CACHE:
        CACHE[name] = history_checkout(name[4:])
    if name not in CACHE:
        build, extra = SHAPES[name]
        root = scratch_root() / name
        root.mkdir()
        for rel, text in build().items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        if extra.get("history"):
            add_history(root, extra["history"])
        CACHE[name] = root
    return CACHE[name]


def options(name: str) -> dict:
    return {} if name.startswith("git:") else SHAPES[name][1]
