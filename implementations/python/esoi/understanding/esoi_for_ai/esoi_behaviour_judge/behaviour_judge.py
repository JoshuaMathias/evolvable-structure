"""The model judge of a behaviour case: the grading prompt, the parsed verdict, and ``build_judge`` over any provider.

The judge is a function ``judge(case, reply) -> (passed, reason)`` made from any provider with an
``answer(messages, model=None, system=None)`` method (``esoi.understanding.esoi_for_ai.command_provider.CommandProvider``
is one), so the library depends on no model vendor. It grades what a reply DOES against the case's expected behaviour and
failure mode, never against regexes. Nothing here calls a model unless a caller passes a provider.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Optional, Tuple

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
