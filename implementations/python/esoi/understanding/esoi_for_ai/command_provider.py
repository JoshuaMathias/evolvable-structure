"""A model provider that pipes the prompt to a command line and returns what it prints, so no model vendor is a dependency.

It has the ``answer(messages, model=None, system=None)`` method that ``build_judge`` and the model arms call.
"""
from __future__ import annotations

import shlex
import subprocess
from typing import Dict, List, Optional


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
