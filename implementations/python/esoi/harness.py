"""Run one implementation of a solution over that solution's cases, and record the result with its provenance.

A component is a folder under the evaluation directory with a ``score.py`` (``score_case(fn, case)``, optionally
``aggregate(rows)`` for a headline, recorded as the row's ``details``, and ``load_cases()`` when the cases live elsewhere), ``cases.json`` (or
``cases.csv``) and ``impls/<name>.py`` exposing ``build(meter) -> fn``. The harness never imports a solution by
name, so a new implementation is one new function; ``--impl module:build`` also accepts one that lives outside
the repository. ``esoi run <component> --impl <name>`` drives it:

  * ``CallMeter`` counts every model call a run makes, so cost is checked against the harness, not guessed;
    ``--max-calls`` aborts a run that exceeds its budget (``BudgetExceeded``).
  * ``--only`` runs named cases, ``--sample N`` runs N cases spread over the strata (the same cases every time;
    a smaller N is a prefix of a larger one, so a cheap first run is part of the bigger run).
  * ``--record`` appends the summary to the results log with ``git_sha`` (suffixed ``-dirty`` when the measured
    code has uncommitted changes) and ``cases_sha`` (a hash of the case files), the provenance the leaderboard
    and the check (rules S16, S20) rely on, and ``sample`` (``sample:N`` for ``--sample N``, ``only:ids`` for
    ``--only``, blank for the full set), so the leaderboard compares arms only on the same cases.
  * an implementation needs no ``impls/<name>.py`` wrapper when the code declares it (``@implementation`` in
    ``esoi.runtime``): the harness imports the module the records name, and calls the implementation with each case's
    ``args`` as keyword arguments (a ``score.py`` may define ``adapt(implementation, meter) -> fn`` to say otherwise).
    Wrapper files stay for baselines and reference arms, and for implementations that need the meter.
  * an arm that meters a deterministic stand-in for a model (it counts the calls the real model would make, with no
    tokens) declares ``SIMULATED = True``: its runs record model ``simulated`` and cost 0.0, it is never treated as paid,
    and the leaderboard compares it on calls.
  * ``esoi run --stale`` re-runs a stale arm on the sample its latest row used (``--full`` runs the whole set), and a
    rival on the selected arm's sample, so a re-record stays comparable.
"""
from __future__ import annotations

import argparse
import ast
import csv
import datetime
import functools
import importlib
import inspect
import io
import json
import os
import pkgutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import balance, circumstances, leaderboard, run_guards, run_log, staleness, variants
from .config import Config
from .assemble import check_name
from .leaderboard import cases_digest, is_partial

RESULT_COLUMNS = ["date", "component", "impl", "cases", "passed", "dev", "heldout", "model_calls",
                  "tokens_in", "tokens_out", "cost_usd", "seconds", "balanced", "git_sha", "cases_sha", "sample", "model", "details"]


class BudgetExceeded(RuntimeError):
    """The run made more model calls than its budget allows."""


class RunError(ValueError):
    """The run cannot start as asked (no such implementation, no case selected); the message says what to change."""


class OfflineViolation(RuntimeError):
    """An offline run tried to start a model command."""


MODEL_COMMANDS = ("claude", "codex", "gemini")   # the commands an offline run may not start
OFFLINE_ENV = "ESOI_OFFLINE"                     # set to 1 during an offline run, for a provider that wants to refuse by itself


class OfflineGuard:
    """Refuses to start a model command while an offline run is in progress. An arm that is not declared live (``PAID = True``, a
    ``paid_arms`` entry, or run with ``--max-calls``) must not call a model, whatever a provider's fallback finds on the machine:
    while the guard is on, ``subprocess.Popen`` raises ``OfflineViolation`` for a command named in ``MODEL_COMMANDS`` and the
    attempt is counted in ``meter.attempted`` (the row's details show it beside the metered calls), and ``ESOI_OFFLINE=1`` is set."""

    def __init__(self, meter: "CallMeter"):
        self.meter = meter
        self.real: Any = None
        self.before: Optional[str] = None

    def start(self) -> None:
        meter, real = self.meter, subprocess.Popen

        class Guarded(real):   # type: ignore[valid-type, misc]
            def __init__(self, args, *rest, **options):
                first = args if isinstance(args, (str, bytes)) else (list(args) or [""])[0]
                word = (os.fsdecode(first).split() or [""])[0]
                if os.path.basename(word) in MODEL_COMMANDS:
                    meter.attempted += 1
                    raise OfflineViolation(f"offline run refused to start {os.path.basename(word)}: the arm is not declared live "
                                           "(PAID = True, paid_arms, or --max-calls)")
                super().__init__(args, *rest, **options)

        self.real, self.before = real, os.environ.get(OFFLINE_ENV)
        subprocess.Popen = Guarded   # type: ignore[misc]
        os.environ[OFFLINE_ENV] = "1"

    def stop(self) -> None:
        if self.real is not None:
            subprocess.Popen = self.real   # type: ignore[misc]
            self.real = None
            if self.before is None:
                os.environ.pop(OFFLINE_ENV, None)
            else:
                os.environ[OFFLINE_ENV] = self.before


def declared_live(config: Config, component: str, impl: str, max_calls: Optional[int]) -> bool:
    """Whether a run may call a model: the arm declares ``PAID = True``, is listed in ``paid_arms``, or the run was given a call budget."""
    base = variants.base_of(impl)
    return max_calls is not None or f"{component}/{base}" in config.paid_arms or declares_paid(impl_path(config, component, base))


def as_number(value: Any) -> float:
    """A counter's value as a number: a plain number as is, an object that defines ``__float__`` (or a ``value`` attribute)
    through that, anything else (None, missing, unreadable) as 0."""
    for read in (lambda v: v if isinstance(v, (int, float)) else None, lambda v: float(v), lambda v: float(v.value)):
        try:
            got = read(value)
            if got is not None:
                return got
        except Exception:   # noqa: BLE001
            continue
    return 0


def read_counters(provider: Any) -> Tuple[float, float, float]:
    """The provider's ``tokens_in``, ``tokens_out`` and ``cost_usd`` as numbers; a missing or non-numeric one reads as 0."""
    out = []
    for name in ("tokens_in", "tokens_out", "cost_usd"):
        try:
            out.append(as_number(getattr(provider, name, 0)))
        except Exception:   # noqa: BLE001
            out.append(0)
    return out[0], out[1], out[2]


