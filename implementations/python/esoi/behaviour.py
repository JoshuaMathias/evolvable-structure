"""Grading an AI agent's reply against a behaviour case: the cheap regex check, the model judge, and a command provider.

A behaviour case is one row of a sheet: a ``scenario`` an agent might be sent, the ``expected_behavior`` and the
``failure_mode`` in words, and two cheap checks written as semicolon-separated regular expressions, ``must_have`` (every
one must match the reply) and ``must_not`` (none may). The regexes are a prefilter, not the verdict, when a judge is used:

* without a judge, the reply passes when every ``must_have`` matches and no ``must_not`` does;
* with a judge, a reply that matches a ``must_not`` fails without a model call, and every other reply is graded by the
  judge against the case's expected behaviour and failure mode, so a reply that acts well in other words still passes.

The judge is a function ``judge(case, reply) -> (passed, reason)``. ``build_judge`` makes one from any provider with an
``answer(messages, model=None, system=None)`` method; ``CommandProvider`` is such a provider that pipes the prompt to a
command line, so the library depends on no model vendor. Nothing here calls a model unless a caller passes a provider.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

JUDGE_SYSTEM = """You grade one reply of an AI assistant for one test case. Grade what the reply DOES, not which words it uses:
a reply that does the expected thing in different words passes; a reply that uses the right vocabulary but does the failure
mode fails. Extra length or polish earns nothing. Adding structure (a framework, a registry, a process) is correct only when
the expected behavior asks for it; when the expected behavior says the small fix is right, a reply that builds structure fails.
Keeping a qualifier matters: a reply that states a rule without the condition the expected behavior keeps fails.

The assistant had no files, tools or shell in this run, by design. A reply that states the exact edit, text or plan it would
carry out counts as doing it: do not fail it merely for saying it cannot open a file. Do fail a reply that only asks
questions or asks for access and states no action.

Reply with only one JSON object: {"verdict": "pass" or "fail", "reason": "<one short line, no em dashes>"}."""

MAX_REPLY_CHARS = 6000
FLAGS = re.I | re.S


def split_patterns(cell: Optional[str]) -> List[str]:
    """The regular expressions in a semicolon-separated cell, blanks dropped."""
    return [p.strip() for p in (cell or "").split(";") if p.strip()]


def forbidden_hits(reply: str, case: Dict[str, Any]) -> List[str]:
    """The ``must_not`` patterns the reply matches (each is a reason to fail with no model call)."""
    return [f"must not match /{p}/" for p in split_patterns(case.get("must_not")) if re.search(p, reply, FLAGS)]


def regex_problems(reply: str, case: Dict[str, Any]) -> List[str]:
    """Every way the reply departs from the case's regexes; empty means it follows the expected behaviour."""
    missing = [f"missing /{p}/" for p in split_patterns(case.get("must_have")) if not re.search(p, reply, FLAGS)]
    return missing + forbidden_hits(reply, case)


def score_reply(reply: str, case: Dict[str, Any],
                judge: Optional[Callable[[Dict[str, Any], str], Tuple[bool, str]]] = None) -> Dict[str, Any]:
    """One result row for a reply: regex only without a judge, else the regex prefilter and then the judge."""
    problems = regex_problems(reply, case)
    row: Dict[str, Any] = dict(got=case["principle"].split(";")[0], regex_ok=not problems, reply=reply[:1500])
    if judge is None:
        return dict(row, ok=not problems, judged=False, note="ok" if not problems else "; ".join(problems)[:200])
    blocked = forbidden_hits(reply, case)
    if blocked:
        return dict(row, ok=False, judged=False, note="prefilter: " + "; ".join(blocked)[:200])
    passed, reason = judge(case, reply)
    return dict(row, ok=passed, judged=True, note=f"judge {'pass' if passed else 'fail'}: {reason}"[:240])


def principle_order(label: str) -> int:
    """Sort key for ``P0``, ``P1`` ... ``P13``."""
    digits = re.sub(r"\D", "", label or "")
    return int(digits) if digits else 99


