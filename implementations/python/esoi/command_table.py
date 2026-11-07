"""Build the sub-command parsers of a container from a text table, so each ``commands.py`` states only what is its own: the commands, their
arguments and their handlers.

A table is text. A line that starts at the left edge is a command, ``name | options | help``; each indented line under it is one argument,
``flags | options | help``, where flags are comma-separated (``--from`` or a bare ``name`` for a positional) and options are space-separated
``key=value`` pairs for ``add_argument`` (``action``, ``default``, ``choices`` as a comma list, ``type=int``, ``nargs``, ``metavar`` as a comma
pair, ``dest``, ``required``) plus ``group=NAME`` to put arguments in one mutually exclusive group. A command's options may be ``add_help=False``
or ``needs_config=False``. A value that is a Python literal is read as one (``8``, ``True``, ``None``, ``[]``); anything else is a string, and an
empty value is the empty string. The handler of a command is the ``run_<name>`` function of the module that owns the table (dashes become underscores).
"""
from __future__ import annotations

import argparse
import ast
from typing import Any, Callable, Dict, Optional

TYPES = {"int": int}


def literal(text: str) -> Any:
    """The Python literal a value spells, else the text itself."""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def option_value(key: str, text: str) -> Any:
    """One ``key=value`` option of an argument or command as ``argparse`` takes it."""
    if key == "choices":
        return [literal(part) for part in text.split(",")]
    if key == "metavar" and "," in text:
        return tuple(text.split(","))
    if key == "nargs" and text == "REMAINDER":
        return argparse.REMAINDER
    if key == "type":
        return TYPES[text]
    return literal(text)


def options_of(text: str) -> Dict[str, Any]:
    """The ``key=value`` pairs of an options field."""
    pairs = (part.partition("=") for part in text.split())
    return {key: option_value(key, value) for key, _, value in pairs}


def split_fields(line: str) -> list:
    """The three fields of a table line: its name or flags, its options and its help."""
    fields = [part.strip() for part in line.strip().split("|", 2)]
    return fields + [""] * (3 - len(fields))


def add_argument(parser: argparse.ArgumentParser, line: str, groups: Dict[str, Any]) -> None:
    flags, text, help_text = split_fields(line)
    options = options_of(text)
    target = parser
    if "group" in options:
        name = options.pop("group")
        if name not in groups:
            groups[name] = parser.add_mutually_exclusive_group()
        target = groups[name]
    if help_text:
        options["help"] = help_text
    target.add_argument(*flags.split(","), **options)


def register(sub, table: str, handlers: Dict[str, Callable], extra: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """Add every command of ``table`` to the sub-parsers ``sub``; ``handlers`` is the owning module's namespace and ``extra`` adds
    ``set_defaults`` values to a command by name (for a value that is code, such as a function of the parsed arguments)."""
    parser = None
    groups: Dict[str, Any] = {}
    for line in table.splitlines():
        if not line.strip():
            continue
        if line[0] != " ":
            name, text, help_text = split_fields(line)
            options = options_of(text)
            parser = sub.add_parser(name, help=help_text, add_help=options.pop("add_help", True))
            parser.set_defaults(handler=handlers["run_" + name.replace("-", "_")], **options, **(extra or {}).get(name, {}))
            groups = {}
        else:
            add_argument(parser, line, groups)
