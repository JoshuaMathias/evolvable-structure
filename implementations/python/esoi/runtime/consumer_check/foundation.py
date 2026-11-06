"""A metric builds on the metric of the library it depends on: it measures on that foundation without re-running it.

A consumer of a library (a service that implements the library's seats) is judged on the cases the library already measures, plus cases of its
own (its real requests, its own source systems). Re-scoring the library's cases in the consumer, with a copy of the library's case files and
scorer, measures the same thing twice and lets the copy drift from the library. This module makes the consumer's metric BUILD ON the library's:

    [builds_on.context_selection.retrieval]          # <consumer component>.<a name for this foundation>
    repo = "../hub"                                   # the foundation's repository (it has its own esoi.toml)
    component = "context_retrieval"                   # the foundation's component, scored by ITS score.py
    share = 0.5                                       # the share of the consumer's number the foundation's cases carry
    on_stale = "run"                                  # "run" (default) or "report" when the recorded result cannot be reused
    arm_prefix = "lib_"                               # optional: the consumer's arm lib_<x> is the foundation's arm <x>

A consumer may build on several foundations (a selection metric and a bootstrap metric, say); the shares of all of them are below 1, and the
consumer's own cases carry the rest. Nothing here knows any particular library.

An arm says which foundation arm it is: ``FOUNDATION_ARMS = {"retrieval": "bm25_body"}`` in its module (or ``FOUNDATION_ARM = "bm25_body"`` when
there is one foundation). An arm that names none for a foundation does not build on it and the shares renormalise over the parts it has.

The rule when ``esoi run`` runs the consumer's arm over a whole set:

1. The consumer runs only its OWN cases (``load_cases`` of its score module holds no copy of the foundation's cases).
2. For each foundation the arm names, the foundation's latest whole-set row for that arm is REUSED when it is current by the foundation's own
   rule (``stale_reasons.stale_reason`` in the foundation's repository: same cases digest, committed code, the arm's code unchanged since its commit).
   Its per-case results join the consumer's per-case log; no foundation case is run.
3. When the row is missing or stale, nothing stale is mixed in. ``on_stale = "run"`` runs the foundation's cases through the FOUNDATION'S scorer
   (its ``score_case``, one code path): with the foundation's own build of the named arm, or, for an arm that names none, through the consumer
   score module's ``foundation_fn(foundation_name, fn)`` adapter (it returns None for a foundation the arm cannot be adapted to: the arm does not build on it). ``on_stale = "report"`` refuses the run and says why the foundation is stale.
4. The number is the blend of the parts at their shares: per-case accuracy, cost and seconds are weighted by share, then folded by the consumer's
   own ``[balance.<component>]`` (the weights stay the consumer's). The row records ``builds_on``: ``name=component:arm@git_sha/cases_sha`` for each
   part, and the row is STALE when the foundation's cases or the foundation arm's code changed since (``stale_reason``), so an improvement to the
   foundation (a new case kind, a scorer fix) reaches the consumer's number the next time it is run.
5. A sampled or ``--only`` run scores the consumer's own cases only and says so; composition is for whole sets.

Cascades: a consumer stage written ``name [inherits=stage]`` is passed only when the foundation's stage of that name passed for the foundation
arm (``inherited_gate``), so the consumer inherits the gate instead of re-proving it. A gate beside ``inherits`` tightens, never loosens (S47).
"""
from __future__ import annotations

import ast
import importlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import case_identity, results_log, cascade_stages, stage_standings
from esoi.structure.intent_registry import config as config_module
from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry.config import Config

ON_STALE = ("run", "report")


@dataclass(frozen=True)
class Foundation:
    component: str      # the consumer's component
    name: str           # what the consumer calls this foundation
    root: Path          # the foundation's repository
    target: str         # the foundation's component
    share: float
    on_stale: str = "run"
    arm_prefix: str = ""   # the consumer's arms named <prefix><foundation arm> ARE that foundation arm (they delegate to it without adding code)