class CallMeter:
    """Counts model calls. ``wrap(provider)`` instruments the named methods in place."""

    def __init__(self, max_calls: Optional[int] = None):
        self.calls = 0
        self.max_calls = max_calls
        self.tokens_in = self.tokens_out = 0
        self.cost_usd = 0.0   # what a provider reports per call (informational on a subscription login)
        self.attempted = 0    # model commands an offline run tried to start and the guard refused (see OfflineGuard)
        self.model: Optional[str] = None   # set by an implementation that pins a model, for the record

    def record(self, n: int = 1) -> None:
        self.calls += n
        if self.max_calls is not None and self.calls > self.max_calls:
            raise BudgetExceeded(f"model-call budget {self.max_calls} exceeded")

    def wrap(self, provider: Any, methods: Tuple[str, ...] = ("plan", "answer")) -> Any:
        """Count calls to ``methods`` of ``provider``; token and cost counters, when the provider keeps them as
        ``tokens_in``, ``tokens_out`` and ``cost_usd`` attributes, are added up from their per-call change."""
        if getattr(provider, "meter_wrapped", False):
            return provider
        if inspect.isclass(provider):
            raise TypeError(f"CallMeter.wrap needs a provider instance, got the class {provider.__name__}: its methods would be "
                            "called unbound (self missing) and its counters are class descriptors, not numbers")
        for name in methods:
            original = getattr(provider, name, None)
            if original is None:
                continue

            def make(fn: Callable) -> Callable:
                @functools.wraps(fn)   # keeps the signature: callers may inspect it for optional kwargs
                def counted(*args, **kwargs):
                    self.record()
                    before = read_counters(provider)
                    try:
                        return fn(*args, **kwargs)
                    finally:
                        try:
                            after = read_counters(provider)
                            self.tokens_in += int(after[0] - before[0])
                            self.tokens_out += int(after[1] - before[1])
                            self.cost_usd += after[2] - before[2]
                        except Exception:   # noqa: BLE001, metering must never change what the provider returns or raises
                            pass
                return counted
            setattr(provider, name, make(original))
        provider.meter_wrapped = True
        return provider


