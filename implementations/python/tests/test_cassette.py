"""The cassette: record and replay of wrapped model calls, with new and replayed usage kept apart."""
import csv
import importlib
import json

import pytest

from esoi.optimization.measurement_harness import cassette
from esoi.optimization.measurement_harness import component_folder
from esoi.optimization.measurement_harness import run_component
from esoi.optimization.measurement_harness import run_errors
from esoi import __main__ as cli
from esoi.optimization.measurement_harness.cassette import Cassette, CassetteMiss
from esoi.optimization.measurement_harness.call_meter import CallMeter
from esoi.optimization.measurement_harness.run_errors import OfflineViolation
from test_harness import git, make


class Provider:
    """Counts the real calls it makes and reports usage the way a provider does."""

    def __init__(self):
        self.real = 0
        self.tokens_in = self.tokens_out = 0
        self.cost_usd = 0.0

    def answer(self, messages, *, model, system=None, timeout=None):
        self.real += 1
        self.tokens_in += 10
        self.tokens_out += 4
        self.cost_usd += 0.5
        return f"{model}:{messages[-1]['content']}:{system}"


class Broken(Provider):
    def answer(self, messages, *, model, system=None):
        self.real += 1
        raise RuntimeError("provider down")


def wired(tmp_path, only=False, offline=False, provider=None):
    meter, provider = CallMeter(), provider or Provider()
    meter.cassette = Cassette(tmp_path / "cass", only=only)
    meter.offline = offline
    meter.wrap(provider, ("answer",))
    return meter, provider


ASK = [{"role": "user", "content": "hi"}]


def test_a_hit_returns_the_identical_text_without_calling_the_provider(tmp_path):
    meter, provider = wired(tmp_path)
    first = provider.answer(ASK, model="m", system="s")
    again = provider.answer(ASK, model="m", system="s")
    assert first == again and provider.real == 1   # the second call never reached the provider
    assert (meter.calls, meter.calls_replayed) == (1, 1)


def test_a_new_process_replays_from_the_file(tmp_path):
    wired(tmp_path)[1].answer(ASK, model="m")
    meter, provider = wired(tmp_path)   # a fresh meter and provider over the same folder
    assert provider.answer(ASK, model="m") == "m:hi:None" and provider.real == 0 and meter.calls == 0


def test_a_changed_prompt_model_or_system_misses_and_a_timeout_does_not(tmp_path):
    meter, provider = wired(tmp_path)
    provider.answer(ASK, model="m", system="s")
    provider.answer([{"role": "user", "content": "other"}], model="m", system="s")
    provider.answer(ASK, model="m2", system="s")
    provider.answer(ASK, model="m", system="s2")
    assert provider.real == 4 and meter.calls_replayed == 0
    provider.answer(ASK, model="m", system="s", timeout=5)   # does not change what the model says
    assert provider.real == 4 and meter.calls_replayed == 1


def test_usage_accounting_separates_new_and_replayed_calls(tmp_path):
    meter, provider = wired(tmp_path)
    provider.answer(ASK, model="m")
    provider.answer(ASK, model="m")
    provider.answer(ASK, model="m")
    assert (meter.tokens_in, meter.tokens_out, meter.cost_usd) == (10, 4, 0.5)   # the one real call
    assert (meter.calls_replayed, meter.replayed_tokens_in, meter.replayed_tokens_out, meter.replayed_cost_usd) == (2, 20, 8, 1.0)


def test_the_file_is_plain_jsonl_with_the_usage_and_no_request_text(tmp_path):
    wired(tmp_path)[1].answer([{"role": "user", "content": "SECRET-PROMPT"}], model="m", system="SECRET-SYSTEM")
    text = (tmp_path / "cass" / "calls.jsonl").read_text()
    entry = json.loads(text.strip())
    assert entry["usage"] == {"tokens_in": 10, "tokens_out": 4, "cost_usd": 0.5, "seconds": entry["usage"]["seconds"]}
    assert len(entry["key"]) == 64 and entry["response"] == "m:SECRET-PROMPT:SECRET-SYSTEM"
    assert "SECRET-SYSTEM" not in text.replace(entry["response"], "")   # only the response carries text, the request is a hash


def test_a_provider_error_is_not_recorded_and_the_next_call_tries_again(tmp_path):
    meter, provider = wired(tmp_path, provider=Broken())
    with pytest.raises(RuntimeError):
        provider.answer(ASK, model="m")
    assert not (tmp_path / "cass" / "calls.jsonl").exists()
    with pytest.raises(RuntimeError):
        provider.answer(ASK, model="m")
    assert provider.real == 2