@dataclass
class Part:
    """The foundation's contribution to one composed run."""
    name: str
    arm: str
    cases: int
    passed: float
    model_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost: Any = 0.0        # dollars, or "" when the foundation's price is unknown
    seconds: float = 0.0
    dev: str = ""
    heldout: str = ""
    how: str = "reused"    # reused | run
    identity: str = ""
    reason: str = ""       # why the recorded result was not reused
    per_case: List[Dict[str, Any]] = field(default_factory=list)


def declared(config: Config, component: str = "") -> List[Foundation]:
    """The foundations a component builds on, from ``[builds_on.<component>.<name>]`` (every component when none is named)."""
    out: List[Foundation] = []
    for comp, table in (config.builds_on or {}).items():
        if component and comp != component:
            continue
        for name, entry in (table or {}).items():
            out.append(Foundation(comp, name, (config.root / str(entry.get("repo", ""))).resolve(), str(entry.get("component", "")),
                                  float(entry.get("share", 0)), str(entry.get("on_stale", "run")), str(entry.get("arm_prefix", ""))))
    return out


def problems(config: Config) -> List[str]:
    """What is wrong with the ``[builds_on]`` tables: a missing repository or component, a share outside (0, 1) or shares that leave the
    consumer's own cases nothing, an unknown ``on_stale``, a consumer component that does not exist."""
    out: List[str] = []
    for comp in sorted({f.component for f in declared(config)}):
        mine = declared(config, comp)
        if not (config.evaluation / comp / "score.py").is_file():
            out.append(f"builds_on.{comp}: the consumer has no component {comp} (no {config.evaluation_dir}/{comp}/score.py)")
        if sum(f.share for f in mine) >= 1:
            out.append(f"builds_on.{comp}: the shares add up to {sum(f.share for f in mine):g}, so the consumer's own cases carry nothing (they must stay below 1)")
        for f in mine:
            tag = f"builds_on.{comp}.{f.name}"
            if not 0 < f.share < 1:
                out.append(f"{tag}: share {f.share:g} is not between 0 and 1")
            if f.on_stale not in ON_STALE:
                out.append(f"{tag}: on_stale {f.on_stale!r} is not one of {', '.join(ON_STALE)}")
            if not (f.root / config_module.CONFIG_NAME).is_file() and not (f.root / "pyproject.toml").is_file():
                out.append(f"{tag}: {f.root.name} has no esoi configuration, so its results cannot be read")
            elif not (f.root / "evaluation" / "components" / f.target / "score.py").is_file() and not has_score(f):
                out.append(f"{tag}: {f.root.name} has no component {f.target}")
    return out


def has_score(f: Foundation) -> bool:
    try:
        return (load_config(f).evaluation / f.target / "score.py").is_file()
    except config_module.ConfigError:
        return False


def load_config(f: Foundation) -> Config:
    return config_module.load(f.root)


def declared_arms(config: Config, component: str, impl: str) -> Dict[str, str]:
    """{foundation name: foundation arm} an arm names with ``FOUNDATION_ARMS = {...}`` (or ``FOUNDATION_ARM = "x"`` for a single foundation)."""
    path = config.evaluation / component / "impls" / f"{variants.base_of(impl)}.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    found: Dict[str, str] = {}
    names = [f.name for f in declared(config, component)]
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                continue
            if node.targets[0].id == "FOUNDATION_ARMS" and isinstance(value, dict):
                found.update({str(k): str(v) for k, v in value.items()})
            elif node.targets[0].id == "FOUNDATION_ARM" and isinstance(value, str) and len(names) == 1:
                found[names[0]] = value
    base = variants.base_of(impl)
    for f in declared(config, component):   # a configured prefix names the arm when the module declares nothing for this foundation
        if f.arm_prefix and f.name not in found and base.startswith(f.arm_prefix) and len(base) > len(f.arm_prefix):
            found[f.name] = base[len(f.arm_prefix):]
    return found


def identity(f: Foundation, arm: str, git_sha: str, cases_sha: str) -> str:
    return f"{f.name}={f.target}:{arm}@{git_sha}/{cases_sha}"