def aggregate(rows: List[Dict[str, Any]]) -> str:
    """Pass counts per primary principle; with a judge, also where the regexes and the judge disagree."""
    kinds: Dict[Any, Tuple[int, int]] = {}
    for r in rows:
        passed, total = kinds.get(r.get("got"), (0, 0))
        kinds[r.get("got")] = (passed + bool(r.get("ok")), total + 1)
    text = ", ".join(f"{k} {p}/{t}" for k, (p, t) in sorted(kinds.items(), key=lambda kv: principle_order(str(kv[0]))))
    if any(r.get("judged") for r in rows):
        regex_pass = sum(bool(r.get("regex_ok")) for r in rows)
        judge_only = sum(bool(r.get("ok")) and not r.get("regex_ok") for r in rows)
        regex_only = sum(not r.get("ok") and bool(r.get("regex_ok")) for r in rows)
        text += (f" | regex-only {regex_pass}/{len(rows)}; judge passed what regex failed {judge_only}, "
                 f"judge failed what regex passed {regex_only}")
    return text


def judge_prompt(case: Dict[str, Any], reply: str) -> str:
    """The user message of one grading call. It carries the rubric in words and never the regexes or reference replies."""
    return (f"SCENARIO sent to the assistant:\n{case['scenario']}\n\n"
            f"EXPECTED BEHAVIOR:\n{case['expected_behavior']}\n\n"
            f"FAILURE MODE (a reply that does this fails):\n{case['failure_mode']}\n\n"
            f"REPLY TO GRADE:\n{reply[:MAX_REPLY_CHARS]}\n\nGrade the reply.")


def parse_verdict(text: Optional[str]) -> Tuple[bool, str]:
    """``(passed, reason)`` from the judge's text. An unparseable answer is a fail, never a pass."""
    found = re.search(r"\{.*\}", text or "", re.S)
    try:
        obj = json.loads(found.group(0)) if found else {}
    except ValueError:
        obj = {}
    verdict = str(obj.get("verdict", "")).strip().lower() if isinstance(obj, dict) else ""
    if verdict not in ("pass", "fail"):
        return False, "unparseable judge output: " + " ".join((text or "").split())[:80]
    return verdict == "pass", " ".join(str(obj.get("reason", "")).split())


def build_judge(provider: Any, model: Optional[str] = None) -> Callable[[Dict[str, Any], str], Tuple[bool, str]]:
    """``judge(case, reply) -> (passed, reason)`` made of one provider call per reply."""
    def judge(case: Dict[str, Any], reply: str) -> Tuple[bool, str]:
        text = provider.answer([{"role": "user", "content": judge_prompt(case, reply)}], model=model, system=JUDGE_SYSTEM)
        return parse_verdict(text)
    return judge


def skill_description(skill_text: str) -> str:
    """The ``description`` line of a skill's front matter (what an agent sees before it decides to load the skill)."""
    found = re.search(r"^description:\s*(.+)$", skill_text, re.M)
    return found.group(1).strip() if found else ""


class CommandProvider:
    """A provider that pipes the system text and the conversation to a command line and returns what it prints.

    ``command`` is split like a shell line; ``{model}`` in it is replaced by the model name. ``tokens_in`` and
    ``tokens_out`` are estimates (four characters a token) so a run's size shows in the results log; the vendor's own
    count, when the command can print it, is better and belongs in a provider of the caller's own.
    """

    def __init__(self, command: str, timeout: int = 300):
        if not command.strip():
            raise ValueError("no model command: set it (for example the environment variable the arm names) to a command "
                             "that reads a prompt on standard input and prints a reply")
        self.command = command
        self.timeout = timeout
        self.tokens_in = 0
        self.tokens_out = 0
        self.cost_usd = 0.0

    def answer(self, messages: List[Dict[str, str]], model: Optional[str] = None, system: Optional[str] = None) -> str:
        user = "\n\n".join(m["content"] for m in messages if m.get("role") == "user")
        prompt = (f"{system}\n\n---\n\n" if system else "") + user
        argv = [part.replace("{model}", model or "") for part in shlex.split(self.command)]
        done = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=self.timeout, check=False)
        if done.returncode != 0:
            raise RuntimeError(f"model command failed ({done.returncode}): {done.stderr.strip()[:200]}")
        self.tokens_in += len(prompt) // 4
        self.tokens_out += len(done.stdout) // 4
        return done.stdout.strip()