def test_an_offline_hit_is_allowed_and_an_offline_miss_is_refused(tmp_path):
    wired(tmp_path)[1].answer(ASK, model="m")
    meter, provider = wired(tmp_path, offline=True)
    assert provider.answer(ASK, model="m") == "m:hi:None"   # no process starts for a replay
    with pytest.raises(OfflineViolation):
        provider.answer([{"role": "user", "content": "new"}], model="m")
    assert provider.real == 0 and meter.attempted == 1 and meter.calls == 0


def test_cassette_only_raises_on_a_miss_and_still_replays_a_hit(tmp_path):
    wired(tmp_path)[1].answer(ASK, model="m")
    meter, provider = wired(tmp_path, only=True)
    assert provider.answer(ASK, model="m") == "m:hi:None"
    with pytest.raises(CassetteMiss):
        provider.answer([{"role": "user", "content": "new"}], model="m")
    assert provider.real == 0


def test_stats_lists_entries_hits_misses_and_size(tmp_path, capsys):
    meter, provider = wired(tmp_path)
    provider.answer(ASK, model="m")
    provider.answer(ASK, model="m")
    found = cassette.stats(tmp_path / "cass")
    assert (found["entries"], found["hits"], found["misses"]) == (1, 1, 1) and found["bytes"] > 0 and found["stored_cost_usd"] == 0.5
    assert cassette.run_cli(["stats", str(tmp_path / "cass")]) == 0
    assert "1 entries" in capsys.readouterr().out
    assert cassette.run_cli(["stats"]) == 2


def test_an_argument_with_no_json_form_is_a_plain_uncached_call(tmp_path):
    meter, provider = wired(tmp_path)
    provider.answer(ASK, model="m", system=object().__class__)   # a class has no JSON form
    provider.answer(ASK, model="m", system=object().__class__)
    assert provider.real == 2 and not (tmp_path / "cass" / "calls.jsonl").exists()
    only, other = wired(tmp_path, only=True)
    with pytest.raises(CassetteMiss):
        other.answer(ASK, model="m", system=object().__class__)


def test_no_cassette_leaves_the_meter_unchanged(tmp_path):
    meter, provider = CallMeter(), Provider()
    meter.wrap(provider, ("answer",))
    provider.answer(ASK, model="m")
    provider.answer(ASK, model="m")
    assert provider.real == 2 and meter.calls_replayed == 0


LLM_ARM = ('PAID = True\n\n\ndef build(meter):\n    from pathlib import Path\n    import sys\n    provider = sys.modules["fake_provider"].make()\n'
           '    meter.wrap(provider, ("answer",))\n\n    def run(kind, args):\n        provider.answer([{"role": "user", "content": str(args["n"])}], model="m")\n'
           '        return {"n": args["n"]}\n    return run\n')


def test_a_run_records_replays_and_reports_the_replayed_cost_apart(tmp_path, monkeypatch):
    import sys
    import types
    fake = types.ModuleType("fake_provider")
    made = []
    fake.make = lambda: made.append(Provider()) or made[-1]
    monkeypatch.setitem(sys.modules, "fake_provider", fake)
    cfg = make(tmp_path, "comp_cass")
    (cfg.evaluation / "comp_cass" / "impls" / "llm.py").write_text(LLM_ARM)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    component_folder.prepare_path(cfg)
    score = importlib.import_module("comp_cass.score")
    cass = str(tmp_path / "cass")
    first, _ = run_component.run_component("comp_cass", score.score_case, ["--impl", "llm", "--max-calls", "10", "--cassette", cass], cfg, lambda t: None)
    real = sum(p.real for p in made)
    assert first["model_calls"] == real > 0
    again, rows = run_component.run_component("comp_cass", score.score_case, ["--impl", "llm", "--max-calls", "10", "--cassette", cass, "--fresh"], cfg, lambda t: None)
    assert sum(p.real for p in made) == real and again["model_calls"] == 0 and again["cli_reported_cost_usd"] == 0
    assert "replayed" in again["details"] and rows[0]["calls_replayed"] == 1
    only, _ = run_component.run_component("comp_cass", score.score_case, ["--impl", "llm", "--max-calls", "10", "--cassette", cass, "--cassette-only", "--fresh"], cfg, lambda t: None)
    assert only["passed"] == only["cases"]
    with pytest.raises(run_errors.RunError):
        run_component.run_component("comp_cass", score.score_case, ["--impl", "llm", "--cassette-only"], cfg, lambda t: None)


def test_the_configuration_can_turn_the_cassette_on_and_the_cli_prints_stats(tmp_path, capsys):
    cfg = make(tmp_path, "comp_cfg")
    assert run_component.cassette_folder(cfg, None) is None
    cfg.harness = {"cassette": "evaluation/cassettes"}
    assert run_component.cassette_folder(cfg, None) == cfg.root / "evaluation" / "cassettes"
    assert run_component.cassette_folder(cfg, "elsewhere").name == "elsewhere"
    assert "harness" in __import__("esoi.structure.intent_registry.config", fromlist=["KNOWN"]).KNOWN
