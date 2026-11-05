"""S51 and S52: problems say what is true, and ideals say the state that is wanted. Advisory rules: they inform and never fail.

A problem describes the gap as it is today, so a sweeping absolute in it ("nobody tests the whole", "it is never measured") is
usually false, and a reader who knows the field stops trusting the record. S51 points at each absolute in a problem's text and
asks whether it is literally true, and if not, what the real gap is.

An ideal states the limit state a solution aims at, so its absolutes are the point and S51 does not read ideals. The trap for an
ideal is a different one: it is written as a solution (a mechanism, a tool, a component or a role: "Use one router for every model
call") instead of the state the people or system affected would be in ("Every request reaches a model that is up and fits its
budget"). S52 points at ideal text that reads like that and asks what state it wants (``docs/explanation/a-problem-says-what-is-true.md``).
"""
from __future__ import annotations

import re
from typing import List

from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S51": "Advisory: a problem says what is true. An absolute in a problem's text (never, nobody, no one, always, everyone, none, "
           "nothing, impossible, the only way, every time, all of) is informed with the words around it, asking whether it is literally "
           "true and, if not, what is missing, for whom, how often and at what cost; ideals are not read, since an ideal states the "
           "limit state (waive as the problem id, or problem_id:field when the absolute is true).",
    "S52": "Advisory: an ideal states the state that is wanted, not a solution. Ideal text that opens with an instruction to build or "
           "use something (use, build, add, implement, have a, keep a) or that names the means (a method such as 'by comparing' or 'is "
           "chosen', one component such as 'one intake' or 'one engine', or a mechanism such as configuration or adapters) is informed, "
           "asking what is true for the people or system affected when the ideal is reached (waive as the ideal id, or ideal_id:field).",
}

#: The problem fields a reader takes as a description of today; the ids and links are not prose.
PROBLEM_FIELDS = ("name", "problem", "who_has_it", "why_it_matters", "why_hard", "existing_attempts")
#: The ideal fields that describe the wanted state; hints of measurement may name how it is checked, so they are not read.
IDEAL_FIELDS = ("name", "principle", "state_description")

ABSOLUTES = re.compile(
    r"\b(never|nobody|no one|no-one|always|everyone|everybody|none|nothing|impossible|cannot ever|the only way|only way|every time|"
    r"all of (?:them|it|the)|not a single|no way to)\b",
    re.I,
)
INSTRUCTION = re.compile(r"^(use|using|build|add|implement|provide|create|store|cache|route|deploy|install|integrate|adopt|run|call|"
                         r"have an?|keep an?|make an?|introduce|wrap|expose)\b", re.I)
#: Phrases that name the means rather than the state: a method ("by comparing", "is chosen"), a single component ("one intake", "one
#: engine"), or a mechanism noun ("configuration", "adapters", "case set"). Written from 30 solution-shaped ideals found by reading
#: three repositories' records, so it is a finder of candidates for a person to read, never a verdict.
MEANS = re.compile(
    r"\b(?:by using|by means of|via an?|via the|"
    r"by (?:configuration|data|measurement|comparing|running|looking at|declaring|rule)|"
    r"through (?:an?|one|adapters|its own|the [\w-]+ (?:seat|tool|path|router|registry|engine|search))|"
    r"(?:is|are) (?:chosen|implemented|recorded as|kept as|planned|tested|judged against|wired|written once|routed|derived from)|"
    r"(?:implemented|written) once|"
    r"one (?:[\w-]+ ){0,2}(?:intake|engine|search|signal|router|path|catalog|registry|pipeline|index|harness)|"
    r"(?:has|have|holds?) (?:an?|one) (?:[\w-]+ ){0,2}(?:intake|metric|engine|index|router|catalog|registry|profile|interface|adapter)s?|"
    r"configuration|adapters?|catalog entry|case set|held-out|lockfile|a change of data)\b",
    re.I,
)


def around(text: str, start: int, end: int, width: int = 40) -> str:
    """The words around a match, cut at word boundaries, so the finding quotes the claim rather than one word."""
    left = text.rfind(" ", 0, max(start - width, 0)) + 1 if start > width else 0
    right = text.find(" ", min(end + width, len(text)))
    snippet = text[left:right if right != -1 else len(text)].strip()
    return ("..." if left else "") + snippet + ("..." if right != -1 else "")


def absolutes(ctx: Context) -> List[str]:
    """S51: each problem field that states a sweeping absolute, once per field, with the words around the first one."""
    out: List[str] = []
    for row in ctx.registry.problems:
        pid = row.get("problem_id", "").strip()
        if not pid or ctx.waived("S51", pid):
            continue
        for key in PROBLEM_FIELDS:
            text = " ".join((row.get(key) or "").split())
            found = list(ABSOLUTES.finditer(text))
            if not found or ctx.waived("S51", f"{pid}:{key}"):
                continue
            words = ", ".join(dict.fromkeys(m.group(0).lower() for m in found))
            out.append(f"S51 {pid}: its {key} says {around(text, found[0].start(), found[0].end())!r} ({words}). Is that literally true? "
                       "next: if not, say the real gap in plain words: what is missing, for whom, how often and at what cost, so someone "
                       "who knows the field would call it accurate; if it is true, waive it as "
                       f"{pid}:{key}")
    return out


def solution_shaped(ctx: Context) -> List[str]:
    """S52: each ideal field that reads as an instruction to build or use something, or that names the means."""
    out: List[str] = []
    for row in ctx.registry.ideals:
        iid = row.get("ideal_id", "").strip()
        if not iid or ctx.waived("S52", iid):
            continue
        for key in IDEAL_FIELDS:
            text = " ".join((row.get(key) or "").split())
            found = INSTRUCTION.match(text) or MEANS.search(text)
            if not found or ctx.waived("S52", f"{iid}:{key}"):
                continue
            out.append(f"S52 {iid}: its {key} says {around(text, found.start(), found.end())!r}, which reads like a solution (a means, "
                       "a tool, a component or a role). next: write the state that is wanted instead: what is true for the people or "
                       "system affected when this ideal is reached; the means belongs in a solution")
    return out


def run(ctx: Context) -> List[str]:
    if not ctx.config.is_disabled("S51"):
        ctx.advisory.extend(absolutes(ctx))
    if not ctx.config.is_disabled("S52"):
        ctx.advisory.extend(solution_shaped(ctx))
    return []


GROUP = RuleGroup(SUMMARIES, run)