def parse_identity(cell: str) -> List[Tuple[str, str, str, str, str]]:
    """``(name, component, arm, git_sha, cases_sha)`` for each entry of a row's ``builds_on`` cell."""
    out = []
    for part in (cell or "").split(";"):
        try:
            name, rest = part.split("=", 1)
            target, rest = rest.split(":", 1)
            arm, rest = rest.rsplit("@", 1)
            sha, cases = rest.split("/", 1)
        except ValueError:
            continue
        out.append((name, target, arm, sha, cases))
    return out


def code_reason(fconf: Config, target: str, arm: str, git_sha: str, cases_sha: str) -> str:
    """Why a foundation arm measured at ``git_sha`` on ``cases_sha`` no longer describes the foundation, or an empty string."""
    from esoi.optimization.measurement_harness import interface as harness
    now = case_identity.cases_digest(target, fconf.evaluation)
    if cases_sha != now:
        return f"the foundation's cases changed (measured on {cases_sha or 'blank'}, now {now})"
    if not git_sha:
        return "the foundation's code has no known commit"
    if git_sha.endswith("-dirty"):
        return "it was measured on uncommitted foundation code"
    return harness.code_changed_reason(fconf, target, {"impl": arm, "git_sha": git_sha})


def stale_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a composed row no longer counts because a foundation it builds on changed, or an empty string (a row that builds on nothing)."""
    cell = row.get("builds_on", "")
    if not cell:
        return ""
    known = {f.name: f for f in declared(config, component)}
    for name, target, arm, sha, cases in parse_identity(cell):
        f = known.get(name)
        if f is None:
            return f"its row builds on {name!r}, which [builds_on.{component}] no longer declares"
        if why := code_reason(load_config(f), target, arm, sha, cases):
            return f"the foundation {name} changed since this row was composed: {why}"
    return ""


def recorded_part(f: Foundation, arm: str) -> Tuple[Optional[Part], str]:
    """The foundation's latest whole-set row for ``arm`` as a part, or ``(None, why it cannot be reused)``."""
    from esoi.optimization.measurement_harness import interface as harness
    fconf = load_config(f)
    rows = [r for r in results_log.all_results(fconf.results_path).get(f.target, {}).get(arm, []) if not (r.get("sample") or "").strip()]
    if not rows:
        return None, f"the foundation has no recorded whole-set result for {arm}"
    row = rows[-1]
    if why := harness.stale_reason(fconf, f.target, row):
        return None, why
    per = [dict(r) for r in results_log.per_case_rows(fconf)
           if (r["component"], r["impl"], r["cases_sha"], (r["sample"] or "").strip()) == (f.target, arm, row["cases_sha"], "")]
    cost = row.get("cost_usd", "")
    return Part(f.name, arm, int(float(row["cases"])), float(row["passed"]), int(float(row.get("model_calls") or 0)),
                int(float(row.get("tokens_in") or 0)), int(float(row.get("tokens_out") or 0)),
                float(cost) if cost not in ("", None) else "", float(row.get("seconds") or 0), row.get("dev", ""), row.get("heldout", ""),
                "reused", identity(f, arm, row["git_sha"], row["cases_sha"]),
                per_case=per if len(per) == int(float(row["cases"])) else []), ""