def prepare_path(config: Config) -> None:
    """Make the repository and the evaluation folder importable (score and impl modules import each other). A component module
    already imported from another project's folder (a process that runs more than one repository) is dropped first, or this
    project's ``<component>.score`` and ``.impls`` would resolve to the other project's files."""
    evaluation = config.evaluation.resolve() if config.evaluation.is_dir() else None
    for folder in (sorted(p.name for p in evaluation.iterdir() if p.is_dir() and (p / "score.py").exists()) if evaluation else []):
        loaded = sys.modules.get(folder)
        where = next(iter(getattr(loaded, "__path__", None) or []), "") if loaded is not None else ""
        if where and Path(where).resolve().parent != evaluation:
            for name in [m for m in sys.modules if m == folder or m.startswith(folder + ".")]:
                sys.modules.pop(name, None)
    for entry in (str(config.evaluation), str(config.root), *(str(config.root / p) for p in config.python_path)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def discover_components(config: Config) -> List[str]:
    """A component is any folder under the evaluation directory with a ``score.py``: adding one needs no edit here."""
    if not config.evaluation.is_dir():
        return []
    return sorted(p.name for p in config.evaluation.iterdir() if (p / "score.py").is_file())


SIMULATED_MODEL = "simulated"   # the model recorded for an arm that declares SIMULATED = True


def declared_build(config: Config, component: str, name: str) -> Optional[Callable]:
    """``build(meter)`` for an implementation the code declares (``esoi.runtime``) for the solution this component
    measures, or None when there is none of that name. Nothing is imported unless a solution measured by the component
    lists the name."""
    from . import runtime
    from .registry import harness_arms, load
    found = {}
    for row in load(config).solutions:
        if any(comp == component for comp, _ in harness_arms(config, row.get("metric_command", ""))):
            try:
                found.update(runtime.load_declared(config, row["solution_id"]))
            except runtime.SelectionError:
                continue
    target = found.get(name.strip().lower())
    if target is None:
        return None
    score = importlib.import_module(f"{component}.score")

    def build(meter: CallMeter, **params: Any) -> Callable:
        bound = functools.partial(check_parameters(target, params, name), **params) if params else target   # esoi.variants
        if hasattr(score, "adapt"):
            return score.adapt(bound, meter)
        return lambda kind, args: bound(**args)
    return build


def check_parameters(fn: Callable, params: Dict[str, Any], name: str) -> Callable:
    """``fn``, or ``RunError`` when it takes none of a variant's parameters by that name: an unknown key fails the arm once,
    loudly, instead of failing every case into a 0/N row."""
    try:
        accepted = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn
    if not any(p.kind is p.VAR_KEYWORD for p in accepted.values()):
        unknown = sorted(set(params) - set(accepted))
        if unknown:
            raise RunError(f"{name} takes no parameter {', '.join(unknown)} (it takes: {', '.join(accepted) or 'none'})")
    return fn


def load_impl(spec: str, component: str, config: Optional[Config] = None) -> Callable:
    """``--impl name`` -> ``<component>/impls/name.py``'s ``build``, else the implementation of that name the code
    declares (needs ``config``); ``module:function`` is also accepted. A variant (``name@key=value``, see ``esoi.variants``)
    resolves ``name`` and passes the parameters to its ``build(meter, **params)``."""
    if ":" in spec:
        module, _, attr = spec.partition(":")
        return getattr(importlib.import_module(module), attr)
    spec, params = variants.split(spec)
    if params:
        build = load_impl(spec, component, config)
        return lambda meter: check_parameters(build, params, spec)(meter, **params)
    try:
        return importlib.import_module(f"{component}.impls.{spec}").build
    except ModuleNotFoundError as exc:
        if exc.name not in (f"{component}.impls.{spec}", f"{component}.impls"):
            raise   # the implementation exists but one of its own imports is missing: that is the finding
        declared = declared_build(config, component, spec) if config is not None else None
        if declared is not None:
            return declared
        try:
            known = sorted(m.name for m in pkgutil.iter_modules(importlib.import_module(f"{component}.impls").__path__))
        except ModuleNotFoundError:
            known = []
        raise RunError(f"{component} has no implementation {spec!r}; known: {', '.join(known) or 'none'} (an implementation "
                       "declared with @implementation is found through the records: `esoi records sync` writes them)") from exc


def stratified_sample(cases: List[dict], n: int, seed: int = 0) -> List[dict]:
    """``n`` cases spread over the strata (``stratum``, else ``dataset``, else ``area``), the same cases every
    time for one seed. A smaller ``n`` is a prefix of a larger one."""
    import random
    rng = random.Random(seed)
    groups: Dict[str, List[dict]] = {}
    for case in sorted(cases, key=lambda c: str(c["id"])):
        groups.setdefault(case.get("stratum") or case.get("dataset") or case.get("area") or "", []).append(case)
    for group in groups.values():
        rng.shuffle(group)
    picked: List[dict] = []
    while len(picked) < n and any(groups.values()):
        for name in sorted(groups):
            if groups[name] and len(picked) < n:
                picked.append(groups[name].pop(0))
    return sorted(picked, key=lambda c: str(c["id"]))


def sample_label(args: argparse.Namespace, cases: List[dict], whole: int) -> str:
    """The ``sample`` cell of a run: blank for the full set, ``only:ids`` for ``--only``, else ``sample:N``."""
    if len(cases) == whole:
        return ""
    if args.only:
        return "only:" + ",".join(str(c["id"]) for c in cases)
    return f"sample:{args.sample}"


def sample_label_args(row: Optional[Dict[str, str]]) -> List[str]:
    """The ``esoi run`` flags a row's ``sample`` label names (``only:`` or ``sample:``), read from the label alone, else ``[]``.
    It imports nothing from the repository's evaluation, so a reader that must not run its code can use it."""
    label = ((row or {}).get("sample") or "").strip()
    if label.startswith("only:"):
        return ["--only", label[len("only:"):]]
    if label.startswith("sample:"):
        return ["--sample", label[len("sample:"):]]
    return []


def sample_args(config: Config, component: str, row: Optional[Dict[str, str]]) -> List[str]:
    """The ``esoi run`` flags that reproduce the sample a recorded row was scored on (``[]`` for the full set). A row
    recorded before the ``sample`` column that scored fewer cases than the set has is read as ``--sample`` of that size,
    which is what ``--sample`` recorded (stratified_sample is deterministic and a smaller N is a prefix of a larger). That
    reading holds only while the case file is unchanged; on other cases the old count says nothing, so the full set runs."""
    if not row:
        return []
    if labelled := sample_label_args(row):
        return labelled
    if (row.get("cases_sha") or "") != cases_digest(component, config.evaluation):
        return []   # a legacy count on other cases says nothing about a sample: the full set
    try:
        count = int(float(row.get("cases") or 0))
    except ValueError:
        return []
    return ["--sample", str(count)] if 0 < count < len(load_cases(component, config)) else []


def load_cases(component: str, config: Config) -> List[dict]:
    """The component's cases: the ``load_cases()`` of its score module when it has one (a dataset folder another
    harness also reads), else ``cases.json``, or ``cases.csv`` when the dataset is reviewed as a sheet (a
    ``heldout`` cell of ``yes`` marks a held-out case)."""
    prepare_path(config)
    score = importlib.import_module(f"{component}.score")
    if hasattr(score, "load_cases"):
        return score.load_cases()
    folder = config.evaluation / component
    if (folder / "cases.json").exists():
        return json.loads((folder / "cases.json").read_text(encoding="utf-8"))
    with (folder / "cases.csv").open(newline="", encoding="utf-8") as fh:
        cases = list(csv.DictReader(fh))
    for case in cases:
        case["heldout"] = (case.get("heldout") or "").strip().lower() == "yes"
    return cases


def git(config: Config, *args: str) -> str:
    return git_at(config.root, *args)


def git_at(folder: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def is_external(config: Config, entry: str) -> bool:
    """Whether a ``code_paths`` entry points outside this repository (``../sibling/pkg``): it is diffed in its own
    repository's git."""
    return not (config.root / entry).resolve().is_relative_to(config.root)


def own_code_paths(config: Config) -> List[str]:
    return [p for p in config.code_paths if not is_external(config, p)]


def external_code_paths(config: Config) -> List[Tuple[str, Path, str]]:
    """``(entry, repository folder, path inside it)`` for each external ``code_paths`` entry that exists and sits in a
    git checkout; one that is not there (a sibling not checked out in CI) is left out, as a commit that cannot be
    looked up is for the repository's own code."""
    found = []
    for entry in config.code_paths:
        if not is_external(config, entry):
            continue
        full = (config.root / entry).resolve()
        folder = full if full.is_dir() else full.parent
        top = git_at(folder, "rev-parse", "--show-toplevel") if folder.is_dir() else ""
        if top:
            found.append((entry, Path(top), str(full.relative_to(Path(top).resolve())) or "."))
    return found


def code_shas(config: Config) -> str:
    """The recorded commit of each external code path, ``entry@sha`` joined by ``;`` (``-dirty`` when that path has
    uncommitted changes): the ``code_shas`` cell of a results row. Blank when the repository has none."""
    parts = []
    for entry, repo, inside in external_code_paths(config):
        sha = git_at(repo, "rev-parse", "--short", "HEAD")
        if sha and git_at(repo, "status", "--porcelain", "--untracked-files=no", "--", inside):
            sha += "-dirty"
        if sha:
            parts.append(f"{entry}@{sha}")
    return ";".join(parts)


def parse_code_shas(cell: str) -> Dict[str, str]:
    return {entry: sha for entry, _, sha in (part.rpartition("@") for part in (cell or "").split(";") if "@" in part)}


def current_sha(config: Config, component: str = "", impl: str = "") -> str:
    """The short commit, suffixed ``-dirty`` when the measured code has uncommitted changes (the results log itself is not the
    code under test). With a component and arm, only uncommitted changes to what that arm measures under the repository's
    staleness rule count (``esoi.staleness``)."""
    sha = git(config, "rev-parse", "--short", "HEAD")
    if not sha:
        return sha
    if component and impl and staleness.rule_for(config) != "repo_wide":
        return sha + ("-dirty" if staleness.dirty_counts(config, component, impl) else "")
    if git(config, "status", "--porcelain", "--untracked-files=no", "--", *own_code_paths(config),
           config.evaluation_dir, f":(exclude){config.results}", f":(exclude){config.per_case}", f":(exclude){config.runs_log}"):
        sha += "-dirty"
    return sha


def changed_since(config: Config, sha: str) -> Optional[List[str]]:
    """Tracked files of the measured code (and the evaluation folder, except the results log) that differ from the
    working tree since the commit a result was recorded at; ``None`` when that commit is not known here."""
    base = sha.removesuffix("-dirty")
    done = subprocess.run(["git", "diff", "--name-only", base, "--", *own_code_paths(config), config.evaluation_dir,
                           f":(exclude){config.results}", f":(exclude){config.per_case}", f":(exclude){config.runs_log}"], cwd=config.root, capture_output=True, text=True)
    return done.stdout.split() if done.returncode == 0 else None


def code_changed_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why the code a row measured changed since its commit, naming the changed file and who owns it, or an empty string. The
    files that count are the ones the staleness rule says the arm measures (``esoi.staleness``); under ``repo_wide`` any file
    of the measured folders."""
    sha = row["git_sha"]
    if staleness.rule_for(config) == "repo_wide":
        changed = changed_since(config, sha)
        return f"the measured code changed since its commit {sha} ({changed[0]}{' and others' if len(changed) > 1 else ''})" if changed else ""
    found = staleness.explain(config, component, row.get("impl", ""), sha)
    if not found or not found["counts"]:
        return ""
    counts, rule, note = found["counts"], found["rule"][0], found["rule"][1]
    more = f" and {len(counts) - 1} more" if len(counts) > 1 else ""
    fallback = f"; {rule} rule, {note}" if note else f"; {rule} rule"
    return f"the measured code changed since its commit {sha} ({counts[0]}{more}{fallback})"


def external_reason(config: Config, row: Dict[str, str]) -> str:
    """Why the code a row measured in other repositories (``code_paths`` outside this one) no longer counts."""
    recorded = parse_code_shas(row.get("code_shas", ""))
    for entry, repo, inside in external_code_paths(config):
        sha = recorded.get(entry)
        if not sha:
            return f"its latest row records no commit for the code path {entry} in another repository (re-run with --record)"
        if sha.endswith("-dirty"):
            return f"its latest row was recorded on uncommitted code in {entry}"
        done = subprocess.run(["git", "diff", "--name-only", sha, "--", inside], cwd=repo, capture_output=True, text=True)
        if done.returncode == 0 and done.stdout.split():
            changed = done.stdout.split()
            return f"the measured code in {entry} changed since its commit {sha} ({changed[0]}{' and others' if len(changed) > 1 else ''})"
    return ""


def defect_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a recorded row is malformed, as opposed to stale: it names no commit (it cannot say what it measured), or
    ``circumstances.csv`` cannot be read. A defect is a problem for ``esoi check``; every other reason in ``stale_reason``
    (the cases, the code, the circumstances or the tree changed since the run) is a fact about time and only informs."""
    if not row.get("git_sha", "").strip():
        return "its latest row has no git_sha"
    try:
        circumstances.for_component(config, component)
    except ValueError as exc:
        return f"circumstances.csv cannot be read: {exc}"
    return ""


def stale_reason(config: Config, component: str, row: Optional[Dict[str, str]], strict: bool = True) -> str:
    """Why a recorded result no longer counts, or an empty string when it is current. A result is stale when it is missing,
    has no commit, was run on other cases than the ones now on disk, and (strict) was run on uncommitted code or the
    measured code, in this repository or in another one named by ``code_paths``, has changed since its commit."""
    if row is None:
        return "it has no recorded result"
    if why := defect_reason(config, component, row):
        return why
    now = cases_digest(component, config.evaluation)
    if row.get("cases_sha", "") != now:
        return f"its latest row was recorded on other cases (cases_sha {row.get('cases_sha') or 'blank'}, now {now})"
    if why := circumstances_stale(config, component, row):
        return why
    if strict and row["git_sha"].endswith("-dirty"):
        return "its latest row was recorded on uncommitted code"
    if strict and (why := code_changed_reason(config, component, row)):
        return why
    return external_reason(config, row) if strict else ""


def price_for(config: Config, model: Optional[str]) -> Optional[Dict[str, float]]:
    """The ``prices`` entry for a model: the exact name, else the longest listed name that is a prefix of it (so a
    dated model id finds its family's price)."""
    if not model or not config.prices:
        return None
    if model in config.prices:
        return config.prices[model]
    listed = [name for name in config.prices if model.startswith(name)]
    return config.prices[max(listed, key=len)] if listed else None


def run_cost(config: Config, summary: Dict[str, Any], model: Optional[str]) -> Any:
    """The dollar cost to record for a run: what the provider reported when that is more than zero, else tokens times
    the configured price of the model, else 0.0 for a run that called no model, else ``""`` (unknown, never a
    zero that reads as free). Prices are USD per million tokens, ``prices = { "model" = { input = 3.0, output = 15.0 } }``."""
    reported = float(summary.get("cli_reported_cost_usd", summary.get("cost_usd", 0.0)) or 0.0)
    if model == SIMULATED_MODEL:
        return 0.0   # a deterministic stand-in: its calls are counted, but nothing is spent
    if reported > 0:
        return reported
    if not summary.get("model_calls"):
        return 0.0
    price = price_for(config, model)
    if price is None or not (summary.get("tokens_in") or summary.get("tokens_out")):
        return ""
    return round((float(summary.get("tokens_in") or 0) * float(price.get("input", 0))
                  + float(summary.get("tokens_out") or 0) * float(price.get("output", 0))) / 1_000_000, 6)


def record_result(summary: Dict[str, Any], config: Config, date: Optional[str] = None,
                  path: Optional[Path] = None, model_env: Optional[str] = None) -> Dict[str, Any]:
    """Append one run's summary to the results log, the source of truth for metrics. Returns the row written."""
    comp = summary.get("component", "")
    model = summary.get("model") or (model_env if summary.get("model_calls") and model_env else
                                     ("unknown" if summary.get("model_calls") else "none"))
    row = dict(summary, date=date or datetime.date.today().isoformat(),
               cost_usd=run_cost(config, summary, model),
               git_sha=current_sha(config, summary.get("component", ""), summary.get("impl", "")), model=model, cases_sha=cases_digest(comp, config.evaluation))
    target = Path(path) if path else config.results_path
    wanted = bool(external_code_paths(config))
    if wanted:
        row["code_shas"] = code_shas(config)
    append_row(target, row, wanted)
    return row


def append_row(target: Path, row: Dict[str, Any], with_code_shas: bool) -> None:
    """Append ``row`` to the results log. The log gains a trailing ``code_shas`` column the first time a repository with
    code in another repository records (older rows keep it blank)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    header: List[str] = []
    old_rows: List[Dict[str, str]] = []
    if target.exists():
        with open(target, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header, old_rows = list(reader.fieldnames or []), list(reader)
    wanted = RESULT_COLUMNS + (["code_shas"] if with_code_shas else [])
    columns = header + [c for c in wanted if c not in header] if header else wanted
    rewrite = not header or columns != header
    with open(target, "w" if rewrite else "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        if rewrite:
            writer.writeheader()
            writer.writerows(old_rows)
        writer.writerow(row)


def check_guards(config: Config, component: str, impl: str, sample: str, args: argparse.Namespace,
                 say: Callable[[str], None]) -> List[str]:
    """Refuse (``RunError``) a run that cannot inform a decision, unless it says why it runs anyway; the notes to record in
    ``details`` are returned. The ceiling guard and the public-first guard are in ``esoi.run_guards``."""
    try:
        forced = run_guards.force_reason(args.force)
        differs = run_guards.check_differs(args.differs) if args.differs is not None else ""
        latest = leaderboard.latest_results(config.results_path).get(component, {}).get(impl)
        paid = paid_reason(config, component, variants.base_of(impl), latest)
        capped = run_guards.ceiling_reason(config, component, impl, sample, paid, stale_reason)
        public, lines = run_guards.public_reason(config, component, impl)
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    notes: List[str] = []
    unsolved = "" if getattr(args, "failed", False) or sample else run_guards.unsolved_reason(config, component, impl)
    if unsolved and not forced:
        raise RunError(f"{impl} is not run on the whole set: {unsolved}")
    if unsolved:
        notes.append(f"forced past unsolved failures: {forced}")
    for line in lines:
        say(f"public result: {line}")
    if capped and not forced:
        raise RunError(f"{impl} is not run: {capped}")
    if capped:
        notes.append(f"forced past ceiling: {forced}")
    if public and not (differs or forced):
        raise RunError(f"{impl} is not run: {public}")
    if public and differs:
        notes.append(f"differs from public: {differs}")
    elif public:
        notes.append(f"forced past public result: {forced}")
    return notes


def run_component(component: str, scorer: Callable, argv: List[str], config: Config,
                  say: Callable[[str], None] = print, guards: bool = True) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Drive one implementation over a component's cases; print each case; optionally record. Returns (summary, rows)."""
    ap = argparse.ArgumentParser(prog=f"esoi run {component}", description=f"Evaluate the {component} component on its own.")
    ap.add_argument("--impl", required=True, help="implementation name (impls/<name>.py) or module:build")
    ap.add_argument("--only", default=None, help="comma-separated case ids")
    ap.add_argument("--failed", action="store_true",
                    help="run only the cases whose latest run (of this implementation, on these cases) failed; cannot be combined with --only or --sample")
    ap.add_argument("--keep-going", action="store_true",
                    help="run past a failing case; without it an unrecorded run stops at the first failure so the implementation can be improved at once")
    ap.add_argument("--fresh", action="store_true",
                    help="run every case, including ones already run for this implementation version (a --sample or whole run reuses those)")
    ap.add_argument("--sample", type=int, default=None, metavar="N",
                    help="run N cases spread over the strata (same cases every time; N=3 is a prefix of N=10)")
    ap.add_argument("--max-calls", type=int, default=None, help="abort when model calls exceed this")
    ap.add_argument("--out", default=None, help="results json path (default: a temporary folder)")
    ap.add_argument("--record", action="store_true", help="append the summary to the results log")
    ap.add_argument("--force", default=None, metavar="REASON",
                    help="run although a guard refuses (a perfect arm already caps this one, or a public result exists); the reason is recorded in details")
    ap.add_argument("--differs", default=None, metavar="WHAT",
                    help='run although a public result exists, saying what differs: "harness: ...", "prompt: ...", "settings", "corpus" or "metric"')
    args = ap.parse_args(argv)
    cases = load_cases(component, config)
    whole = len(cases)
    try:
        circs = circumstances.for_component(config, component)   # an unreadable circumstance fails here, before any model call
        circumstances.check_fields(circs, cases)
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    impl = args.impl if ":" in args.impl else variants.canonical(args.impl)   # one spelling of a variant in every record
    runs_path, cases_sha = config.root / config.runs_log, cases_digest(component, config.evaluation)
    if args.failed:
        if args.only or args.sample is not None:
            raise RunError("--failed already names the cases to run (the ones that failed last); drop --only or --sample")
        failing = run_log.failed_cases(runs_path, component, impl, cases_sha)
        if not failing:
            raise RunError(f"no failing case is logged for {impl} on these cases, so there is nothing to rerun "
                           f"(the log is {config.runs_log}); run it without --failed")
        args.only = ",".join(failing)
    elif guards and not (args.only or args.sample is not None or args.record or args.force is not None):
        unsolved = run_guards.unsolved_cases(config, component, impl)
        if unsolved:   # the failing cases are rerun by themselves; the whole set waits until they pass
            say(f"{len(unsolved)} case(s) failed in the latest run and have not passed since, so only those run ({', '.join(unsolved[:8])}"
                f"{' ...' if len(unsolved) > 8 else ''}); pass --force \"reason\" to run the whole set")
            args.only = ",".join(unsolved)
    if args.only:
        keep = {c.strip() for c in args.only.split(",")}
        cases = [c for c in cases if c["id"] in keep]
        if not cases:
            raise RunError(f"--only {args.only!r} matches no case of {component}")
    if args.sample is not None:
        if args.sample < 1:
            raise RunError("--sample needs a number of cases of at least 1")
        cases = stratified_sample(cases, args.sample)
    sample = sample_label(args, cases, whole)
    budget = args.max_calls if args.max_calls is not None else "none"
    say(f"{component}: {len(cases)} case(s), impl {args.impl}, model-call budget {budget}: "
        f"{', '.join(str(c['id']) for c in cases[:12])}{' ...' if len(cases) > 12 else ''}")
    notes = check_guards(config, component, impl, sample, args, say) if guards else []
    meter = CallMeter(args.max_calls)
    guard = None if declared_live(config, component, impl, args.max_calls) else OfflineGuard(meter)
    fn = load_impl(impl, component, config)(meter)
    git_sha = current_sha(config, component, impl)
    reuse = {} if (args.fresh or args.only) else run_log.reusable(runs_path, component, impl, cases_sha, git_sha)
    stop_at_fail = not (args.keep_going or args.record)   # a recorded run is a whole measurement; a development run is for fixing
    log = run_log.RunLog(runs_path, dict(component=component, impl=impl, cases_sha=cases_sha, git_sha=git_sha, sample=sample,
                                         recorded="yes" if args.record else "no"))
    log.begin()
    rows: List[Dict[str, Any]] = []
    reused = dict(calls=0, tokens_in=0, tokens_out=0, cost=0.0, seconds=0.0, cases=0)
    stopped = ""
    started = time.time()
    if guard:
        guard.start()
    try:
        for case in cases:
            before, t0, in0, out0, cost0 = meter.calls, time.time(), meter.tokens_in, meter.tokens_out, meter.cost_usd
            if str(case["id"]) in reuse:
                row = dict(reuse[str(case["id"])])
                spent = float(row.pop("cost", 0) or 0)
                for name, key in (("calls", "calls"), ("tokens_in", "tokens_in"), ("tokens_out", "tokens_out"), ("seconds", "seconds")):
                    reused[name] += row.get(key) or 0
                reused["cost"] += spent
                reused["cases"] += 1
                rows.append(row)
                log.case(row, spent, reused=True)
                say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} reused from an earlier run of this implementation version")
                continue
            try:
                row = scorer(fn, case)
            except BudgetExceeded:
                raise
            except Exception as exc:
                row = dict(ok=False, note=f"{type(exc).__name__}: {exc}")
            row.update(id=case["id"], area=case.get("area"), calls=meter.calls - before, seconds=round(time.time() - t0, 1),
                       tokens_in=meter.tokens_in - in0, tokens_out=meter.tokens_out - out0)
            rows.append(row)
            log.case(row, meter.cost_usd - cost0)
            say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} calls={row['calls']} {row.get('got', '')} | {row.get('note', '')}")
            if stop_at_fail and not row["ok"]:
                stopped = f"stopped at the first failing case, {row['id']}"
                break
    except BaseException as exc:   # Ctrl-C, a spent call budget or a crash: what was scored stays in the log
        log.end(f"stopped: {type(exc).__name__}")
        raise
    finally:
        if guard:
            guard.stop()
    log.end("done" if not stopped else stopped.replace("stopped at", "stopped: at"))
    cases = cases[:len(rows)]
    passed = sum(bool(r["ok"]) for r in rows)
    held = [r for r, c in zip(rows, cases) if c.get("heldout")]
    summary = dict(component=component, impl=impl, cases=len(rows), passed=passed,
                   dev=f"{sum(bool(r['ok']) for r in rows if r not in held)}/{len(rows) - len(held)}",
                   heldout=f"{sum(bool(r['ok']) for r in held)}/{len(held)}",
                   model_calls=meter.calls + reused["calls"], tokens_in=meter.tokens_in + reused["tokens_in"],
                   tokens_out=meter.tokens_out + reused["tokens_out"],
                   cli_reported_cost_usd=round(meter.cost_usd + reused["cost"], 4),
                   seconds=round(time.time() - started + reused["seconds"], 1),
                   model=SIMULATED_MODEL if declares_simulated(impl_path(config, component, variants.base_of(impl))) else meter.model,
                   sample=sample)
    cost = run_cost(config, summary, summary["model"])
    summary.update(balance.balanced(passed, len(rows), cost, summary["seconds"], config.balance.get(component)))
    say(f"\n{component} / {args.impl}: {passed}/{len(rows)} passed (dev {summary['dev']}, held-out "
        f"{summary['heldout']}), {summary['model_calls']} model calls, {summary['tokens_in']} in / {summary['tokens_out']} out tokens, "
        f"cost {'$' + str(cost) if cost != '' else 'unknown (no price for the model in `prices`)'}, {summary['seconds']}s")
    if "balanced" in summary:
        say(f"balanced score {summary['balanced']} = accuracy {summary['accuracy']}, ${summary['cost_per_case']}/case, "
            f"{summary['seconds_per_case']}s/case (weights and budgets: [balance.{component}] in the configuration)")
    score = importlib.import_module(f"{component}.score")
    if hasattr(score, "aggregate"):
        headline = score.aggregate(rows)
        say(f"{component}: {headline}")
        summary["details"] = details_text(headline)
    if hasattr(score, "disqualify") and (barred := score.disqualify(rows)):   # a hard fail: the run records a zero balanced score, so it cannot rank
        summary["balanced"] = 0.0
        summary["details"] = f"DISQUALIFIED {barred}; {summary.get('details', '')}".strip("; ")
        say(f"{component}: DISQUALIFIED, {barred}")
    if meter.attempted:
        notes.append(f"offline guard refused {meter.attempted} attempted model call(s) (metered {meter.calls}); declare the arm live (PAID = True) to call a model")
    if reused["cases"]:
        notes.append(f"reused {reused['cases']} case(s) already run for this implementation version")
    if notes:
        summary["details"] = run_guards.note_details(summary.get("details", ""), notes)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(summary=summary, rows=rows), indent=1), encoding="utf-8")
        say(f"results: {out}")
    if stopped:
        say(f"{stopped}: fix it and rerun just the failing case(s) with --failed; every case run is saved in {config.runs_log} "
            "(this run is not recorded; add --keep-going to run past failures)")
    if args.record:
        record_result(summary, config)
        say(f"recorded in {config.results}")
        if not sample.startswith("only:"):
            for part in record_slices(config, component, circs, summary, cases, rows):
                say(f"recorded {part['sample']}: {part['passed']}/{part['cases']} (derived from this run)")
    return summary, rows


