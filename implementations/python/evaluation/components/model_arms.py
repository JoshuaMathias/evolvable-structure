"""Shared by the evaluation arms that call a model: the provider, the model names and the judge, all read from the
environment so no vendor, key or price is written into the repository. Nothing here runs unless a paid arm is run."""
import os

from esoi import behaviour

COMMAND_ENV = "ESOI_MODEL_COMMAND"
MODEL_ENV = "ESOI_MODEL"
JUDGE_MODEL_ENV = "ESOI_JUDGE_MODEL"


def provider(meter):
    """A command provider counted by ``meter``. The command reads a prompt on standard input and prints a reply."""
    command = os.environ.get(COMMAND_ENV, "")
    if not command.strip():
        raise ValueError(f"a paid arm needs {COMMAND_ENV}: a command that reads a prompt on standard input and prints a reply "
                         f"(optionally {MODEL_ENV} and {JUDGE_MODEL_ENV} to name the models); nothing was called")
    return meter.wrap(behaviour.CommandProvider(command))


def model():
    return os.environ.get(MODEL_ENV, "")


def judge_model():
    return os.environ.get(JUDGE_MODEL_ENV) or model()


def judge(meter):
    """``judge(case, reply)`` whose calls are counted by ``meter``."""
    return behaviour.build_judge(provider(meter), judge_model())