def run_part(f: Foundation, arm: str, consumer_fn: Callable, adapter: Optional[Callable], meter: Any, say: Callable[[str], None],
             reason: str) -> Optional[Part]:
    """Run the foundation's cases through the foundation's own scorer. With a named foundation arm it is the foundation's own build of that arm;
    without one the consumer's ``adapter(name, fn)`` turns the consumer's arm into what the foundation's scorer calls."""
    from esoi.optimization.measurement_harness import interface as harness
    from esoi.optimization.when_metrics_are_run import interface as gating
    fconf = load_config(f)
    harness.prepare_path(fconf)
    cases = harness.load_cases(f.target, fconf)
    score = importlib.import_module(f"{f.target}.score")
    if arm:
        fn = harness.load_impl(arm, f.target, fconf)(meter)
    elif adapter is not None and (fn := adapter(f.name, consumer_fn)) is not None:
        pass
    else:
        return None
    say(f"{f.name}: running {len(cases)} foundation case(s) through {f.root.name}'s {f.target} scorer ({reason})")
    rows: List[Dict[str, Any]] = []
    spent = dict(calls=meter.calls, tin=meter.tokens_in, tout=meter.tokens_out, cost=meter.cost_usd)
    started = time.time()
    for case in cases:
        before, t0, cost0 = meter.calls, time.time(), meter.cost_usd
        try:
            row = score.score_case(fn, case)
        except gating.BudgetExceeded:
            raise
        except Exception as exc:   # a case that raises fails; the run goes on
            row = dict(ok=False, note=f"{type(exc).__name__}: {exc}")
        row.update(id=case["id"], calls=meter.calls - before, seconds=round(time.time() - t0, 1), heldout=bool(case.get("heldout")))
        rows.append(row)
    held = [r for r in rows if r["heldout"]]
    sha = harness.current_sha(fconf, f.target, arm) if arm else harness.current_sha(fconf)
    ident = identity(f, arm or "(consumer arm)", sha, case_identity.cases_digest(f.target, fconf.evaluation))
    return Part(f.name, arm or "(consumer arm)", len(rows), float(sum(bool(r["ok"]) for r in rows)), meter.calls - spent["calls"],
                meter.tokens_in - spent["tin"], meter.tokens_out - spent["tout"], round(meter.cost_usd - spent["cost"], 6),
                round(time.time() - started, 1), f"{sum(bool(r['ok']) for r in rows if not r['heldout'])}/{len(rows) - len(held)}",
                f"{sum(bool(r['ok']) for r in held)}/{len(held)}", "run", ident, reason,
                [dict(case_id=str(r["id"]), ok="1" if r["ok"] else "0", calls=r["calls"], seconds=r["seconds"]) for r in rows])


def measure(config: Config, component: str, impl: str, consumer_fn: Callable, adapter: Optional[Callable], meter: Any,
            say: Callable[[str], None]) -> List[Part]:
    """The part each foundation contributes for this arm: reuse a current recorded result, else the policy's choice (see the module docstring)."""
    from esoi.optimization.measurement_harness import interface as harness
    named, parts = declared_arms(config, component, impl), []
    for f in declared(config, component):
        arm = named.get(f.name, "")
        if not arm and adapter is None:
            say(f"{f.name}: this arm names no foundation arm and the score module has no adapter, so it does not build on {f.name}")
            continue
        found, why = recorded_part(f, arm) if arm else (None, "the arm names no foundation arm, so it is measured by the foundation's scorer")
        if found is not None:
            say(f"{f.name}: reused {found.cases} case(s) of {f.root.name}'s {f.target} for {arm} ({found.identity}); none run again")
            parts.append(found)
        elif f.on_stale == "report":
            raise harness.RunError(f"the foundation {f.name} cannot be reused: {why} (on_stale = report, so nothing is run; "
                                   f"re-record {arm or 'the foundation arm'} in {f.root.name} and run again)")
        elif (ran := run_part(f, arm, consumer_fn, adapter, meter, say, why)) is not None:
            parts.append(ran)
        else:
            say(f"{f.name}: this arm names no foundation arm and the score module's foundation_fn does not adapt it, so it does not build on {f.name}")
    return parts