def details_text(headline: Any, limit: int = 300) -> str:
    """The recorded ``details`` cell for a component's ``aggregate(rows)``: a mapping becomes ``key=value`` pairs joined by
    ``; `` (secondary numbers such as nDCG next to the pass count), anything else its text; clipped to ``limit``."""
    if isinstance(headline, dict):
        text = "; ".join(f"{key}={value}" for key, value in headline.items())
    else:
        text = "" if headline is None else str(headline)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


PER_CASE_COLUMNS = ["component", "impl", "cases_sha", "circumstances_sha", "sample", "case_id", "heldout", "ok", "calls",
                    "tokens_in", "tokens_out", "seconds", "circumstances", "score"]
PER_CASE_KEY = leaderboard.PER_CASE_KEY


def read_per_case(config: Config, every: bool = False) -> List[Dict[str, str]]:
    """The per-case log, the newest row of each (arm, cases, sample, case) or, with ``every``, every row in file order
    (``leaderboard.per_case_rows``, which the leaderboard's paired test also reads)."""
    return leaderboard.per_case_rows(config, every)


def upgrade_per_case_header(path: Path) -> None:
    """Rewrite a per-case log written by an older version (a header without a column added since, such as ``score``) under the
    current header, in one move, so a new row never lands under a header that lacks its column. Existing values are kept and a
    column the old file lacked is left empty. A file already on the current header is not touched."""
    if not path.is_file() or path.stat().st_size == 0:
        return
    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh), [])
        if header == PER_CASE_COLUMNS:
            return
        fh.seek(0)
        rows = [r for r in csv.DictReader(fh) if r.get("component") != "component"]
    unknown = [name for name in header if name not in PER_CASE_COLUMNS]
    if unknown:
        raise RunError(f"{path} has column(s) this version does not know ({', '.join(unknown)}); remedy: update esoi")
    temporary = path.with_suffix(path.suffix + ".upgrade")
    with open(temporary, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, PER_CASE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({name: row.get(name, "") or "" for name in PER_CASE_COLUMNS} for row in rows)
    os.replace(temporary, path)


def write_per_case(config: Config, new: List[Dict[str, str]]) -> None:
    """Add rows to the per-case log without losing another recorder's: one append of the whole batch (``O_APPEND``), then,
    when the arm had rows of its own from older cases or an earlier run of the same sample, a compaction written to a
    temporary file and moved over the log in one step. A row lost to a compaction that overlapped an append is re-derived:
    the arm is stale (``circumstances_stale``) until its rows are back."""
    path = config.root / config.per_case
    path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_per_case_header(path)
    out = io.StringIO()
    writer = csv.DictWriter(out, PER_CASE_COLUMNS, lineterminator="\n")
    if not path.is_file() or path.stat().st_size == 0:
        writer.writeheader()
    writer.writerows(new)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, out.getvalue().encode("utf-8"))
    finally:
        os.close(fd)
    arm = {(r["component"], r["impl"]) for r in new}
    keep = [r for r in read_per_case(config) if (r["component"], r["impl"]) not in arm or r["cases_sha"] == new[0]["cases_sha"]]
    if len(keep) != len(read_per_case(config, every=True)):   # superseded rows, rows of older cases or a repeated header
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        with open(temporary, "w", newline="", encoding="utf-8") as fh:
            compacted = csv.DictWriter(fh, PER_CASE_COLUMNS, lineterminator="\n")
            compacted.writeheader()
            compacted.writerows(keep)
        os.replace(temporary, path)


