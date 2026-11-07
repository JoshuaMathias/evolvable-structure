"""The command tables are read by what each key means: a typo or a value out of place fails the build and names the line."""
import argparse

import pytest

from esoi import command_table
from esoi.command_table import TableError


def build(table, **handlers):
    parser = argparse.ArgumentParser()
    command_table.register(parser.add_subparsers(dest="cmd"), table, {"run_go": lambda config, args: 0, **handlers})
    return parser


def test_a_value_is_read_by_its_key_and_never_by_its_look():
    parser = build("go | | do it\n    --n | type=int default=8 | a count\n    --name | default=007 | a name\n    --none | default=None |\n    --list | default=[] |\n")
    args = parser.parse_args(["go"])
    assert (args.n, args.name, args.none, args.list) == (8, "007", None, [])


def test_choices_are_read_by_the_arguments_type():
    args = build("go | |\n    --tier | type=int choices=0,1,2 default=1 |\n").parse_args(["go", "--tier", "2"])
    assert args.tier == 2


@pytest.mark.parametrize("line,words", [("    --n | defualt=3 |", ("line 2", "defualt")), ("    --n | required=yes |", ("line 2", "required")),
                                        ("    --n | type=float |", ("line 2", "float")), ("    --n | nargs=many |", ("line 2", "nargs")),
                                        ("    --n | default |", ("line 2", "key=value")), ("    --n | type=int choices=a,b |", ("line 2", "choices"))])
def test_a_mistake_in_a_table_line_fails_with_the_line_named(line, words):
    with pytest.raises(TableError) as caught:
        build("go | |\n" + line + "\n")
    assert all(word in str(caught.value) for word in words)


def test_a_command_without_its_handler_and_an_argument_before_any_command_are_named():
    with pytest.raises(TableError, match="run_missing"):
        build("missing | |\n")
    with pytest.raises(TableError, match="line 1"):
        build("    --n | |\n")
    with pytest.raises(TableError, match="unknown option"):
        build("go | needs_config=False colour=red |\n")


def test_the_command_options_are_booleans():
    assert build("go | needs_config=False |\n").parse_args(["go"]).needs_config is False