def blend(own: Dict[str, Any], own_cost: Any, parts: List[Part], foundations: List[Foundation], table: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The composed summary fields: parts and the consumer's own cases weighted by share (shares renormalised over the parts present), then
    folded by the consumer's ``[balance.<component>]``. ``own`` is the consumer's own run summary (``cases``, ``passed``, ``seconds`` ...)."""
    weights = {p.name: next(f.share for f in foundations if f.name == p.name) for p in parts}
    from esoi.optimization.measurement_harness import interface as harness
    own_share = 1.0 - sum(f.share for f in foundations)
    if own["cases"]:
        weights[""] = own_share
    total = sum(weights.values())
    shares = {k: v / total for k, v in weights.items()}
    cases = own["cases"] + sum(p.cases for p in parts)
    accuracy = (shares.get("", 0.0) * own["passed"] / own["cases"] if own["cases"] else 0.0) + sum(shares[p.name] * p.passed / p.cases for p in parts if p.cases)
    unknown = (own["cases"] and own_cost == "") or any(p.cost == "" for p in parts)
    cost_pc = None if unknown else ((shares.get("", 0.0) * float(own_cost or 0) / own["cases"] if own["cases"] else 0.0)
                                    + sum(shares[p.name] * float(p.cost) / p.cases for p in parts if p.cases))
    seconds_pc = (shares.get("", 0.0) * own["seconds"] / own["cases"] if own["cases"] else 0.0) + sum(shares[p.name] * p.seconds / p.cases for p in parts if p.cases)
    out = dict(cases=cases, passed=round(accuracy * cases), model_calls=own["model_calls"] + sum(p.model_calls for p in parts),
               tokens_in=own["tokens_in"] + sum(p.tokens_in for p in parts), tokens_out=own["tokens_out"] + sum(p.tokens_out for p in parts),
               seconds=round(own["seconds"] + sum(p.seconds for p in parts), 1),
               cli_reported_cost_usd=round(float(own_cost or 0) + sum(float(p.cost or 0) for p in parts), 4),
               dev=sum_ratio([own["dev"]] + [p.dev for p in parts]), heldout=sum_ratio([own["heldout"]] + [p.heldout for p in parts]),
               builds_on=";".join(p.identity for p in parts))
    if cost_pc is not None:
        out.update(harness.balanced(accuracy * cases, cases, cost_pc * cases, seconds_pc * cases, table))
    return out


def sum_ratio(cells: List[str]) -> str:
    done = total = 0
    for cell in cells:
        try:
            a, b = (int(x) for x in cell.split("/"))
        except ValueError:
            continue
        done, total = done + a, total + b
    return f"{done}/{total}"


def note_for(part: Part, share: float) -> str:
    accuracy = part.passed / part.cases if part.cases else 0.0
    how = "reused, none run again" if part.how == "reused" else f"run through the foundation's scorer ({part.reason})"
    return f"builds on {part.name} at share {share:g}: {part.cases} cases, accuracy {accuracy:.3f}, {how}"


def inherited_gate(config: Config, component: str, impl: str) -> Callable[[cascade_stages.Stage], Tuple[bool, str]]:
    """``gate(stage) -> (met, why)``: whether the foundation stage a consumer stage ``inherits`` has passed for the foundation arm this arm names,
    by the foundation's own stage definition (gate, floor, expiry and staleness all the foundation's)."""
    from esoi.optimization.measurement_harness import interface as harness
    from esoi.structure.intent_registry import registry as registry_module
    named, foundations = declared_arms(config, component, impl), declared(config, component)

    def gate(stage: cascade_stages.Stage) -> Tuple[bool, str]:
        checked: List[Tuple[bool, str]] = []
        for f in foundations:
            arm = named.get(f.name)
            if not arm:
                continue
            fconf = load_config(f)
            loaded = registry_module.load(fconf)
            for metric in loaded.metrics:
                if f.target not in [c for c, _ in registry_module.harness_arms(fconf, metric.get("command", ""))]:
                    continue
                stages, errors = cascade_stages.load_stages(fconf, metric)
                theirs = next((i for i, s in enumerate(stages) if s.name == stage.inherits), None)
                if theirs is None or errors:
                    continue
                history = results_log.all_results(fconf.results_path).get(f.target, {}).get(arm, [])
                standing = stage_standings.standings(stages, {arm: history}, None, lambda row, c=fconf: harness.stale_reason(c, f.target, row, True),
                                             fconf.evaluation).get(arm)
                row = standing.rows.get(theirs) if standing else None
                if row is None:
                    why = "expired or stale" if standing and theirs in standing.expired else "not run"
                    checked.append((False, f"{f.name}: {arm} at {stage.inherits} is {why}"))
                else:
                    met, why = stage_standings.gate_met(stages[theirs], row, None, fconf.evaluation)
                    checked.append((met, f"{f.name}: {arm} at {stage.inherits}: {why or 'passed'}"))
        if not checked:
            return False, f"no foundation has a stage {stage.inherits!r} for this arm"
        failed = [why for met, why in checked if not met]
        return (not failed), "; ".join(failed)
    return gate