def case_balanced_scores(config: Config, component: str, summary: Dict[str, Any], rows: List[Dict[str, Any]]) -> List[float]:
    """The balanced score of each case of a run (``balance.case_scores``): the run's cost shared out by tokens (by model calls, else
    equally, when no tokens were counted). Empty when the component sets no balance or the price is unknown, as for the run's own
    balanced score."""
    cost = run_cost(config, summary, summary.get("model"))
    table = config.balance.get(component)
    if table is None or cost == "" or cost is None or not rows:
        return []
    for field_name in ("tokens_in", "calls"):
        weights = [float(r.get(field_name) or 0) + (float(r.get("tokens_out") or 0) if field_name == "tokens_in" else 0) for r in rows]
        if sum(weights) > 0:
            break
    else:
        weights = [1.0] * len(rows)
    share = [float(cost) * w / sum(weights) for w in weights]
    return balance.case_scores([bool(r["ok"]) for r in rows], share, [float(r["seconds"]) for r in rows], table)


def record_slices(config: Config, component: str, circs: List[circumstances.Circumstance], summary: Dict[str, Any],
                  cases: List[dict], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The derived rows of a recorded run, one per circumstance it satisfies and has cases in (``slice:<id>``, or
    ``sample:N/slice:<id>``), appended to the results log, and the run's per-case log (written for every recorded run, because
    the leaderboard's paired test needs each case's outcome; a component with no circumstances gets no derived rows). A slice costs no model call: it is a sum over the cases the run already scored."""
    key = dict(component=component, impl=summary["impl"], cases_sha=cases_digest(component, config.evaluation),
               circumstances_sha=circumstances.digest(circs) if circs else "", sample=summary["sample"])
    scores = case_balanced_scores(config, component, summary, rows)
    write_per_case(config, [dict(key, case_id=str(c["id"]), heldout="yes" if c.get("heldout") else "", ok="1" if r["ok"] else "0",
                                 calls=r["calls"], tokens_in=r["tokens_in"], tokens_out=r["tokens_out"], seconds=r["seconds"],
                                 circumstances=";".join(circumstances.case_circumstances(circs, c)),
                                 score=scores[i] if scores else "") for i, (c, r) in enumerate(zip(cases, rows))])
    if not circs:
        return []   # no circumstances: no derived slice rows, but the per-case outcomes still support the paired test
    total = (summary["tokens_in"] + summary["tokens_out"]) or 0
    written = []
    for cid, found in circumstances.slices(circs, cases, circumstances.run_context(summary.get("model"), summary["impl"])).items():
        check_name(cid, "slice id")   # a '/' or ';' would make the row read as a whole run
        part = [rows[i] for i in found]
        dev = [i for i in found if not cases[i].get("heldout")]
        held = [i for i in found if cases[i].get("heldout")]
        share = sum(r["tokens_in"] + r["tokens_out"] for r in part) / total if total else len(found) / len(rows)
        piece = dict(summary, cases=len(found), passed=sum(bool(r["ok"]) for r in part),
                     dev=f"{sum(bool(rows[i]['ok']) for i in dev)}/{len(dev)}", heldout=f"{sum(bool(rows[i]['ok']) for i in held)}/{len(held)}",
                     model_calls=sum(r["calls"] for r in part), tokens_in=sum(r["tokens_in"] for r in part),
                     tokens_out=sum(r["tokens_out"] for r in part), seconds=round(sum(r["seconds"] for r in part), 1),
                     cli_reported_cost_usd=round(summary["cli_reported_cost_usd"] * share, 4),
                     sample=(summary["sample"] + "/" if summary["sample"] else "") + f"slice:{cid}", details="derived from the run of the same date")
        for stale_key in ("balanced", "accuracy", "cost_per_case", "seconds_per_case"):
            piece.pop(stale_key, None)
        piece.update(balance.balanced(piece["passed"], piece["cases"], run_cost(config, piece, piece["model"]), piece["seconds"],
                                      config.balance.get(component)))
        record_result(piece, config)
        written.append(piece)
    return written


def circumstances_stale(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a whole-run row's derived rows no longer count: ``circumstances.csv`` changed (or cannot be read) since they were
    derived, or the per-case log holds no rows for the run. Empty for a component with no circumstances."""
    if is_partial(row):
        return ""
    try:
        circs = circumstances.for_component(config, component)
    except ValueError as exc:
        return f"circumstances.csv cannot be read: {exc}"
    if not circs:
        return ""
    wanted = (component, row.get("impl", ""), row.get("cases_sha", ""), (row.get("sample") or "").strip())
    mine = [r for r in read_per_case(config) if (r["component"], r["impl"], r["cases_sha"], r["sample"]) == wanted]
    if not any(r["circumstances_sha"] == circumstances.digest(circs) for r in mine):
        return "its slice rows and per-case log were not derived from the current circumstances.csv (re-run it to derive them)"
    return ""


