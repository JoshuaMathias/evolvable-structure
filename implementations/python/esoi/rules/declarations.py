"""Rule S30: what the code declares (``@solution``, ``@implementation``, ``register``) is in the records.

The code is read, not imported (``esoi.declarations.scan``), so the check runs wherever the source is.
"""
from __future__ import annotations

from typing import List

from .. import declarations
from .base import Context, RuleGroup

SUMMARIES = {
    "S30": "Every solution and implementation declared in the measured code (@solution, @implementation, register) has "
           "its solutions.csv row and implementations.csv record, and the record's filepath is the declaring file; "
           "`esoi records sync` writes the missing rows.",
}


def run(ctx: Context) -> List[str]:
    measured = set(declarations.code_files(ctx.config))   # the code under measurement, not tests or fixtures
    declared = declarations.scan(ctx.config, [f for f in ctx.files if f in measured])
    return declarations.drift(ctx.config, ctx.registry, declared)


GROUP = RuleGroup(SUMMARIES, run)
