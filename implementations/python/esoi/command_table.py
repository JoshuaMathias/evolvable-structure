"""Build the sub-command parsers of a container from a text table, so each ``commands.py`` states only what is its own: the commands, their
arguments and their handlers.

A table is text. A line that starts at the left edge is a command, ``name | options | help``; each indented line under it is one argument,
``flags | options | help``, where flags are comma-separated (``--from`` or a bare ``name`` for a positional) and options are space-separated
``key=value`` pairs. The keys are a closed list, and a value is read by what its key means, never by how it looks:

* an argument takes ``action``, ``default``, ``choices`` (a comma list, each read by the argument's ``type``), ``type`` (``int``), ``nargs`` (``?``, ``*``, ``+``,
  ``REMAINDER`` or a whole number), ``metavar`` (a comma pair makes a tuple), ``dest``, ``required`` (``True`` or ``False``), and ``group=NAME`` to put arguments in one
  mutually exclusive group;
* ``default`` is the text after the ``=`` (empty for the empty string, so ``default=8`` is ``"8"`` and ``type=int`` makes ``argparse`` turn it into 8), except the two words
  ``None`` and ``[]``, which are those values;
* a command takes ``add_help`` and ``needs_config`` (``True`` or ``False``).

A key, a value or a handler the table does not allow stops the build with a ``TableError`` that names the line. The handler of a command is the
``run_<name>`` function of the module that owns the table (dashes become underscores).
"""
from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, List, Optional, Tuple

TYPES = {"int": int}
ARGUMENT_KEYS = ("action", "default", "choices", "type", "nargs", "metavar", "dest", "required", "group")
COMMAND_KEYS = ("add_help", "needs_config")
NARGS_WORDS = {"?": "?", "*": "*", "+": "+", "REMAINDER": argparse.REMAINDER}
DEFAULT_WORDS = {"None": None, "[]": []}


class TableError(ValueError):
    """A line of a command table that cannot be built; the message names the line."""


def boolean(text: str, options: Dict[str, Any]) -> bool:
    if text not in ("True", "False"):
        raise TableError(f"a boolean option must be True or False, not {text!r}")
    return text == "True"


def type_of(text: str, options: Dict[str, Any]) -> Callable:
    if text not in TYPES:
        raise TableError(f"type must be one of {', '.join(TYPES)}, not {text!r}")
    return TYPES[text]


def nargs_of(text: str, options: Dict[str, Any]) -> Any:
    if text in NARGS_WORDS:
        return NARGS_WORDS[text]
    if text.isdigit():
        return int(text)
    raise TableError(f"nargs must be ?, *, +, REMAINDER or a whole number, not {text!r}")


def choices_of(text: str, options: Dict[str, Any]) -> list:
    kind = options.get("type", str)   # write type= before choices=
    try:
        return [kind(part) for part in text.split(",")]
    except ValueError:
        raise TableError(f"choices {text!r} are not all valid for type {kind.__name__}") from None


def metavar_of(text: str, options: Dict[str, Any]) -> Any:
    return tuple(text.split(",")) if "," in text else text


def default_of(text: str, options: Dict[str, Any]) -> Any:
    return DEFAULT_WORDS.get(text, text)


READERS: Dict[str, Callable[[str, Dict[str, Any]], Any]] = {
    "required": boolean, "add_help": boolean, "needs_config": boolean, "type": type_of, "nargs": nargs_of, "choices": choices_of,
    "metavar": metavar_of, "default": default_of,
}


def option_value(key: str, text: str, options: Dict[str, Any]) -> Any:
    """One ``key=value`` option as ``argparse`` takes it (text unless the key says otherwise); ``options`` holds the ones read before it on the line."""
    return READERS.get(key, lambda value, read: value)(text, options)


def options_of(text: str, allowed: Tuple[str, ...]) -> Dict[str, Any]:
    """The ``key=value`` pairs of an options field; a key outside ``allowed`` is an error."""
    found: Dict[str, Any] = {}
    for part in text.split():
        key, equals, value = part.partition("=")
        if not equals:
            raise TableError(f"{part!r} is not key=value")
        if key not in allowed:
            raise TableError(f"unknown option {key!r} (allowed: {', '.join(allowed)})")
        found[key] = option_value(key, value, found)
    return found


def split_fields(line: str) -> List[str]:
    """The three fields of a table line: its name or flags, its options and its help."""
    fields = [part.strip() for part in line.strip().split("|", 2)]
    return fields + [""] * (3 - len(fields))


def add_argument(parser: argparse.ArgumentParser, line: str, groups: Dict[str, Any]) -> None:
    flags, text, help_text = split_fields(line)
    options = options_of(text, ARGUMENT_KEYS)
    target = parser
    if "group" in options:
        name = options.pop("group")
        if name not in groups:
            groups[name] = parser.add_mutually_exclusive_group()
        target = groups[name]
    if help_text:
        options["help"] = help_text
    target.add_argument(*flags.split(","), **options)


def add_command(sub, line: str, handlers: Dict[str, Callable], extra: Optional[Dict[str, Dict[str, Any]]]):
    """The sub-parser of one command line of the table."""
    name, text, help_text = split_fields(line)
    options = options_of(text, COMMAND_KEYS)
    handler = handlers.get("run_" + name.replace("-", "_"))
    if handler is None:
        raise TableError(f"command {name!r} has no function run_{name.replace('-', '_')}")
    parser = sub.add_parser(name, help=help_text, add_help=options.pop("add_help", True))
    parser.set_defaults(handler=handler, **options, **(extra or {}).get(name, {}))
    return parser


def register(sub, table: str, handlers: Dict[str, Callable], extra: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """Add every command of ``table`` to the sub-parsers ``sub``; ``handlers`` is the owning module's namespace and ``extra`` adds
    ``set_defaults`` values to a command by name (for a value that is code, such as a function of the parsed arguments)."""
    parser = None
    groups: Dict[str, Any] = {}
    for number, line in enumerate(table.splitlines(), 1):
        if not line.strip():
            continue
        try:
            if line[0] != " ":
                parser, groups = add_command(sub, line, handlers, extra), {}
            elif parser is None:
                raise TableError("an argument line comes before any command")
            else:
                add_argument(parser, line, groups)
        except (TableError, argparse.ArgumentError) as exc:
            raise TableError(f"command table line {number} ({line.strip()[:60]!r}): {exc}") from None