def declares_constant(path: Path, name: str) -> bool:
    """Whether a module sets ``<name> = True`` at module level (the markers ``PAID`` and ``SIMULATED``)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    return any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
               and isinstance(n.value, ast.Constant) and n.value.value is True for n in tree.body)


def declares_paid(path: Path) -> bool:
    """Whether an implementation module sets ``PAID = True`` at module level (it calls a model that costs money)."""
    return declares_constant(path, "PAID")


def declares_simulated(path: Path) -> bool:
    """Whether an implementation module sets ``SIMULATED = True``: it meters a deterministic stand-in for a model."""
    return declares_constant(path, "SIMULATED")


def impl_path(config: Config, component: str, impl: str) -> Path:
    return config.evaluation / component / "impls" / f"{impl}.py"


def paid_reason(config: Config, component: str, impl: str, row: Optional[Dict[str, str]]) -> str:
    """Why running an arm may spend money, or an empty string for an offline arm: it is listed in ``paid_arms``, its
    module declares ``PAID = True``, or its last recorded run called a model. An arm that declares ``SIMULATED = True``
    (or whose last row records model ``simulated``) meters a stand-in and spends nothing, whatever its model calls: its
    cost is known (0.0), never inferred from a missing price."""
    if f"{component}/{impl}" in config.paid_arms:
        return "listed in paid_arms"
    if declares_paid(impl_path(config, component, impl)):
        return "declares PAID = True"
    if declares_simulated(impl_path(config, component, impl)) or (row or {}).get("model") == SIMULATED_MODEL:
        return ""
    if row and int(float(row.get("model_calls") or 0)) > 0:
        return "its last recorded run called a model"
    return ""


def stale_arms(config: Config) -> List[Tuple[str, str]]:
    """Each selected arm of the registry, then every other recorded arm of its component that competes with it (an
    ablation or validity arm is no rival). A rival recorded on other cases or another sample is included: it is not compared until it is
    re-run on the selected arm's cases and sample."""
    from . import leaderboard
    from .registry import load
    latest = leaderboard.latest_results(config.results_path)   # every arm, even one recorded only on named cases
    arms: List[Tuple[str, str]] = []
    registry = load(config)
    for row in registry.solutions:
        comp, impl = leaderboard.selected_arm(config, row, "", registry)
        if not comp:
            continue
        for arm in [(comp, impl)] + [(comp, name) for name, r in sorted(latest.get(comp, {}).items())
                                 if not leaderboard.is_ablation(r, config.evaluation)]:
            if arm not in arms:
                arms.append(arm)
    return arms


def expired_reason(config: Config, component: str, row: Optional[Dict[str, str]], today: Optional[datetime.date] = None) -> str:
    """Why a row's age makes it worth re-running: a metric of the solutions this component measures declares an expiration (or the
    project's ``[expiration] default`` does) and the row is older. Empty when none is declared (never by default) or it has not passed."""
    from . import cascade
    from .registry import harness_arms, load
    if not row or not row.get("date"):
        return ""
    try:
        recorded = datetime.date.fromisoformat(row["date"][:10])
    except ValueError:
        return ""
    today = today or datetime.date.today()
    for metric in load(config).metrics:
        if not any(comp == component for comp, _ in harness_arms(config, metric.get("command", ""))):
            continue
        days, _ = cascade.parse_expiration(metric.get("expiration", ""))
        if days is None and not metric.get("expiration", "").strip():
            days, _ = cascade.default_days(config)
        if days is not None and (today - recorded).days > days:
            return f"its metric {metric.get('metric_id', '')} declares an expiration of {days} days and the row is {(today - recorded).days} days old"
    return ""


def not_rerun_reason(config: Config, component: str, impl: str, row: Optional[Dict[str, str]], selected: bool, for_decision: bool,
                     named: bool, run_all: bool) -> str:
    """Empty when running a stale arm is worth its cost now, else why ``--stale`` leaves it alone. A changed file, or changed cases,
    only informs: a row is re-run automatically when it has never been measured (a selected arm), when its metric's expiration has
    passed, when a pending decision or release depends on it (``for_decision``, the selected arm only), when a person names it
    (``--include``), or with ``--all`` (the old run-everything behaviour). A rival, and any row nothing depends on, is never re-run."""
    if run_all or named:
        return ""
    if row is None and selected:
        return ""
    if selected and expired_reason(config, component, row):
        return ""
    if not selected:
        return "nothing depends on it (a rival is measured when a decision needs the comparison: name it with --include)"
    if for_decision:
        return ""
    return "no pending decision or release depends on it (run `esoi run --stale --for-decision` when one does, or name the arm with --include)"


def rerun_stale(config: Config, say: Callable[[str], None] = print, record: bool = True, include_paid: bool = False,
                include: Optional[List[str]] = None, full: bool = False, plan: bool = False, run_all: bool = False,
                for_decision: bool = False) -> int:
    """Report every selected implementation, and every rival recorded beside it, whose recorded result no longer counts, and run
    and record only those worth running (``not_rerun_reason``): a changed file or changed cases is information, not an order.

    By default a stale row is re-run when it has never been measured (a selected arm), when its metric's expiration has passed
    (never unless a metric or the project declares one), or when a pending decision or release depends on it (``for_decision``, the
    selected arm only) or a person names it (``include``). A rival, and any row nothing depends on, is listed as not re-run.
    ``run_all`` is the old behaviour: re-run every stale arm. Each plan line says which file changed and which component owns it,
    and why the row is or is not re-run.

    Each run uses the sample of the selected arm's newest whole-run row (an ``only:`` or ``slice:`` row is never the row
    staleness is judged on), so a re-record stays comparable with its rivals; ``full`` runs the whole set instead.

    An arm that may spend money (``paid_reason``) is never run by default: it is listed as skipped with the command that
    runs it. ``include_paid`` runs them all, ``include`` (``component/impl`` names) only those.
    The recorded rows are the only progress: every run appends its row when it finishes, so a killed re-record loses just the
    arm in flight and the next ``--stale`` starts at it, skipping what is already current. ``plan`` lists each arm with its
    decision (current, would run, not re-run, skipped as paid or capped) and runs nothing."""
    from . import leaderboard
    from .registry import load
    prepare_path(config)
    latest = leaderboard.latest_results(config.results_path, whole=True)   # staleness is judged on the newest whole run, not an only: row
    registry = load(config)
    selected_arms = {leaderboard.selected_arm(config, r, "", registry) for r in registry.solutions}
    skipped: List[str] = []
    skipped_ceiling: List[str] = []
    left: List[str] = []
    failed = 0
    target: Dict[str, List[str]] = {}   # component -> run flags of its selected arm's sample
    for comp, impl in stale_arms(config):
        row = latest.get(comp, {}).get(impl)
        why = stale_reason(config, comp, row)
        if comp not in target:   # stale_arms lists the selected arm of a component first
            target[comp] = [] if full else sample_args(config, comp, row)
        flags = target[comp]
        if not why and row and (comp, impl) not in selected_arms:
            wanted = sample_args(config, comp, row)
            if wanted != flags:
                why = f"it was scored on a different sample ({' '.join(wanted) or 'full set'}) than the selected arm ({' '.join(flags) or 'full set'}), so it is not comparable"
        if not why and full and row and sample_args(config, comp, row):
            why = "it was scored on a sample and --full asks for the whole set"
        if not why and (comp, impl) in selected_arms:
            why = expired_reason(config, comp, row)   # an expiration the metric or project declares and that has passed
        if not why:
            say(f"{comp}/{impl}: current")
            continue
        named = f"{comp}/{impl}" in (include or [])   # a person named this arm: that is the decision the guard asks for
        waiting = not_rerun_reason(config, comp, impl, row, (comp, impl) in selected_arms, for_decision, named, run_all)
        if waiting:
            label = "measured code changed since " + why.split(" changed since ", 1)[-1] if why.startswith("the measured code changed since") else f"stale, {why}"
            say(f"{comp}/{impl}: {label}; not re-run: {waiting}")
            left.append(f"{comp}/{impl}")
            continue
        paid = paid_reason(config, comp, impl, row)
        if paid and not (include_paid or named):
            say(f"{comp}/{impl}: stale, {why}; SKIPPED because it may spend money ({paid})")
            skipped.append(f"{comp}/{impl}")
            continue
        capped = "" if named else run_guards.ceiling_reason(config, comp, impl, run_guards.sample_of(flags), paid, stale_reason)
        if capped:
            say(f"{comp}/{impl}: stale, {why}; SKIPPED, not worth running: {capped}")
            skipped_ceiling.append(f"{comp}/{impl}")
            continue
        say(f"{comp}/{impl}: stale, {why}")
        if plan:
            say(f"{comp}/{impl}: would run" + (f" ({' '.join(flags)})" if flags else ""))
            continue
        score = importlib.import_module(f"{comp}.score")
        try:
            run_component(comp, score.score_case, ["--impl", impl] + flags + (["--record"] if record else ["--keep-going"]), config,
                          lambda text: None, guards=False)
        except RunError as exc:   # an arm that cannot start (an unknown variant key, a bad circumstance) fails once, loudly
            failed += 1
            say(f"{comp}/{impl}: ERROR, {exc}")
            continue
        say(f"{comp}/{impl}: run" + (f" ({' '.join(flags)})" if flags else "") + (" and recorded" if record else ""))
    if left:
        say(f"{len(left)} row(s) not re-run: a changed file only informs; improve the implementation first, and measure when a decision "
            "depends on the result (`esoi run --stale --for-decision`, `--include COMPONENT/IMPL`, or `--all` for every stale arm)")
    if skipped:
        say(f"skipped {len(skipped)} paid arm(s); stage and budget them first (see the metric run policy), then run each with "
            "`esoi run <component> --impl <name> --max-calls N --record`, or "
            f"`esoi run --stale --include {' --include '.join(skipped)}`")
    return 1 if failed else 0


def run_cli(argv: List[str], config: Config, say: Callable[[str], None] = print) -> int:
    """``esoi run <component> --impl <name> [flags]``, or ``esoi run --stale`` to re-run what is stale."""
    prepare_path(config)
    if argv and argv[0] == "--stale":
        include = [argv[i + 1] for i, word in enumerate(argv[:-1]) if word == "--include"]
        return rerun_stale(config, say, record="--no-record" not in argv, include_paid="--include-paid" in argv,
                           include=include, full="--full" in argv, plan="--plan" in argv, run_all="--all" in argv,
                           for_decision="--for-decision" in argv)
    components = discover_components(config)
    if not argv or argv[0] not in components:
        say("usage: esoi run <component> --impl <name> [--only IDS | --failed] [--sample N] [--max-calls N] [--keep-going] [--fresh] [--record] [--differs WHAT] [--force REASON]  |  esoi run --stale [--plan] [--full] [--for-decision | --all] [--include-paid | --include COMPONENT/IMPL]")
        say("components: " + (", ".join(components) or "none found under " + config.evaluation_dir))
        return 2
    score = importlib.import_module(f"{argv[0]}.score")
    try:
        run_component(argv[0], score.score_case, argv[1:], config, say)
    except RunError as exc:
        say(f"esoi run: {exc}")
        return 2
    return 0
